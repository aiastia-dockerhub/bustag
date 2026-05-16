from bustag.model.prepare import load_data, process_data, prepare_predict_data, prepare_data


def test_load_data():
    items = load_data()
    print(len(items))
    item = items[0]
    print(item.fanhao, item.tags_dict)
    assert len(items) > 0


def test_process_data():
    items = load_data()
    from bustag.model.prepare import as_dict
    dicts = [as_dict(item) for item in items]
    import pandas as pd
    df = pd.DataFrame(dicts)
    X, y = process_data(df)
    print(f'Feature matrix shape: {X.shape}')
    print(f'Labels shape: {y.shape}')
    assert X.shape[0] == y.shape[0]
    assert X.shape[1] > 0


def test_prepare_data():
    X_train, X_test, y_train, y_test = prepare_data()
    print(f'Train: {X_train.shape}, Test: {X_test.shape}')
    assert X_train.shape[0] > X_test.shape[0]


def test_prepare_predict_data():
    ids, X = prepare_predict_data()
    print(f'Predict data shape: {X.shape}')
    if len(X) > 0:
        print(f'Sample features: {X.iloc[0].values[:10]}')
    print(f'IDs count: {len(ids)}')