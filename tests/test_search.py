import json
from urllib.parse import urlencode

import bottle
from test_auth import call_app
from bustag.spider.db import Item, ItemRate


def search(**params):
    status, _, body = call_app(bottle.default_app(), 'GET', '/api/search',
                               headers={'QUERY_STRING': urlencode(params)})
    assert status == 200
    return json.loads(body)


def test_title_search_pagination_and_rating(seeded_data):
    first = search(q='Movie', rate_filter='liked')
    assert first['item'] is None
    assert first['page_info']['total_items'] == 120
    assert len(first['tag_items']) == 10
    assert all(item['rate_value'] == 1 for item in first['tag_items'])
    second = search(q='Movie', rate_filter='liked', page=2)
    assert not ({item['fanhao'] for item in first['tag_items']} &
                {item['fanhao'] for item in second['tag_items']})


def test_exact_number_respects_rating_and_normalization(seeded_data):
    assert search(q='test0001', rate_filter='liked')['item']['fanhao'] == 'TEST-0001'
    assert search(q='test0001', rate_filter='disliked')['item'] is None
    assert search(q='TEST-00')['page_info']['total_items'] == 100


def test_unicode_title_and_unrated_filter(seeded_data):
    Item.update(title='夏日 100% 的约定').where(Item.fanhao == 'TEST-0001').execute()
    ItemRate.delete().where(ItemRate.item == 'TEST-0001').execute()
    result = search(q='夏日 100%', rate_filter='unrated')
    assert result['page_info']['total_items'] == 1
    assert result['tag_items'][0]['fanhao'] == 'TEST-0001'
    assert search(q='不存在的名称')['tag_items'] == []
