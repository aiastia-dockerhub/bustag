import pytest
from bustag.spider.parser import parse_movie_detail, parse_movie_list_item, create_tag


def test_parse_movie_detail():
    detail = {
        'id': 'SSIS-406',
        'title': 'SSIS-406 test movie title',
        'img': 'https://example.com/cover.jpg',
        'date': '2022-05-20',
        'videoLength': 120,
        'director': {'id': 'hh', 'name': 'test_director'},
        'producer': {'id': '7q', 'name': 'test_producer'},
        'publisher': {'id': '9x', 'name': 'test_publisher'},
        'series': {'id': 'xx', 'name': 'test_series'},
        'genres': [
            {'id': 'e', 'name': 'genre1'},
            {'id': 'f', 'name': 'genre2'},
        ],
        'stars': [
            {'id': '2xi', 'name': 'star1'},
            {'id': '3xi', 'name': 'star2'},
        ],
    }
    meta, tags = parse_movie_detail(detail)
    assert meta['fanhao'] == 'SSIS-406'
    assert meta['title'] == 'test movie title'
    assert meta['cover_img_url'] == 'https://example.com/cover.jpg'
    assert meta['release_date'] == '2022-05-20'
    assert meta['length'] == '120'
    tag_types = [t.type for t in tags]
    assert 'director' in tag_types
    assert 'studio' in tag_types
    assert 'label' in tag_types
    assert 'series' in tag_types
    assert 'genre' in tag_types
    assert 'star' in tag_types
    assert len(tags) == 7


def test_parse_movie_detail_no_extras():
    detail = {
        'id': 'SSIS-406',
        'title': 'SSIS-406 test title',
        'img': 'https://example.com/cover.jpg',
        'date': '2022-05-20',
        'videoLength': 120,
        'director': None,
        'producer': None,
        'publisher': None,
        'series': None,
        'genres': [],
        'stars': [],
    }
    meta, tags = parse_movie_detail(detail)
    assert meta['fanhao'] == 'SSIS-406'
    assert len(tags) == 0


def test_parse_movie_list_item():
    item = {
        'id': 'SSIS-406',
        'title': 'test title',
        'img': 'https://example.com/cover.jpg',
        'date': '2022-05-20',
        'tags': ['HD', 'subtitle'],
    }
    result = parse_movie_list_item(item)
    assert result['id'] == 'SSIS-406'
    assert result['title'] == 'test title'
    assert result['date'] == '2022-05-20'


def test_create_tag():
    tag = create_tag('genre', 'test', '/genre/1')
    assert tag.type == 'genre'
    assert tag.value == 'test'
    assert tag.link == '/genre/1'
