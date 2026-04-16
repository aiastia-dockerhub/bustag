'''
persist data to db
支持 SQLite（默认）和 MySQL（通过配置切换）
'''
from datetime import date
import datetime
import operator
from functools import reduce
import json
from peewee import *
from enum import IntEnum
from collections import defaultdict
from bustag.util import logger, get_data_path, format_datetime, get_now_time, get_full_url

DB_FILE = 'bus.db'


def _create_db():
    '''根据配置创建数据库连接，支持 sqlite 和 mysql'''
    try:
        from bustag.util import APP_CONFIG
        db_type = APP_CONFIG.get('database.type', 'sqlite').lower().strip()
    except Exception:
        db_type = 'sqlite'

    if db_type == 'mysql':
        try:
            from playhouse.pool import PooledMySQLDatabase
            mysql_db = PooledMySQLDatabase(
                database=APP_CONFIG.get('database.name', 'bustag'),
                host=APP_CONFIG.get('database.host', 'localhost'),
                port=int(APP_CONFIG.get('database.port', '3306')),
                user=APP_CONFIG.get('database.user', 'root'),
                password=APP_CONFIG.get('database.password', ''),
                charset='utf8mb4',
                max_connections=8,
                stale_timeout=300,
            )
            logger.info(f'Using MySQL: {APP_CONFIG.get("database.host")}/{APP_CONFIG.get("database.name")}')
            return mysql_db
        except ImportError:
            logger.warning('pymysql not installed, falling back to SQLite')
        except Exception as e:
            logger.warning(f'MySQL connection failed: {e}, falling back to SQLite')

    # 默认使用 SQLite
    sqlite_db = SqliteDatabase(get_data_path(DB_FILE), pragmas={
        'journal_mode': 'wal'})
    logger.info('Using SQLite')
    return sqlite_db


db = _create_db()


class BaseModel(Model):

    class Meta:
        database = db
        legacy_table_names = False


class ExistError(Exception):
    pass


class DBError(Exception):
    pass


class Item(BaseModel):
    '''
    item table
    '''
    title = CharField()
    fanhao = CharField(unique=True)
    url = CharField(unique=True)
    release_date = DateField()
    add_date = DateTimeField(default=datetime.datetime.now)
    meta_info = TextField()
    # 影片类型：normal=有码, uncensored=无码
    movie_type = CharField(default='normal')

    def __repr__(self):
        return f'<Item:{self.fanhao} {self.title}>'

    @staticmethod
    def saveit(meta_info, movie_type='normal'):
        item_release_date = date.fromisoformat(meta_info.pop('release_date'))
        item_fanhao = meta_info.pop('fanhao')
        item_title = meta_info.pop('title')
        item_url = meta_info.pop('url')
        item_meta = json.dumps(meta_info)
        try:
            item = Item.create(fanhao=item_fanhao, title=item_title, url=item_url,
                               release_date=item_release_date, meta_info=item_meta,
                               movie_type=movie_type)
            logger.debug(f'save item:  {item}')
        except IntegrityError:
            logger.debug('Item exists: {item_fanhao}')
            raise ExistError()
        else:
            return item

    @staticmethod
    def loadit(item):
        item.url = get_full_url(item.url)
        meta = json.loads(item.meta_info)
        item.cover_img_url = meta['cover_img_url']
        series = item.fanhao.split('-')[0]
        item.add_date = format_datetime(item.add_date)

    @staticmethod
    def getit(id):
        item = Item.get_by_id(id)
        return item

    @staticmethod
    def get_by_fanhao(fanhao):
        item = Item.get_or_none(Item.fanhao == fanhao)
        return item

    @staticmethod
    def get_tags_dict(item):
        tags_dict = defaultdict(list)
        for t in item.tags_list:
            tags_dict[t.tag.type_].append(t.tag.value)
        item.tags_dict = tags_dict


class Tag(BaseModel):
    '''
    tag table
    '''
    type_ = CharField(column_name='type')
    value = CharField()
    url = CharField()

    class Meta:
        indexes = (
            # Specify a unique multi-column index
            (('type_', 'value'), True),
        )

    def __repr__(self):
        return f'<Tag {self.value}>'

    @staticmethod
    def saveit(tag_info):
        tag, created = Tag.get_or_create(type_=tag_info.type, value=tag_info.value,
                                         defaults={'url': tag_info.link})
        if created:
            logger.debug(f'save tag:  {tag}')
        return tag


class ItemTag(BaseModel):
    item = ForeignKeyField(Item, field='fanhao', backref='tags_list')
    tag = ForeignKeyField(Tag, backref='items')

    class Meta:
        indexes = (
            # Specify a unique multi-column index
            (('item', 'tag'), True),
        )

    @staticmethod
    def saveit(item, tag):
        item_tag, created = ItemTag.get_or_create(item=item, tag=tag)
        if created:
            logger.debug(f'save tag_item: {item_tag}')
        return item_tag

    def __repr__(self):
        return f'<ItemTag {self.item.fanhao} - {self.tag.value}>'


