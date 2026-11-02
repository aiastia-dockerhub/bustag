import json
import bottle
from playhouse.test_utils import count_queries
from test_auth import call_app
from bustag.app import api
from bustag.spider.db import Item, ItemRate, Tag, touch_data


def test_search_rate_query_is_batched(seeded_data):
    items = list(Item.select().limit(50))
    for item in items:
        item.tags_dict = {}
    with count_queries() as count:
        api._enrich_items_with_rate(items)
    assert count.count == 1
    assert all(item.rate_type == 1 for item in items)


def test_dictionary_separate_and_etag(seeded_data):
    app = bottle.default_app()
    status, headers, body = call_app(app, 'GET', '/api/tags')
    assert status == 200 and len(json.loads(body)['star_tags']) == 1
    status, _, body = call_app(app, 'GET', '/api/tags', headers={'HTTP_IF_NONE_MATCH': headers['Etag']})
    assert status == 304 and not body
    status, _, body = call_app(app, 'GET', '/api/search', headers={'QUERY_STRING': 'q=TEST-0000'})
    data = json.loads(body)
    assert status == 200 and data['item']['tags_dict']['star']
    assert 'star_tags' not in data


def test_cache_invalidated_by_worker_revision(seeded_data):
    app = bottle.default_app()
    query = {'QUERY_STRING': 'like=1'}
    first = json.loads(call_app(app, 'GET', '/api/tagit', headers=query)[2])
    assert first['page_info']['total_items'] == 120
    ItemRate.delete().where(ItemRate.rate_value == 1).execute()
    touch_data()
    second = json.loads(call_app(app, 'GET', '/api/tagit', headers=query)[2])
    assert second['page_info']['total_items'] == 0


def test_job_submission_is_async():
    status, _, body = call_app(bottle.default_app(), 'POST', '/api/do-training', body={})
    assert status == 202
    assert json.loads(body)['job']['state'] == 'queued'


def test_cache_is_bounded():
    for index in range(1000):
        api._cache_set(str(index), {'value': index})
    assert len(api._api_cache) == 256
