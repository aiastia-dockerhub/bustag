'''
persist data to db
支持 SQLite（默认）和 MySQL（通过配置切换）
'''
from datetime import date
import fcntl
import os
import datetime
import operator
from functools import reduce, lru_cache
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
        'journal_mode': 'wal', 'busy_timeout': 10000, 'cache_size': -16384})
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
    add_day = DateField(null=True)
    meta_info = TextField()
    # 影片类型：normal=有码, uncensored=无码
    movie_type = CharField(default='normal')

    def __repr__(self):
        return f'<Item:{self.fanhao} {self.title}>'

    def save(self, *args, **kwargs):
        # Keep the indexed day aligned with the original timestamp, including imports.
        if self.add_day is None or Item.add_date in self.dirty_fields:
            value = self.add_date
            self.add_day = value.date() if isinstance(value, datetime.datetime) else str(value)[:10]
        return super().save(*args, **kwargs)

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
    def search_by_fanhao(keyword, limit=50):
        '''
        模糊搜索番号，返回已加载标签与封面信息的 item 列表。
        SQLite 的 LIKE 默认对 ASCII 大小写不敏感，故 keyword 大小写均可。
        '''
        query = Item.select().where(Item.fanhao.contains(keyword)).limit(limit)
        items = get_tags_for_items(query)
        items_list = []
        for item in items:
            Item.loadit(item)
            items_list.append(item)
        return items_list

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
    def set_user_rating(fanhao, value):
        timestamp = get_now_time()
        query = ItemRate.insert(item=fanhao, rate_type=RATE_TYPE.USER_RATE,
                                rate_value=value, rete_time=timestamp)
        updates = {ItemRate.rate_type: RATE_TYPE.USER_RATE,
                   ItemRate.rate_value: value, ItemRate.rete_time: timestamp}
        options = {'update': updates}
        if not isinstance(db, MySQLDatabase):
            options['conflict_target'] = [ItemRate.item]
        with db.atomic():
            query.on_conflict(**options).execute()
            touch_data()

    @staticmethod
    def getit(id):
        item_rate = ItemRate.get_or_none(ItemRate.id == id)
        return item_rate

    @staticmethod
    def get_by_fanhao(fanhao):
        item_rate = ItemRate.get_or_none(ItemRate.item_id == fanhao)
        return item_rate


class SkipItem(BaseModel):
    '''
    跳过列表（404 不存在的番号等）
    与 Item 表分离，不影响前端显示
    '''
    fanhao = CharField(unique=True)
    reason = CharField(default='not_found')
    add_date = DateTimeField(default=datetime.datetime.now)

    @staticmethod
    def is_skipped(fanhao):
        '''检查番号是否在跳过列表中'''
        return SkipItem.get_or_none(SkipItem.fanhao == fanhao) is not None

    @staticmethod
    def add_skip(fanhao, reason='not_found'):
        '''添加番号到跳过列表'''
        try:
            SkipItem.create(fanhao=fanhao, reason=reason)
            logger.debug(f'Added to skip list: {fanhao}')
        except IntegrityError:
            logger.debug(f'SkipItem already exists: {fanhao}')


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
    with db.atomic():
        try:
            item = Item.saveit(dict(meta_info), movie_type=movie_type)
        except ExistError:
            return False
        tag_ids = [Tag.saveit(info).id for info in tags]
        if tag_ids:
            rows = [{'item': item.fanhao, 'tag': tag_id} for tag_id in set(tag_ids)]
            ItemTag.insert_many(rows).execute()
        touch_data()
    return True


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


def _list_filter(rate_type, rate_value, movie_type):
    rate = ItemRate.select(ItemRate.id).where(ItemRate.item == Item.fanhao)
    if rate_type is None:
        condition = ~fn.EXISTS(rate)
        if rate_value is not None:
            condition &= SQL('0 = 1')
    else:
        rate = rate.where(ItemRate.rate_type == rate_type)
        if rate_value is not None:
            rate = rate.where(ItemRate.rate_value == rate_value)
        condition = fn.EXISTS(rate)
    if movie_type is not None:
        condition &= Item.movie_type == movie_type
    return condition