class RATE_TYPE(IntEnum):
    NOT_RATE = 0
    USER_RATE = 1
    SYSTEM_RATE = 2


class RATE_VALUE(IntEnum):
    LIKE = 1
    DISLIKE = 0


class ItemRate(BaseModel):
    rate_type = IntegerField()
    rate_value = IntegerField()
    item = ForeignKeyField(Item, field='fanhao',
                           backref='rated_items', unique=True)
    rete_time = DateTimeField(default=datetime.datetime.now)

    @staticmethod
    def saveit(rate_type, rate_value, fanhao):
        item_rate = None
        try:
            item_rate = ItemRate.create(
                item=fanhao, rate_type=rate_type, rate_value=rate_value)
            logger.debug(f'save ItemRate: {item_rate}')
        except IntegrityError:
            logger.debug(f'ItemRate exists: {fanhao}')
        else:
            return item_rate

    @staticmethod
    def getit(id):
        item_rate = ItemRate.get_or_none(ItemRate.id == id)
        return item_rate

    @staticmethod
    def get_by_fanhao(fanhao):
        item_rate = ItemRate.get_or_none(ItemRate.item_id == fanhao)
        return item_rate


class LocalItem(BaseModel):
    '''
    local item table
    '''
    item = ForeignKeyField(Item, field='fanhao',
                           backref='local_item', unique=True)
    path = CharField(null=True)
    size = IntegerField(null=True)
    add_date = DateTimeField(default=datetime.datetime.now)
    last_view_date = DateTimeField(null=True)
    view_times = IntegerField(default=0)

    @staticmethod
    def saveit(fanhao, path):
        local_item = None
        try:
            local_item = LocalItem.create(
                item=fanhao, path=path)
            logger.debug(f'save LocalItem: {fanhao}')
        except IntegrityError:
            logger.debug(f'LocalItem exists: {fanhao}')
        else:
            return local_item

    def __repr__(self):
        return f'<LocalItem {self.fanhao}({self.path})>'

    @staticmethod
    def update_play(id):
        nrows = (LocalItem
                 .update({LocalItem.last_view_date: get_now_time(),
                          LocalItem.view_times: LocalItem.view_times+1})
                 .where(LocalItem.id == id)
                 .execute())
        logger.debug(f'update LocalItem {id} : rows:{nrows}')
        return LocalItem.get_by_id(id)

    @staticmethod
    def loadit(local_item):
        local_item.last_view_date = format_datetime(
            local_item.last_view_date) if local_item.last_view_date else ''


def save(meta_info, tags, movie_type='normal'):
    item_title = meta_info['title']
    tag_objs = []
    try:
        item = Item.saveit(meta_info, movie_type=movie_type)
    except ExistError:
        logger.debug(f'item exists: {item_title}')
    else:
        with db.atomic():
            for tag_info in tags:
                tag = Tag.saveit(tag_info)
                if tag:
                    tag_objs.append(tag)
        with db.atomic():
            for tag_obj in tag_objs:
                ItemTag.saveit(item, tag_obj)


def test_save():
    item_url = 'https://www.cdnbus.bid/MADM-116'
    item_title = 'test item'
    item_fanhao = 'MADM-116'
    item_release_date = date(2019, 7, 19)
    item_meta_info = ''
    item = Item(title=item_title, url=item_url, fanhao=item_fanhao,
                release_date=item_release_date, meta_info=item_meta_info)
    item.save()

    tag1 = Tag.create(type_='genre', value='素人',
                      url='https://www.cdnbus.bid/genre/s1')
    tag2 = Tag.create(type_='star', value='樱田',
                      url='https://www.cdnbus.bid/star/dbd')
    tag3 = Tag.create(type_='genre', value='高清',
                      url='https://www.cdnbus.bid/genre/x1')
    ItemTag.create(item=item, tag=tag1)
    ItemTag.create(item=item, tag=tag2)

    ItemRate.saveit(RATE_TYPE.USER_RATE, RATE_VALUE.LIKE, item.fanhao)
    LocalItem.saveit('MADM-116', '/Download/MADM-116.avi')


