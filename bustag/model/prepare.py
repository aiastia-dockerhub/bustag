'''
prepare data for model training
增强特征工程：按标签类型分别编码 + 数值特征
'''
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from bustag.spider.db import get_items, RATE_TYPE
from bustag.model.persist import dump_model, load_model
from bustag.util import logger, get_data_path, MODEL_PATH

BINARIZER_PATH = MODEL_PATH + 'label_binarizer.pkl'
FEATURE_NAMES_PATH = MODEL_PATH + 'feature_names.pkl'

# 标签类型优先级（影响特征重要性）
TAG_TYPES = ['genre', 'star', 'label', 'director', 'maker', 'series']


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
    '''
    将 item 转换为字典，结构化提取各类特征
    '''
    # 按类型分组标签
    tags_by_type = {}
    for tag_type, tags in item.tags_dict.items():
        tags_by_type[tag_type] = list(tags)

    # 提取系列信息（番号前缀）
    series = item.fanhao.split('-')[0] if item.fanhao else ''

    # 计算发行日期距今天数
    days_since_release = None
    if item.release_date:
        try:
            if isinstance(item.release_date, datetime):
                delta = datetime.now() - item.release_date
            else:
                release = datetime.strptime(str(item.release_date), '%Y-%m-%d')
                delta = datetime.now() - release
            days_since_release = max(delta.days, 0)
        except (ValueError, TypeError):
            days_since_release = None

    d = {
        'id': item.fanhao,
        'title': item.title,
        'fanhao': item.fanhao,
        'url': item.url,
        'add_date': item.add_date,
        'tags_by_type': tags_by_type,
        'genre_tags': set(tags_by_type.get('genre', [])),
        'star_tags': set(tags_by_type.get('star', [])),
        'other_tags': set(),
        'tag_count': sum(len(v) for v in tags_by_type.values()),
        'genre_count': len(tags_by_type.get('genre', [])),
        'star_count': len(tags_by_type.get('star', [])),
        'days_since_release': days_since_release,
        'series': series,
        'cover_img_url': item.cover_img_url,
        'target': item.rate_value
    }

    # 收集其他类型的标签
    for tag_type in tags_by_type:
        if tag_type not in ('genre', 'star'):
            d['other_tags'].update(tags_by_type[tag_type])

    return d


def _make_safe_columns(n):
    '''生成安全列名 f_0, f_1, ... 避免 LightGBM JSON 特殊字符问题'''
    return [f'f_{i}' for i in range(n)]


def _encode_tag_type(tag_sets, binarizer=None, fit=False):
    '''
    对某一类标签进行 multi-hot 编码
    Args:
        tag_sets: Series of sets
        binarizer: 已有的 MultiLabelBinarizer（预测时使用）
        fit: 是否训练（fit）新的 binarizer
    Returns:
        (encoded_array, binarizer, feature_names)
    '''
    if fit:
        binarizer = MultiLabelBinarizer(sparse_output=False)
        encoded = binarizer.fit_transform(tag_sets.values)
    else:
        # 处理未见过的标签：先 transform，如果维度不匹配则补零
        try:
            encoded = binarizer.transform(tag_sets.values)
        except ValueError:
            # 有些标签不在训练集中，需要手动编码
            classes = set(binarizer.classes_)
            encoded = np.array([
                [1 if t in classes else 0 for t in tags]
                for tags in tag_sets.values
            ])
            if encoded.shape[1] < len(binarizer.classes_):
                # 补齐缺失的列
                pad = np.zeros((encoded.shape[0], len(binarizer.classes_) - encoded.shape[1]))
                encoded = np.hstack([encoded, pad])
            elif encoded.shape[1] > len(binarizer.classes_):
                # 只保留训练集中的标签列
                encoded = encoded[:, :len(binarizer.classes_)]

    columns = _make_safe_columns(encoded.shape[1])
    return encoded, binarizer, columns


