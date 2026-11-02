import numpy as np
import pandas as pd
from scipy import sparse
from bustag.model.prepare import (load_data, as_dict, process_data, prepare_data,
                                  prepare_predict_data, fit_features, transform_features)


def test_sparse_features(seeded_data):
    items = load_data()
    assert len(items) == 240
    df = pd.DataFrame(map(as_dict, items))
    X, y = process_data(df, persist=False)
    assert sparse.isspmatrix_csr(X) and X.dtype == np.float32
    assert X.shape[0] == len(y) == 240
    assert X.nnz < X.shape[0] * X.shape[1]


def test_prepare_data(seeded_data):
    train, test, y_train, y_test = prepare_data()
    assert train.shape[0] == 180 and test.shape[0] == 60
    assert train.shape[1] == test.shape[1]
    assert set(y_train) == set(y_test) == {0, 1}


def test_empty_prediction_needs_no_model():
    ids, X, cursor = prepare_predict_data()
    assert len(ids) == X.shape[0] == 0
    assert cursor is None


def test_unknown_labels_and_series_keep_column_order(seeded_data):
    df = pd.DataFrame(map(as_dict, load_data()))
    encoders, _ = fit_features(df)
    expected = transform_features(df, encoders)
    df.loc[0, 'genre_tags'].add('unknown-genre')
    actual = transform_features(df, encoders)
    assert (actual != expected).nnz == 0