@lru_cache(maxsize=128)
def _item_count(database, revision, rate_type, rate_value, movie_type):
    # Count without page sorting or selected metadata, shared by pages of the same filter.
    if rate_type is not None:
        query = ItemRate.select().join(Item).where(ItemRate.rate_type == rate_type)
        if rate_value is not None:
            query = query.where(ItemRate.rate_value == rate_value)
        if movie_type is not None:
            query = query.where(Item.movie_type == movie_type)
    else:
        query = Item.select(Item.id).where(_list_filter(rate_type, rate_value, movie_type))
    return query.count()


def get_items(rate_type=None, rate_value=None, page=1, page_size=10, movie_type=None):
    page_size = max(1, min(int(page_size), 5000))
    if page is not None:
        page = max(1, int(page))
    total = _item_count(str(db.database), data_revision(), rate_type, rate_value, movie_type)
    rating = ItemRate.select(ItemRate.rate_value).where(ItemRate.item == Item.fanhao).limit(1)
    # EXISTS keeps Item as the outer scan, so the day index can satisfy ORDER BY / LIMIT.
    query = (Item.select(Item, rating.alias('rate_value'))
             .where(_list_filter(rate_type, rate_value, movie_type))
             .order_by(Item.add_day.desc(), Item.release_date.desc(), Item.id.asc()))
    if page is not None:
        query = query.paginate(page, page_size)
    items = get_tags_for_items(query)
    for item in items:
        Item.loadit(item)
    return items, (total, (total + page_size - 1) // page_size, page, page_size)


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


def _today_bounds():
    start = get_now_time().replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + datetime.timedelta(days=1)


def get_today_update_count():
    start, end = _today_bounds()
    return Item.select().where(Item.add_date >= start, Item.add_date < end).count()


def get_today_recommend_count():
    start, end = _today_bounds()
    return ItemRate.select().where(
        ItemRate.rete_time >= start, ItemRate.rete_time < end,
        ItemRate.rate_type == RATE_TYPE.SYSTEM_RATE,
        ItemRate.rate_value == RATE_VALUE.LIKE).count()


def get_genre_tags():
    '''
    获取所有 genre 类型的标签，按字母排序，返回 {id, value} 列表
    '''
    tags = (Tag.select(Tag.id, Tag.value)
            .where(Tag.type_ == 'genre')
            .order_by(Tag.value)
            .distinct())
    return [{'id': t.id, 'value': t.value} for t in tags]


def get_star_tags():
    '''
    获取所有 star 类型的标签（女优），按字母排序，返回 {id, value} 列表
    '''
    tags = (Tag.select(Tag.id, Tag.value)
            .where(Tag.type_ == 'star')
            .order_by(Tag.value)
            .distinct())
    return [{'id': t.id, 'value': t.value} for t in tags]


def get_items_by_tag_id(tag_id, page=1, page_size=10, rate_filter=None):
    '''
    按标签 ID 搜索关联的 Item，支持分页和评分筛选
    rate_filter: None/'liked'/'disliked'/'recommended'/'unrated'
    '''
    items_list = []
    return _get_items_by_tag_clause(Tag.id == tag_id, page, page_size, rate_filter)


def get_items_by_tag(tag_value, page=1, page_size=10, rate_filter=None):
    return _get_items_by_tag_clause(Tag.value == tag_value, page, page_size, rate_filter)


def _get_items_by_tag_clause(clause, page, page_size, rate_filter):
    items_list = []
    clauses = [clause]

    if rate_filter in ('liked', 'disliked', 'recommended'):
        # 需要 INNER JOIN ItemRate（只返回有对应打标记录的）
        q = (Item.select(Item)
             .join(ItemTag, on=(ItemTag.item == Item.fanhao))
             .join(Tag, on=(ItemTag.tag == Tag.id))
             .switch(Item)
             .join(ItemRate, on=(ItemRate.item_id == Item.fanhao))
             )
        if rate_filter == 'liked':
            clauses.append(ItemRate.rate_type == RATE_TYPE.USER_RATE)
            clauses.append(ItemRate.rate_value == RATE_VALUE.LIKE)
        elif rate_filter == 'disliked':
            clauses.append(ItemRate.rate_type == RATE_TYPE.USER_RATE)
            clauses.append(ItemRate.rate_value == RATE_VALUE.DISLIKE)
        elif rate_filter == 'recommended':
            clauses.append(ItemRate.rate_type == RATE_TYPE.SYSTEM_RATE)
    elif rate_filter == 'unrated':
        # LEFT JOIN ItemRate，筛选没有打标记录的
        q = (Item.select(Item)
             .join(ItemTag, on=(ItemTag.item == Item.fanhao))
             .join(Tag, on=(ItemTag.tag == Tag.id))
             .switch(Item)
             .join(ItemRate, JOIN.LEFT_OUTER, on=(ItemRate.item_id == Item.fanhao))
             )
        clauses.append(ItemRate.id.is_null())
    else:
        # 无筛选，不 JOIN ItemRate
        q = (Item.select(Item)
             .join(ItemTag, on=(ItemTag.item == Item.fanhao))
             .join(Tag, on=(ItemTag.tag == Tag.id))
             )

    q = q.where(reduce(operator.and_, clauses)).order_by(
        Item.add_day.desc(), Item.release_date.desc(), Item.id.asc())

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


def get_feature_items(after_id=0, max_id=None, page_size=1000, user_rated=False):
    query = Item.select(Item.id, Item.fanhao)
    if user_rated:
        query = (Item.select(Item.id, Item.fanhao, ItemRate)
                 .join(ItemRate, attr='item_rate').where(ItemRate.rate_type == RATE_TYPE.USER_RATE))
    else:
        query = query.where(~fn.EXISTS(ItemRate.select(ItemRate.id).where(
            ItemRate.item == Item.fanhao)))
    query = query.where(Item.id > after_id)
    if max_id is not None:
        query = query.where(Item.id <= max_id)
    query = query.order_by(Item.id).limit(page_size)
    items = get_tags_for_items(query)
    if user_rated:
        for item in items:
            item.rate_value = item.item_rate.rate_value
    return items


class DataRevision(BaseModel):
    name = CharField(primary_key=True)
    version = BigIntegerField(default=0)


def touch_data():
    # A shared revision invalidates API caches across the web and worker processes.
    DataRevision.update(version=DataRevision.version + 1).where(
        DataRevision.name == 'data').execute()


def data_revision():
    return DataRevision.get_by_id('data').version


def ensure_indexes():
    definitions = {
        'item': {
            'item_day_sort': 'add_day DESC, release_date DESC, id ASC',
            'item_type_day_sort': 'movie_type, add_day DESC, release_date DESC, id ASC',
            'item_added': 'add_date',
        },
        'item_rate': {
            'rate_filter_item': 'rate_type, rate_value, item_id',
            'rate_today': 'rate_type, rate_value, rete_time',
        },
        'item_tag': {'tag_item_lookup': 'tag_id, item_id'},
    }
    for table, indexes in definitions.items():
        existing = {index.name for index in db.get_indexes(table)}
        for name, fields in indexes.items():
            if name not in existing:
                db.execute_sql(f'CREATE INDEX {name} ON {table} ({fields})')


def init():
    path = get_data_path('schema.lock')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        _init_schema()


def _init_schema():
    db.connect(reuse_if_open=True)
    db.create_tables([Item, Tag, ItemTag, ItemRate, SkipItem, LocalItem, DataRevision])
    # 自动迁移：旧数据库没有 movie_type 字段时自动添加
    try:
        columns = [col.name for col in db.get_columns('item')]
        if 'movie_type' not in columns:
            db.execute_sql('ALTER TABLE item ADD COLUMN movie_type VARCHAR(20) DEFAULT \'normal\'')
            logger.info('Database migrated: added movie_type column to item table')
    except Exception as e:
        logger.warning(f'Database migration check: {e}')

    columns = {col.name for col in db.get_columns('item')}
    if 'add_day' not in columns:
        db.execute_sql('ALTER TABLE item ADD COLUMN add_day DATE')
    db.execute_sql('UPDATE item SET add_day = DATE(add_date) WHERE add_day IS NULL')
    DataRevision.get_or_create(name='data')
    ensure_indexes()


init()
