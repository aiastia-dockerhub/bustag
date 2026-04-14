'''
数据解析模块
从 javbus-api 返回的 JSON 数据中提取影片信息
替代原有的 HTML 解析方式
'''
from collections import namedtuple

Tag = namedtuple('Tag', ['type', 'value', 'link'])


def parse_movie_detail(detail):
    '''
    解析影片详情 API 返回的 JSON 数据

    Args:
        detail: dict - API 返回的影片详情 JSON

    Returns:
        tuple: (dict, list)
        dict - meta 数据
        list - tag 列表
    '''
    meta = {}
    tag_list = []

    # 基本信息
    movie_id = detail.get('id', '')
    title = detail.get('title', '')
    # API 返回的 title 格式为 "SSIS-406 完整标题"，需要分离番号和标题
    if title.startswith(movie_id):
        title_text = title[len(movie_id):].strip()
    else:
        title_text = title

    meta['fanhao'] = movie_id
    meta['title'] = title_text
    meta['cover_img_url'] = detail.get('img', '')
    meta['release_date'] = detail.get('date', '')
    meta['length'] = str(detail.get('videoLength', ''))

    # 导演
    director = detail.get('director')
    if director and director.get('name'):
        tag_list.append(create_tag('director', director['name'], f"/director/{director.get('id', '')}"))

    # 制作商 (producer)
    producer = detail.get('producer')
    if producer and producer.get('name'):
        tag_list.append(create_tag('studio', producer['name'], f"/studio/{producer.get('id', '')}"))

    # 发行商 (publisher)
    publisher = detail.get('publisher')
    if publisher and publisher.get('name'):
        tag_list.append(create_tag('label', publisher['name'], f"/label/{publisher.get('id', '')}"))

    # 系列 (series)
    series = detail.get('series')
    if series and series.get('name'):
        tag_list.append(create_tag('series', series['name'], f"/series/{series.get('id', '')}"))

    # 类别 (genres)
    genres = detail.get('genres', [])
    for genre in genres:
        if genre.get('name'):
            tag_list.append(create_tag('genre', genre['name'], f"/genre/{genre.get('id', '')}"))

    # 演员 (stars)
    stars = detail.get('stars', [])
    for star in stars:
        if star.get('name'):
            tag_list.append(create_tag('star', star['name'], f"/star/{star.get('id', '')}"))

    return meta, tag_list


def parse_movie_list_item(movie_item):
    '''
    解析影片列表中的单个影片项

    Args:
        movie_item: dict - 列表 API 返回的单个影片 JSON

    Returns:
        dict: 影片基本信息（不含完整标签）
    '''
    return {
        'id': movie_item.get('id', ''),
        'title': movie_item.get('title', ''),
        'img': movie_item.get('img', ''),
        'date': movie_item.get('date', ''),
        'tags': movie_item.get('tags', [])
    }


def create_tag(tag_type, tag_value, tag_link):
    '''
    创建标签对象

    Args:
        tag_type: 标签类型 (genre/star/director/studio/label/series)
        tag_value: 标签值
        tag_link: 标签链接

    Returns:
        Tag: 命名元组
    '''
    return Tag(tag_type, tag_value, tag_link)