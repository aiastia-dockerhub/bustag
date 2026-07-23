'''
create classifier model and predict
'''
import threading
from sklearn.metrics import f1_score, recall_score, accuracy_score, precision_score, confusion_matrix
from sklearn.neighbors import KNeighborsClassifier
from bustag.model.prepare import prepare_data, prepare_predict_data
from bustag.model.persist import load_model, dump_model
from bustag.spider.db import RATE_TYPE, ItemRate, db
from bustag.util import logger, get_data_path, MODEL_PATH

MODEL_FILE = MODEL_PATH + 'model.pkl'
MIN_TRAIN_NUM = 200
# 分块预测的每块大小（控制内存峰值，避免 OOM）
PREDICT_CHUNK_SIZE = 1000

# 全局推荐锁：防止「重新推荐」与「后台调度器自动推荐」并发跑导致内存翻倍
_recommend_lock = threading.Lock()


def load():
    model_data = load_model(get_data_path(MODEL_FILE))
    return model_data


def create_model():
    knn = KNeighborsClassifier(n_neighbors=11)
    return knn


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
    import numpy as np
    unique_classes = np.unique(y_train)
    if len(unique_classes) < 2:
        raise ValueError(
            f'训练数据只有一个类别({unique_classes}), 无法训练模型. '
            f'请确保既有"喜欢"也有"不喜欢"的打标数据')

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    confusion_mtx = confusion_matrix(y_test, y_pred, labels=[0, 1])
    scores = evaluate(confusion_mtx, y_test, y_pred)
    models_data = (model, scores)
    dump_model(get_data_path(MODEL_FILE), models_data)
    logger.info('new model trained')
    return models_data


def evaluate(confusion_mtx, y_test, y_pred):
    tn, fp, fn, tp = confusion_mtx.ravel()
    # accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    logger.info(f'tp: {tp}, fp: {fp}')
    logger.info(f'fn: {fn}, tn: {tn}')
    # logger.info(f'accuracy_score: {accuracy}')
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

    优化：分块加载 + 分块预测 + 批量写入，控制内存峰值避免 OOM；
         持有全局锁防止与后台调度器的推荐任务并发执行。
    Returns:
        (total, recommended) 或 None（已有推荐任务在执行，本次跳过）
    '''
    # 非阻塞抢锁：若后台调度器已在推荐，立即返回 None，由调用方决定如何处理
    if not _recommend_lock.acquire(blocking=False):
        logger.warning('recommend() already running, skip this call')
        return None

    try:
        return _recommend_locked()
    finally:
        _recommend_lock.release()


def _recommend_locked():
    '''实际的推荐逻辑，调用前需已持有 _recommend_lock'''
    # 模型只加载一次，避免分块预测时每块重复读盘 model.pkl
    model, _ = load()

    count = 0
    total = 0
    rate_type = RATE_TYPE.SYSTEM_RATE

    # 关键：始终取 page=1。因为我们处理完一块就会给这些项写入 ItemRate 记录，
    # 它们随即从未评分集合消失；下一轮 page=1 自然取到下一批未评分项。
    # 若改成 page=1,2,3... 递增，由于每轮数据集都在缩小，OFFSET 会错位、跳过大量项。
    # （相当于边遍历边删除，必须每次从头取。）
    batch_no = 0
    while True:
        batch_no += 1
        # 分块加载未评分数据：内存峰值 = 单块而非全量
        ids, X, _ = prepare_predict_data(
            page=1, page_size=PREDICT_CHUNK_SIZE)
        if len(X) == 0:
            break

        # 用已加载的模型分块预测（KNN 硬分类）
        y_pred = model.predict(X)

        # 收集本块写入行，单次事务批量 INSERT（替代旧的逐条 save）
        rows = []
        for item_id, y in zip(ids, y_pred):
            if y == 1:
                count += 1
            rows.append({
                'rate_type': rate_type,
                'rate_value': int(y),
                'item': item_id,
            })

        if rows:
            with db.atomic():
                ItemRate.insert_many(rows).execute()

        total += len(ids)
        logger.info(
            f'recommend batch={batch_no}: +{len(ids)} '
            f'(running total={total}, recommended={count})')

        # 本块不足一页，说明未评分数据已处理完
        if len(ids) < PREDICT_CHUNK_SIZE:
            break

    logger.warning(
        f'predicted {total} items, recommended {count}')
    return total, count
