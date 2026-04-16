'''
create classifier model and predict
'''
from sklearn.metrics import f1_score, recall_score, accuracy_score, precision_score, confusion_matrix
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GridSearchCV
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
    """创建梯度提升分类器"""
    gbc = GradientBoostingClassifier(random_state=42)
    return gbc


def predict(X_test):
    model, _ = load()
    y_pred = model.predict(X_test)
    return y_pred


def train():
    X_train, X_test, y_train, y_test = prepare_data()
    total = len(X_test) + len(X_train)
    if total < MIN_TRAIN_NUM:
        raise ValueError(f'训练数据不足, 无法训练模型. 需要{MIN_TRAIN_NUM}, 当前{total}')

    # 检查训练数据是否同时包含喜欢和不喜欢两个类别
    import numpy as np
    unique_classes = np.unique(y_train)
    if len(unique_classes) < 2:
        raise ValueError(
            f'训练数据只有一个类别({unique_classes}), 无法训练模型. '
            f'请确保既有"喜欢"也有"不喜欢"的打标数据')

    # GridSearchCV 自动搜索最优参数
    logger.info('开始 GridSearchCV 参数搜索...')
    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [3, 5, 7],
        'learning_rate': [0.05, 0.1, 0.2],
        'min_samples_split': [2, 5],
    }

    gbc = GradientBoostingClassifier(random_state=42)
    grid_search = GridSearchCV(
        gbc, param_grid,
        cv=3,               # 3 折交叉验证
        scoring='f1',       # 以 F1 分数作为优化目标
        n_jobs=-1,          # 使用所有 CPU 核心
        verbose=1,
    )
    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    logger.info(f'最优参数: {grid_search.best_params_}')
    logger.info(f'最优交叉验证 F1: {grid_search.best_score_:.4f}')

    # 用最优模型在测试集上评估
    y_pred = best_model.predict(X_test)
    confusion_mtx = confusion_matrix(y_test, y_pred, labels=[0, 1])
    scores = evaluate(confusion_mtx, y_test, y_pred)

    models_data = (best_model, scores)
    dump_model(get_data_path(MODEL_FILE), models_data)
    logger.info('new model trained')
    return models_data


def evaluate(confusion_mtx, y_test, y_pred):
    tn, fp, fn, tp = confusion_mtx.ravel()
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    logger.info(f'tp: {tp}, fp: {fp}')
    logger.info(f'fn: {fn}, tn: {tn}')
    logger.info(f'accuracy_score: {accuracy}')
    logger.info(f'precision_score: {precision}')
    logger.info(f'recall_score: {recall}')
    logger.info(f'f1_score: {f1}')
    model_scores = dict(accuracy=accuracy, precision=precision, recall=recall, f1=f1)
    model_scores = {key: float('{:.2f}'.format(value))
                    for key, value in model_scores.items()}
    return model_scores


def recommend():
    '''
    use trained model to recommend items
    '''
    ids, X = prepare_predict_data()
    if len(X) == 0 or X.size == 0:
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