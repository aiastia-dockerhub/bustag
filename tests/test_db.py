from playhouse.test_utils import count_queries
from bustag.spider.db import (Item, ItemRate, Tag, ItemTag, RATE_TYPE, db, get_items,
                              get_items_by_tag_id, get_feature_items, get_today_update_count,
                              get_today_recommend_count, init)


def test_get_items_sorted_and_paginated(seeded_data):
    items, page = get_items(RATE_TYPE.USER_RATE, page=1)
    assert len(items) == 10 and page[:2] == (240, 24)
    assert all(item.rate_value in (0, 1) for item in items)
    assert [item.add_date[:10] for item in items] == sorted(
        [item.add_date[:10] for item in items], reverse=True)


def test_tags_prefetched(seeded_data):
    with count_queries() as counter:
        items = get_feature_items(user_rated=True)
        assert len(items) == 240
        assert all(item.tags_dict for item in items)
        assert {item.rate_value for item in items} == {0, 1}
    assert counter.count == 3


def test_today_bounds(seeded_data):
    assert get_today_update_count() == 80
    assert get_today_recommend_count() == 0
    ItemRate.update(rate_type=RATE_TYPE.SYSTEM_RATE).execute()
    assert get_today_recommend_count() == 120


def test_tag_id_does_not_match_other_type(seeded_data):
    genre = Tag.get(Tag.type_ == 'genre')
    duplicate_name = Tag.create(type_='star', value=genre.value, url='/star/other')
    item = Item.get_by_id(1)
    ItemTag.create(item=item.fanhao, tag=duplicate_name)
    items, page = get_items_by_tag_id(genre.id, page=None)
    assert page[0] == 120
    assert item.fanhao not in {row.fanhao for row in items}


def test_existing_db_migration(seeded_data):
    db.execute_sql('DROP INDEX item_day_sort')
    db.execute_sql('DROP INDEX item_type_day_sort')
    db.execute_sql('ALTER TABLE item DROP COLUMN add_day')
    init()
    assert Item.get_by_id(1).add_day is not None
    before = Item.select().count()
    init()
    assert Item.select().count() == before
    plan = db.execute_sql('EXPLAIN QUERY PLAN SELECT * FROM item WHERE movie_type = ? '
                          'ORDER BY add_day DESC, release_date DESC, id ASC LIMIT 10', ('normal',)).fetchall()
    assert any('item_type_day_sort' in str(row) for row in plan)
    assert not any('TEMP B-TREE' in str(row) for row in plan)
