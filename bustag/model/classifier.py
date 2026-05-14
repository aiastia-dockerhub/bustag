'''
create classifier model and predict
使用 LightGBM 梯度提升树替代 KNN，提升推荐精度
'''
import numpy as np
from sklearn.metrics import f1_score, recall_score, precision_score, confusion_matrix
from lightgbm import LGBMClassifier
from bustag.model.prepare import prepare_data, prepare_predict_data
from bustag.model.persist import load_model, dump_model
from bustag.spider.db import RATE_TYPE, ItemRate
from bustag.util import logger, get_data_path, MODEL_PATH

MODEL_FILE = MODEL_PATH + 'model.pkl'
MIN_TRAIN_NUM = 200


def load():
    model_data = load_model(get_data_path(MODEL_FILE))
    return model_data


def create_model():
    '''
    创建 LightGBM 分类器
    针对小数据集（200~5000条）优化的默认参数
    '''
    model = LGBMClassifier(
        n_estimators=100,       # 树的数量
        max_depth=6,            # 树的最大深度，防止过拟合
        learning_rate=0.1,      # 学习率
        num_leaves=31,          # 叶子节点数
        min_child_samples=20,   # 叶子节点最小样本数，小数据集防过拟合
        subsample=0.8,          # 样本采样比例
        colsample_bytree=0.8,   # 特征采样比例
        reg_alpha=0.1,          # L1 正则化
        reg_lambda=0.1,         # L2 正则化
        random_state=42,
        verbose=-1,             # 静默模式
        n_jobs=1,               # 单线程，避免资源竞争
    )
    return model


def predict(X_test):
    model, _ = load()
    y_pred = model.predict(X_test)
    return y_pred


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

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    confusion_mtx = confusion_matrix(y_test, y_pred, labels=[0, 1])
    scores = evaluate(confusion_mtx, y_test, y_pred)

    # 记录特征重要性 Top 10
    try:
        importances = model.feature_importances_
        top_indices = np.argsort(importances)[::-1][:10]
        logger.info(f'Top 10 feature importances: {importances[top_indices]}')
    except Exception:
        pass

    models_data = (model, scores)
    dump_model(get_data_path(MODEL_FILE), models_data)
    logger.info('new LightGBM model trained')
    return models_data


def evaluate(confusion_mtx, y_test, y_pred):
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
    model_scores = {key: float('{:.2f}'.format(value))
                    for key, value in model_scores.items()}
    return model_scores


def recommend():
    '''
    use trained model to recommend items
    '''
    ids, X = prepare_predict_data()
    if len(X) == 0:
        logger.warning(
            f'no data for recommend')
        return
    count = 0
    total = len(ids)
    y_pred = predict(X)
    for id, y in zip(ids, y_pred):
        if y == 1:
            count += 1
        rate_type = RATE_TYPE.SYSTEM_RATE
        rate_value = y
        item_id = id
        item_rate = ItemRate(rate_type=rate_type,
                             rate_value=rate_value, item_id=item_id)
        item_rate.save()
    logger.warning(
        f'predicted {total} items, recommended {count}')
    return total, count