'''
prepare data for model training
'''
import json
import operator
import pickle
import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from bustag.spider.db import get_items, RATE_TYPE, ItemRate, Item, get_tags_for_items
from bustag.model.persist import dump_model, load_model
from bustag.util import logger, get_data_path, MODEL_PATH

BINARIZER_PATH = MODEL_PATH + 'label_binarizer.pkl'

# 用于训练的标签类型（按重要性排序）
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
    # 按类型分别提取标签
    tags_by_type = {}
    for tag_type in TAG_TYPES:
        tags_by_type[tag_type] = item.tags_dict.get(tag_type, [])

    # 提取番号前缀作为系列特征（如 SSIS、ABP 等）
    fanhao_prefix = ''
    if item.fanhao:
        import re
        match = re.match(r'^([A-Z]+)', item.fanhao)
        if match:
            fanhao_prefix = match.group(1)

    # 提取视频时长
    length = 0
    try:
        meta = json.loads(item.meta_info) if hasattr(item, 'meta_info') else {}
        length_str = meta.get('length', '0')
        length = int(length_str) if length_str and length_str.isdigit() else 0
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass

    # 提取发行月份（季节性特征）
    release_month = 0
    try:
        if item.release_date:
            release_month = item.release_date.month if hasattr(item.release_date, 'month') else 0
    except (AttributeError, TypeError):
        pass

    # 电影类型（有码/无码）
    movie_type = getattr(item, 'movie_type', 'normal')

    d = {
        'id': item.fanhao,
        'title': item.title,
        'fanhao': item.fanhao,
        'url': item.url,
        'add_date': item.add_date,
        'tags_by_type': tags_by_type,
        'fanhao_prefix': fanhao_prefix,
        'length': length,
        'release_month': release_month,
        'movie_type': movie_type,
        'cover_img_url': item.cover_img_url if hasattr(item, 'cover_img_url') else '',
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
            logger.info(f'{tag_type}: {encoded.shape[1]} 个特征')

    # 番号前缀 one-hot 编码
    prefix_values = df['fanhao_prefix'].values
    mlb_prefix = MultiLabelBinarizer()
    prefix_encoded = mlb_prefix.fit_transform([[p] if p else [] for p in prefix_values])
    binarizers['prefix'] = mlb_prefix
    if prefix_encoded.shape[1] > 0:
        feature_parts.append(prefix_encoded)
        logger.info(f'prefix: {prefix_encoded.shape[1]} 个特征')

    # 视频时长（数值特征，标准化）
    length_values = df['length'].values.astype(float).reshape(-1, 1)
    length_mean = length_values.mean()
    length_std = length_values.std() if length_values.std() > 0 else 1
    length_normalized = (length_values - length_mean) / length_std
    feature_parts.append(length_normalized)
    binarizers['length_mean'] = length_mean
    binarizers['length_std'] = length_std
    logger.info(f'length: mean={length_mean:.1f}, std={length_std:.1f}')

    # 发行月份（周期特征：sin/cos）
    months = df['release_month'].values.astype(float)
    month_sin = np.sin(2 * np.pi * months / 12).reshape(-1, 1)
    month_cos = np.cos(2 * np.pi * months / 12).reshape(-1, 1)
    feature_parts.append(month_sin)
    feature_parts.append(month_cos)

    # 电影类型 one-hot
    movie_type_values = df['movie_type'].values
    mlb_mt = MultiLabelBinarizer()
    mt_encoded = mlb_mt.fit_transform([[mt] for mt in movie_type_values])
    binarizers['movie_type'] = mlb_mt
    if mt_encoded.shape[1] > 0:
        feature_parts.append(mt_encoded)

    # 拼接所有特征
    X = np.hstack(feature_parts)
    y = df[['target']].values.ravel()

    logger.info(f'总特征数: {X.shape[1]}, 样本数: {X.shape[0]}')

    # 保存所有 binarizer 和预处理参数
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

    binarizers = load_model(get_data_path(BINARIZER_PATH))
    dicts = (as_dict(item) for item in unrated_items)
    df = pd.DataFrame(dicts)

    # 展开标签
    for tag_type in TAG_TYPES:
        df[f'tags_{tag_type}'] = df['tags_by_type'].apply(
            lambda d: d.get(tag_type, []))

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

    # 番号前缀
    prefix_values = df['fanhao_prefix'].values
    mlb_prefix = binarizers.get('prefix')
    if mlb_prefix:
        prefix_encoded = mlb_prefix.transform([[p] if p else [] for p in prefix_values])
        if prefix_encoded.shape[1] > 0:
            feature_parts.append(prefix_encoded)

    # 视频时长
    length_values = df['length'].values.astype(float).reshape(-1, 1)
    length_mean = binarizers.get('length_mean', 0)
    length_std = binarizers.get('length_std', 1)
    length_normalized = (length_values - length_mean) / length_std
    feature_parts.append(length_normalized)

    # 发行月份
    months = df['release_month'].values.astype(float)
    month_sin = np.sin(2 * np.pi * months / 12).reshape(-1, 1)
    month_cos = np.cos(2 * np.pi * months / 12).reshape(-1, 1)
    feature_parts.append(month_sin)
    feature_parts.append(month_cos)

    # 电影类型
    movie_type_values = df['movie_type'].values
    mlb_mt = binarizers.get('movie_type')
    if mlb_mt:
        mt_encoded = mlb_mt.transform([[mt] for mt in movie_type_values])
        if mt_encoded.shape[1] > 0:
            feature_parts.append(mt_encoded)

    X = np.hstack(feature_parts)
    return df.index.values, X