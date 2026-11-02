"""Sparse float32 features shared by training and incremental inference."""
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from bustag.spider.db import get_feature_items, Item, fn
from bustag.model.persist import dump_model, load_model
from bustag.util import get_data_path, MODEL_PATH

BINARIZER_PATH = MODEL_PATH + 'label_binarizer.pkl'
FEATURE_NAMES_PATH = MODEL_PATH + 'feature_names.pkl'
TAG_TYPES = ['genre', 'star', 'label', 'director', 'maker', 'series']
NUMERIC_NAMES = ['tag_count', 'genre_count', 'star_count', 'has_star']


def load_data():
    items = []
    after_id = 0
    max_id = Item.select(fn.MAX(Item.id)).scalar() or 0
    while after_id < max_id:
        batch = get_feature_items(after_id, max_id, user_rated=True)
        if not batch:
            break
        items.extend(batch)
        after_id = batch[-1].id
    return items


def as_dict(item):
    tags = item.tags_dict
    genre = set(tags.get('genre', []))
    star = set(tags.get('star', []))
    other = {value for kind, values in tags.items()
             if kind not in ('genre', 'star') for value in values}
    return {
        'id': item.fanhao,
        'genre_tags': genre, 'star_tags': star, 'other_tags': other,
        'series': item.fanhao.split('-')[0],
        'tag_count': sum(map(len, tags.values())),
        'genre_count': len(genre), 'star_count': len(star),
        'target': getattr(item, 'rate_value', None),
    }


def _make_safe_columns(n):
    return [f'f_{i}' for i in range(n)]


def _encode_tag_type(tag_sets, binarizer=None, fit=False):
    if fit:
        binarizer = MultiLabelBinarizer(sparse_output=True)
        matrix = binarizer.fit_transform(tag_sets)
    else:
        # Filter unknown labels without building huge warning strings or dense arrays.
        known = set(binarizer.classes_)
        values = [set(tags) & known for tags in tag_sets]
        # Legacy encoders use dense output. Construct an equivalent sparse encoder.
        encoder = MultiLabelBinarizer(classes=binarizer.classes_, sparse_output=True)
        encoder.fit([[]])
        matrix = encoder.transform(values)
    return matrix.astype(np.float32), binarizer, _make_safe_columns(matrix.shape[1])


def fit_features(df):
    binarizers, names, offset = {}, {}, 0
    for kind in ('genre', 'star', 'other', 'series'):
        values = df[f'{kind}_tags'] if kind != 'series' else [
            {value} if value else set() for value in df['series']]
        encoder = MultiLabelBinarizer(sparse_output=True)
        if kind == 'series':
            counts = df['series'].value_counts()
            frequent = set(counts[counts >= 2].index)
            values = [tags & frequent for tags in values]
            binarizers['frequent_series'] = sorted(frequent)
        encoder.fit(values)
        binarizers[kind] = encoder
        names[kind] = {'start': offset, 'count': len(encoder.classes_),
                       'classes': list(encoder.classes_)}
        offset += len(encoder.classes_)
    names['numeric'] = {'start': offset, 'count': 4, 'names': NUMERIC_NAMES}
    return binarizers, names


def transform_features(df, binarizers):
    matrices = []
    for kind in ('genre', 'star', 'other', 'series'):
        values = df[f'{kind}_tags'] if kind != 'series' else [
            {value} if value else set() for value in df['series']]
        matrix, _, _ = _encode_tag_type(values, binarizers[kind])
        # Preserve the column subset of older three-file models.
        if kind == 'series' and binarizers.get('frequent_series'):
            keep = set(binarizers['frequent_series'])
            indices = [i for i, value in enumerate(binarizers[kind].classes_) if value in keep]
            matrix = matrix[:, indices]
        matrices.append(matrix)
    numeric = np.column_stack([
        df['tag_count'], df['genre_count'], df['star_count'],
        np.asarray(df['star_count']) > 0]).astype(np.float32)
    matrices.append(sparse.csr_matrix(numeric))
    return sparse.hstack(matrices, format='csr', dtype=np.float32)


def process_data(df, persist=True):
    binarizers, names = fit_features(df)
    X = transform_features(df, binarizers)
    if persist:
        dump_model(get_data_path(BINARIZER_PATH), binarizers)
        dump_model(get_data_path(FEATURE_NAMES_PATH), names)
    return X, df['target'].to_numpy()


def split_data(X, y):
    return train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)


def prepare_data(return_metadata=False):
    df = pd.DataFrame([as_dict(item) for item in load_data()])
    if df.empty or df['target'].nunique() < 2:
        raise ValueError('训练数据需同时包含喜欢和不喜欢两个类别')
    # Fit vocabulary on the training partition only, never on the held-out test data.
    train, test = train_test_split(df, test_size=0.25, random_state=42, stratify=df['target'])
    binarizers, names = fit_features(train)
    result = (transform_features(train, binarizers), transform_features(test, binarizers),
              train['target'].to_numpy(), test['target'].to_numpy())
    if return_metadata:
        return (*result, binarizers, names)
    return result


def prepare_predict_data(page=1, page_size=1000, *, after_id=0, max_id=None,
                         binarizers=None):
    # OFFSET is only retained for legacy callers; the recommendation task uses an ID cursor.
    if page not in (1, None):
        raise ValueError('预测请使用 after_id 游标分页')
    items = get_feature_items(after_id, max_id, page_size=page_size)
    if not items:
        return np.array([], dtype=object), sparse.csr_matrix((0, 0), dtype=np.float32), None
    if binarizers is None:
        binarizers = load_model(get_data_path(BINARIZER_PATH))
    df = pd.DataFrame([as_dict(item) for item in items])
    return df['id'].to_numpy(), transform_features(df, binarizers), items[-1].id
