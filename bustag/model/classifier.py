'''
create classifier model and predict
使用 LightGBM 梯度提升树替代 KNN，提升推荐精度
优化：交叉验证 + 概率推荐 + 可读特征重要性 + AUC 评估
'''
import re
import html
import numpy as np
from sklearn.metrics import (
    f1_score, recall_score, precision_score, confusion_matrix,
    roc_auc_score, cross_val_score
)
from lightgbm import LGBMClassifier
from bustag.model.prepare import prepare_data, prepare_predict_data
from bustag.model.persist import load_model, dump_model
from bustag.spider.db import RATE_TYPE, ItemRate
from bustag.util import logger, get_data_path, MODEL_PATH

MODEL_FILE = MODEL_PATH + 'model.pkl'
FEATURE_NAMES_PATH = MODEL_PATH + 'feature_names.pkl'
MIN_TRAIN_NUM = 200
# 推荐阈值：预测概率 >= 此值才推荐
RECOMMEND_THRESHOLD = 0.6


def load():
    model_data = load_model(get_data_path(MODEL_FILE))
    return model_data


def create_model():
    '''
    创建 LightGBM 分类器
    针对小数据集（200~5000条）优化的默认参数
    '''
    model = LGBMClassifier(
        n_estimators=200,       # 增加树数量，配合 early stopping
        max_depth=6,            # 树的最大深度，防止过拟合
        learning_rate=0.05,     # 降低学习率，提高泛化能力
        num_leaves=31,          # 叶子节点数
        min_child_samples=20,   # 叶子节点最小样本数，小数据集防过拟合
        subsample=0.8,          # 样本采样比例
        colsample_bytree=0.8,   # 特征采样比例
        reg_alpha=0.1,          # L1 正则化
        reg_lambda=0.1,         # L2 正则化
        class_weight='balanced', # 自动平衡喜欢/不喜欢样本权重
        random_state=42,
        verbose=-1,             # 静默模式
        n_jobs=1,               # 单线程，避免资源竞争
    )
    return model


def predict(X_test):
    model, _ = load()
    y_pred = model.predict(X_test)
    return y_pred


def predict_proba(X_test):
    '''返回预测概率（喜欢类的概率）'''
    model, _ = load()
    y_proba = model.predict_proba(X_test)[:, 1]
    return y_proba


def _sanitize_name(name):
    '''
    清理特征名中的特殊字符，防止 HTML/日志注入问题
    - 移除控制字符（换行、制表符等）
    - 使用 html.escape() 转义 HTML 特殊字符
    - 截断过长名称
    '''
    # 移除控制字符（保留可打印字符）
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    # 使用标准库进行 HTML 转义（处理 < > & " 等）
    name = html.escape(name, quote=True)
    # 截断过长名称
    if len(name) > 50:
        name = name[:47] + '...'
    return name


def _get_readable_importances(model, top_n=15):
    '''
    获取可读的特征重要性，将 f_0, f_1 映射回实际标签名
    所有标签名经过特殊字符清理，防止 HTML/日志注入
    '''
    try:
        feature_names = load_model(get_data_path(FEATURE_NAMES_PATH))
    except (FileNotFoundError, Exception):
        feature_names = None

    importances = model.feature_importances_
    top_indices = np.argsort(importances)[::-1][:top_n]
    readable = []

    for idx in top_indices:
        imp = importances[idx]
        if imp == 0:
            continue
        name = f'f_{idx}'
        if feature_names:
            # 查找该索引对应的特征类别和名称
            for category, info in feature_names.items():
                start = info['start']
                count = info['count']
                if start <= idx < start + count:
                    local_idx = idx - start
                    if category == 'numeric':
                        name = info['names'][local_idx]
                    elif 'classes' in info and local_idx < len(info['classes']):
                        cls_name = _sanitize_name(info['classes'][local_idx])
                        name = f'{category}:{cls_name}'
                    else:
                        name = f'{category}_f{local_idx}'
                    break
        readable.append((name, int(imp)))

    return readable