def get_items(rate_type=None, rate_value=None, page=1, page_size=10, movie_type=None):
    '''
    get required items based on some conditions
    movie_type: None=全部, 'normal'=有码, 'uncensored'=无码
    '''
    items_list = []
    clauses = []
    if rate_type is not None:
        clauses.append(ItemRate.rate_type == rate_type)
    else:
        clauses.append(ItemRate.rate_type.is_null())
    if rate_value is not None:
        clauses.append(ItemRate.rate_value == rate_value)
    if movie_type is not None:
        clauses.append(Item.movie_type == movie_type)
    # 排序：添加日期(只取日期部分)降序 → 发行日期降序 → ID升序
    q = (Item.select(Item, ItemRate)
         .join(ItemRate, JOIN.LEFT_OUTER, attr='item_rate')
         .where(reduce(operator.and_, clauses))
         .order_by(fn.date(Item.add_date).desc(), Item.release_date.desc(), Item.id.asc())
         )
    total_items = q.count()
    if not page is None:
        q = q.paginate(page, page_size)
    items = get_tags_for_items(q)
    for item in items:
        Item.loadit(item)
        if hasattr(item, 'item_rate'):
            item.rate_value = item.item_rate.rate_value
        else:
            item.rate_value = None
        items_list.append(item)

    total_pages = (total_items + page_size - 1) // page_size
    page_info = (total_items, total_pages, page, page_size)
    return items_list, page_info


def get_local_items(page=1, page_size=10):
    '''
    get local items
    '''
    items = []
    q = (LocalItem.select(LocalItem)
         .where(LocalItem.path.is_null(False))
         .order_by(LocalItem.id.desc())
         )
    total_items = q.count()
    if not page is None:
        q = q.paginate(page, page_size)

    item_query = Item.select()
    item_tag_query = ItemTag.select()
    tag_query = Tag.select()
    items_with_tags = prefetch(q, item_query, item_tag_query, tag_query)

    for local_item in items_with_tags:
        try:
            Item.loadit(local_item.item)
            Item.get_tags_dict(local_item.item)
            items.append(local_item)
        except Exception:
            pass

    total_pages = (total_items + page_size - 1) // page_size
    page_info = (total_items, total_pages, page, page_size)
    return items, page_info


def get_today_update_count():
    now = get_now_time()
    year, month, day = now.year, now.month, now.day
    q = Item.select().where((Item.add_date.year == year)
                            & (Item.add_date.month == month)
                            & (Item.add_date.day == day)
                            )
    return q.count()


def get_today_recommend_count():
    now = get_now_time()
    year, month, day = now.year, now.month, now.day
    q = ItemRate.select().where((ItemRate.rete_time.year == year)
                                & (ItemRate.rete_time.month == month)
                                & (ItemRate.rete_time.day == day)
                                & (ItemRate.rate_type == RATE_TYPE.SYSTEM_RATE)
                                & (ItemRate.rate_value == RATE_VALUE.LIKE)
                                )
    return q.count()


def get_genre_tags():
    '''
    获取所有 genre 类型的标签，按字母排序
    '''
    tags = (Tag.select(Tag.value)
            .where(Tag.type_ == 'genre')
            .order_by(Tag.value)
            .distinct())
    return [t.value for t in tags]


def get_items_by_tag(tag_value, page=1, page_size=10):
    '''
    按标签值搜索关联的 Item，支持分页
    '''
    items_list = []
    tag = Tag.get_or_none(Tag.value == tag_value)
    if not tag:
        return items_list, (0, 0, 1, page_size)

    # 排序：添加日期(只取日期部分)降序 → 发行日期降序 → ID升序
    q = (Item.select(Item)
         .join(ItemTag, on=(ItemTag.item == Item.fanhao))
         .join(Tag, on=(ItemTag.tag == Tag.id))
         .where(Tag.value == tag_value)
         .order_by(fn.date(Item.add_date).desc(), Item.release_date.desc(), Item.id.asc())
         )
    total_items = q.count()
    if page is not None:
        q = q.paginate(page, page_size)
    items = get_tags_for_items(q)
    for item in items:
        Item.loadit(item)
        items_list.append(item)

    total_pages = (total_items + page_size - 1) // page_size
    page_info = (total_items, total_pages, page, page_size)
    return items_list, page_info


def get_tags_for_items(items_query):
    item_tag_query = ItemTag.select()
    tag_query = Tag.select()
    items_with_tags = prefetch(items_query, item_tag_query, tag_query)
    items = []
    for item in items_with_tags:
        Item.get_tags_dict(item)
        items.append(item)

    return items


def init():
    db.connect(reuse_if_open=True)
    db.create_tables([Item, Tag, ItemTag, ItemRate, LocalItem])
    # 自动迁移：旧数据库没有 movie_type 字段时自动添加
    try:
        columns = [col.name for col in db.get_columns('item')]
        if 'movie_type' not in columns:
            db.execute_sql('ALTER TABLE item ADD COLUMN movie_type VARCHAR(20) DEFAULT \'normal\'')
            logger.info('Database migrated: added movie_type column to item table')
    except Exception as e:
        logger.warning(f'Database migration check: {e}')


init()
