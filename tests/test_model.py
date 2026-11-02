import json
from datetime import date
import numpy as np
import pytest
from bustag.model import classifier as clf
from bustag.model.operations import model_operation, ModelBusyError
from bustag.spider.db import Item, ItemRate, RATE_TYPE


def add_unrated(count):
    return [Item.create(fanhao=f'NEW-{index}', title='New', url=f'https://example.com/new/{index}',
                        release_date=date.today(), meta_info='{}') for index in range(count)]


def test_train_atomic_bundle(seeded_data):
    clf.train()
    bundle = clf.load_bundle()
    assert bundle['format'] == 2
    assert bundle['model'].n_features_in_ == sum(info['count'] for info in bundle['feature_names'].values())
    assert 'f1' in bundle['scores']
    assert 'cv_f1_mean' not in bundle['scores']


def test_exact_chunk_multiple_and_snapshot(seeded_data, monkeypatch):
    clf.train()
    rows = add_unrated(4)
    monkeypatch.setitem(clf.APP_CONFIG, 'model.predict_chunk_size', '2')
    original = clf.prepare_predict_data
    calls = []
    def prepare(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            add_unrated(0)
            Item.create(fanhao='LATER-1', title='Later', url='https://example.com/later',
                        release_date=date.today(), meta_info='{}')
        return original(**kwargs)
    monkeypatch.setattr(clf, 'prepare_predict_data', prepare)
    assert clf.recommend()[0] == 4
    assert ItemRate.select().where(ItemRate.rate_type == RATE_TYPE.SYSTEM_RATE).count() == 4
    assert ItemRate.get_by_fanhao('LATER-1') is None
    assert calls[0]['after_id'] < calls[1]['after_id']


def test_concurrent_user_tag_is_preserved(seeded_data, monkeypatch):
    clf.train()
    item = add_unrated(1)[0]
    original = clf.prepare_predict_data
    def prepare(**kwargs):
        result = original(**kwargs)
        if len(result[0]):
            ItemRate.create(item=item.fanhao, rate_type=RATE_TYPE.USER_RATE, rate_value=1)
        return result
    monkeypatch.setattr(clf, 'prepare_predict_data', prepare)
    assert clf.recommend()[0] == 1
    rate = ItemRate.get_by_fanhao(item.fanhao)
    assert rate.rate_type == RATE_TYPE.USER_RATE and rate.rate_value == 1


def test_busy_reset_does_not_delete_recommendations(seeded_data):
    ItemRate.update(rate_type=RATE_TYPE.SYSTEM_RATE).execute()
    with model_operation():
        assert clf.recommend(reset=True) is None
        with pytest.raises(ModelBusyError):
            clf.clear_recommend()
    assert ItemRate.select().count() == 240


def test_missing_model_reset_keeps_old_results(seeded_data):
    ItemRate.update(rate_type=RATE_TYPE.SYSTEM_RATE).execute()
    with pytest.raises(FileNotFoundError):
        clf.recommend(reset=True)
    assert ItemRate.select().count() == 240


def test_full_evaluation_and_legacy_model(seeded_data):
    from bustag.model.persist import dump_model
    from bustag.util import get_data_path
    from bustag.model.prepare import BINARIZER_PATH
    clf.train(full_evaluation=True)
    bundle = clf.load_bundle()
    assert 'cv_f1_mean' in bundle['scores']
    # Older installs publish a tuple and separate dense-output encoders.
    for encoder in bundle['binarizers'].values():
        if hasattr(encoder, 'sparse_output'):
            encoder.sparse_output = False
    dump_model(get_data_path(clf.MODEL_FILE), (bundle['model'], bundle['scores']))
    dump_model(get_data_path(BINARIZER_PATH), bundle['binarizers'])
    add_unrated(1)
    assert clf.recommend()[0] == 1


def test_user_upsert_replaces_prediction_and_survives_deletion(seeded_data):
    item = add_unrated(1)[0]
    ItemRate.create(item=item.fanhao, rate_type=RATE_TYPE.SYSTEM_RATE, rate_value=0)
    ItemRate.set_user_rating(item.fanhao, 1)
    rate = ItemRate.get_by_fanhao(item.fanhao)
    assert rate.rate_type == RATE_TYPE.USER_RATE and rate.rate_value == 1
    ItemRate.delete().where(ItemRate.item == item.fanhao).execute()
    ItemRate.set_user_rating(item.fanhao, 0)
    assert ItemRate.get_by_fanhao(item.fanhao).rate_type == RATE_TYPE.USER_RATE