def train():
    model = create_model()
    X_train, X_test, y_train, y_test = prepare_data()
    total = len(X_test) + len(X_train)
    if total < MIN_TRAIN_NUM:
        raise ValueError(f'训练数据不足, 无法训练模型. 需要{MIN_TRAIN_NUM}, 当前{total}')

    # 检查训练数据是否同时包含喜欢和不喜欢两个类别
    unique_classes = np.unique(y_train)
    if len(unique_classes) < 2:
        raise ValueError(
            f'训练数据只有一个类别({unique_classes}), 无法训练模型. '
            f'请确保既有"喜欢"也有"不喜欢"的打标数据')

    # 训练模型（带早停）
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
    )

    # --- 评估 ---
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    confusion_mtx = confusion_matrix(y_test, y_pred, labels=[0, 1])
    scores = evaluate(confusion_mtx, y_test, y_pred, y_proba)

    # --- 交叉验证（5折） ---
    try:
        cv_scores = cross_val_score(
            model, X_train, y_train, cv=5, scoring='f1', n_jobs=1)
        cv_mean = float('{:.2f}'.format(cv_scores.mean()))
        cv_std = float('{:.2f}'.format(cv_scores.std()))
        scores['cv_f1_mean'] = cv_mean
        scores['cv_f1_std'] = cv_std
        logger.info(f'5-Fold CV F1: {cv_mean} ± {cv_std}')
    except Exception as e:
        logger.warning(f'Cross-validation failed: {e}')

    # 记录可读的特征重要性 Top 15
    try:
        readable = _get_readable_importances(model, top_n=15)
        logger.info('Top 15 feature importances (readable):')
        for name, imp in readable:
            logger.info(f'  {name}: {imp}')
        scores['top_features'] = readable[:10]
    except Exception as e:
        logger.warning(f'Failed to get readable importances: {e}')

    models_data = (model, scores)
    dump_model(get_data_path(MODEL_FILE), models_data)
    logger.info('new LightGBM model trained')
    return models_data


def evaluate(confusion_mtx, y_test, y_pred, y_proba=None):
    tn, fp, fn, tp = confusion_mtx.ravel()
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    logger.info(f'tp: {tp}, fp: {fp}')
    logger.info(f'fn: {fn}, tn: {tn}')
    logger.info(f'precision_score: {precision}')
    logger.info(f'recall_score: {recall}')
    logger.info(f'f1_score: {f1}')

    model_scores = dict(precision=precision, recall=recall, f1=f1)

    # AUC 评估
    if y_proba is not None:
        try:
            auc = roc_auc_score(y_test, y_proba)
            model_scores['auc'] = auc
            logger.info(f'AUC: {auc}')
        except ValueError:
            pass

    model_scores = {key: float('{:.2f}'.format(value))
                    for key, value in model_scores.items()
                    if key != 'top_features'}
    return model_scores


def recommend():
    '''
    use trained model to recommend items
    使用概率阈值而非硬分类，只推荐高概率喜欢的项目
    '''
    ids, X = prepare_predict_data()
    if len(X) == 0:
        logger.warning('no data for recommend')
        return

    count = 0
    total = len(ids)
    y_proba = predict_proba(X)

    for item_id, prob in zip(ids, y_proba):
        # 使用概率阈值决策
        if prob >= RECOMMEND_THRESHOLD:
            rate_value = 1  # LIKE
            count += 1
        else:
            rate_value = 0  # DISLIKE

        rate_type = RATE_TYPE.SYSTEM_RATE
        item_rate = ItemRate(rate_type=rate_type,
                             rate_value=rate_value, item_id=item_id)
        item_rate.save()

    logger.warning(
        f'predicted {total} items, recommended {count} '
        f'(threshold={RECOMMEND_THRESHOLD})')
    return total, count