def process_data(df):
    '''
    增强特征处理：
    1. 按标签类型（genre/star/other）分别 multi-hot 编码
    2. 添加数值特征：tag_count, genre_count, star_count, has_star
    3. 添加 series one-hot 编码
    '''
    feature_names = {}
    all_features = []
    col_offset = 0

    # --- 1. Genre 标签编码 ---
    genre_encoded, genre_mlb, genre_cols = _encode_tag_type(
        df['genre_tags'], fit=True)
    all_features.append(genre_encoded)
    feature_names['genre'] = {
        'start': col_offset,
        'count': genre_encoded.shape[1],
        'classes': list(genre_mlb.classes_)
    }
    col_offset += genre_encoded.shape[1]
    logger.info(f'Genre features: {genre_encoded.shape[1]} tags')

    # --- 2. Star 标签编码 ---
    star_encoded, star_mlb, star_cols = _encode_tag_type(
        df['star_tags'], fit=True)
    all_features.append(star_encoded)
    feature_names['star'] = {
        'start': col_offset,
        'count': star_encoded.shape[1],
        'classes': list(star_mlb.classes_)
    }
    col_offset += star_encoded.shape[1]
    logger.info(f'Star features: {star_encoded.shape[1]} tags')

    # --- 3. Other 标签编码（label, director, maker, series 等）---
    other_encoded, other_mlb, other_cols = _encode_tag_type(
        df['other_tags'], fit=True)
    all_features.append(other_encoded)
    feature_names['other'] = {
        'start': col_offset,
        'count': other_encoded.shape[1],
        'classes': list(other_mlb.classes_)
    }
    col_offset += other_encoded.shape[1]
    logger.info(f'Other tag features: {other_encoded.shape[1]} tags')

    # --- 4. Series one-hot 编码 ---
    series_mlb = MultiLabelBinarizer(sparse_output=False)
    # 将 series 包装为 set 以适配 MultiLabelBinarizer
    series_sets = df['series'].apply(lambda x: {x} if x else set())
    series_encoded = series_mlb.fit_transform(series_sets.values)
    # 只保留出现次数 >= 2 的 series，减少稀疏特征
    series_counts = df['series'].value_counts()
    frequent_series = set(series_counts[series_counts >= 2].index)
    if len(frequent_series) > 0:
        keep_indices = [i for i, c in enumerate(series_mlb.classes_)
                        if c in frequent_series]
        if keep_indices:
            series_encoded = series_encoded[:, keep_indices]
            series_classes = [series_mlb.classes_[i] for i in keep_indices]
        else:
            series_encoded = np.zeros((len(df), 0))
            series_classes = []
    else:
        series_classes = list(series_mlb.classes_)

    if series_encoded.shape[1] > 0:
        all_features.append(series_encoded)
        feature_names['series'] = {
            'start': col_offset,
            'count': series_encoded.shape[1],
            'classes': series_classes
        }
        col_offset += series_encoded.shape[1]
    logger.info(f'Series features: {series_encoded.shape[1]}')

    # --- 5. 数值特征 ---
    numeric_features = []
    numeric_names = []

    # tag_count: 总标签数
    numeric_features.append(df['tag_count'].values.astype(float))
    numeric_names.append('tag_count')

    # genre_count: 类型标签数
    numeric_features.append(df['genre_count'].values.astype(float))
    numeric_names.append('genre_count')

    # star_count: 演员数量
    numeric_features.append(df['star_count'].values.astype(float))
    numeric_names.append('star_count')

    # has_star: 是否有演员信息（二值）
    has_star = (df['star_count'].values > 0).astype(float)
    numeric_features.append(has_star)
    numeric_names.append('has_star')

    numeric_array = np.column_stack(numeric_features)
    all_features.append(numeric_array)
    feature_names['numeric'] = {
        'start': col_offset,
        'count': len(numeric_names),
        'names': numeric_names
    }
    col_offset += len(numeric_names)
    logger.info(f'Numeric features: {len(numeric_names)}')

    # --- 合并所有特征 ---
    X_array = np.hstack(all_features)
    columns = _make_safe_columns(X_array.shape[1])
    X = pd.DataFrame(X_array, columns=columns)
    y = df['target'].values.ravel()

    # 保存编码器和特征名称映射
    binarizers = {
        'genre': genre_mlb,
        'star': star_mlb,
        'other': other_mlb,
        'series': series_mlb,
        'frequent_series': list(frequent_series) if series_encoded.shape[1] > 0 else [],
    }
    dump_model(get_data_path(BINARIZER_PATH), binarizers)
    dump_model(get_data_path(FEATURE_NAMES_PATH), feature_names)

    logger.info(f'Total features: {X_array.shape[1]} '
                f'(genre={genre_encoded.shape[1]}, star={star_encoded.shape[1]}, '
                f'other={other_encoded.shape[1]}, series={series_encoded.shape[1]}, '
                f'numeric={len(numeric_names)})')

    return X, y


