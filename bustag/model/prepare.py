'''
prepare data for model training
'''
import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from bustag.spider.db import get_items, RATE_TYPE, ItemRate, Item, get_tags_for_items
from bustag.model.persist import dump_model, load_model
from bustag.util import logger, get_data_path, MODEL_PATH

BINARIZER_PATH = MODEL_PATH + 'label_binarizer.pkl'

# 用于训练的标签类型
TAG_TYPES = ['genre', 'star', 'studio', 'label', 'series', 'director']


def load_data():
    '''
    load data from database and do processing
    '''
    rate_type = RATE_TYPE.USER_RATE.value
    rate_value = None
    page = None
    items, _ = get_items(rate_type=rate_type, rate_value=rate_value,
                         page=page)
    return items


def as_dict(item):
    # 按类型分别提取标签（空标签自动处理为 []）
    tags_by_type = {}
    for tag_type in TAG_TYPES:
        tags_by_type[tag_type] = item.tags_dict.get(tag_type, [])

    d = {
        'id': item.fanhao,
        'fanhao': item.fanhao,
        'tags_by_type': tags_by_type,
        'target': item.rate_value
    }
    return d


def process_data(df):
    '''
    分类型处理标签特征，拼接为最终特征矩阵
    '''
    binarizers = {}

    # 对每种标签类型单独做 one-hot 编码
    feature_parts = []
    for tag_type in TAG_TYPES:
        col = f'tags_{tag_type}'
        values = df[col].values if col in df.columns else [[] for _ in range(len(df))]

        mlb = MultiLabelBinarizer()
        encoded = mlb.fit_transform(values)
        binarizers[tag_type] = mlb

        if encoded.shape[1] > 0:
            feature_parts.append(encoded)
            logger.info(f'{tag_type}: {encoded.shape[1]} 个特征值')

    # 拼接所有特征
    X = np.hstack(feature_parts)
    y = df[['target']].values.ravel()

    logger.info(f'总特征数: {X.shape[1]}, 样本数: {X.shape[0]}')

    # 保存所有 binarizer
    dump_model(get_data_path(BINARIZER_PATH), binarizers)

    return X, y


def split_data(X, y):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42)
    return (X_train, X_test, y_train, y_test)


def prepare_data():
    items = load_data()
    dicts = (as_dict(item) for item in items)
    df = pd.DataFrame(dicts)

    # 展开 tags_by_type 为独立的列
    for tag_type in TAG_TYPES:
        df[f'tags_{tag_type}'] = df['tags_by_type'].apply(
            lambda d: d.get(tag_type, []))

    X, y = process_data(df)
    return split_data(X, y)


def prepare_predict_data():
    # get not rated data
    rate_type = None
    rate_value = None
    page = None
    unrated_items, _ = get_items(
        rate_type=rate_type, rate_value=rate_value, page=page)

    if not unrated_items:
        logger.warning('no unrated items for prediction')
        return np.array([]), np.array([]).reshape(0, 0)

    binarizers = load_model(get_data_path(BINARIZER_PATH))
    dicts = list(as_dict(item) for item in unrated_items)

    if not dicts:
        return np.array([]), np.array([]).reshape(0, 0)

    df = pd.DataFrame(dicts)

    # 展开标签（安全检查）
    if 'tags_by_type' not in df.columns:
        df['tags_by_type'] = [{} for _ in range(len(df))]

    for tag_type in TAG_TYPES:
        df[f'tags_{tag_type}'] = df['tags_by_type'].apply(
            lambda d: d.get(tag_type, []) if isinstance(d, dict) else [])

    df.set_index('id', inplace=True)

    # 用训练时的 binarizer 转换特征
    feature_parts = []
    for tag_type in TAG_TYPES:
        col = f'tags_{tag_type}'
        values = df[col].values if col in df.columns else [[] for _ in range(len(df))]
        mlb = binarizers.get(tag_type)
        if mlb:
            encoded = mlb.transform(values)
            if encoded.shape[1] > 0:
                feature_parts.append(encoded)

    X = np.hstack(feature_parts)
    return df.index.values, X