def split_data(X, y):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)
    return (X_train, X_test, y_train, y_test)


def prepare_data():
    items = load_data()
    dicts = [as_dict(item) for item in items]
    df = pd.DataFrame(dicts)
    X, y = process_data(df)
    return split_data(X, y)


def prepare_predict_data(page=1, page_size=1000):
    '''
    get not rated data for prediction

    Args:
        page: 页码，从 1 开始。None 表示一次性加载全部（旧行为，不推荐用于大数据集）
        page_size: 每页条数，默认 1000，分块预测以控制内存峰值
    Returns:
        (ids, X, page_info) - 当 page=None 时 page_info 为 None
    '''
    # get not rated data
    rate_type = None
    rate_value = None
    unrated_items, page_info = get_items(
        rate_type=rate_type, rate_value=rate_value, page=page,
        page_size=page_size)

    binarizers = load_model(get_data_path(BINARIZER_PATH))
    genre_mlb = binarizers['genre']
    star_mlb = binarizers['star']
    other_mlb = binarizers['other']
    series_mlb = binarizers['series']
    frequent_series = set(binarizers.get('frequent_series', []))

    dicts = [as_dict(item) for item in unrated_items]
    df = pd.DataFrame(dicts)
    df.set_index('id', inplace=True)

    all_features = []

    # Genre 编码
    genre_encoded, _, _ = _encode_tag_type(df['genre_tags'], genre_mlb, fit=False)
    all_features.append(genre_encoded)

    # Star 编码
    star_encoded, _, _ = _encode_tag_type(df['star_tags'], star_mlb, fit=False)
    all_features.append(star_encoded)

    # Other 编码
    other_encoded, _, _ = _encode_tag_type(df['other_tags'], other_mlb, fit=False)
    all_features.append(other_encoded)

    # Series 编码
    series_sets = df['series'].apply(lambda x: {x} if x else set())
    series_encoded_raw = series_mlb.transform(series_sets.values)
    if frequent_series:
        keep_indices = [i for i, c in enumerate(series_mlb.classes_)
                        if c in frequent_series]
        if keep_indices:
            series_encoded = series_encoded_raw[:, keep_indices]
        else:
            series_encoded = np.zeros((len(df), 0))
    else:
        series_encoded = series_encoded_raw
    if series_encoded.shape[1] > 0:
        all_features.append(series_encoded)

    # 数值特征
    numeric_features = []
    numeric_features.append(df['tag_count'].values.astype(float))
    numeric_features.append(df['genre_count'].values.astype(float))
    numeric_features.append(df['star_count'].values.astype(float))

    # has_star: 是否有演员信息（二值）
    has_star = (df['star_count'].values > 0).astype(float)
    numeric_features.append(has_star)

    numeric_array = np.column_stack(numeric_features)
    all_features.append(numeric_array)

    # 合并
    X_array = np.hstack(all_features)
    columns = _make_safe_columns(X_array.shape[1])
    X = pd.DataFrame(X_array, columns=columns)

    return df.index.values, X, page_info