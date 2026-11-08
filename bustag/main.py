'''
命令行入口点
使用 javbus-api 替代原有的 aspider 爬虫
'''

import click
import bustag.model.classifier as clf
from bustag.spider import bus_spider
from bustag.util import APP_CONFIG


@click.command()
def recommend():
    '''
    根据现有模型预测推荐数据
    '''
    try:
        clf.recommend()
    except FileNotFoundError:
        click.echo('还没有训练好的模型, 无法推荐')


@click.command()
@click.option("--count", help="下载页数", type=int)
def download(count):
    """
    下载更新数据（通过 javbus-api）
    """
    print('start download')
    if count is not None:
        APP_CONFIG['download.count'] = count
    bus_spider.download_movies(pages=count)


@click.command()
@click.option("--fanhao", help="指定番号下载", multiple=True)
@click.option("--star", help="演员 ID（JavBus 演员页 /star/<id> 中的 ID，如 qs6）", multiple=True)
@click.option("--keyword", help="搜索关键词（只添加有磁力链接的影片）", multiple=True)
@click.option("--pages", help="每个演员/关键词抓取的页数，默认 1", type=int, default=1)
@click.option("--type", "movie_type", help="影片类型，默认用配置 download.movie_type",
              type=click.Choice(['normal', 'uncensored']), default=None)
def fetch(fanhao, star, keyword, pages, movie_type):
    """
    根据番号 / 演员 ID / 搜索关键词批量下载影片
    """
    if not fanhao and not star and not keyword:
        click.echo('请至少指定一项，如: bustag fetch --star qs6 --keyword 三上')
        return
    saved = 0
    if fanhao:
        saved += bus_spider.download_by_fanhaos(list(fanhao))
    if star or keyword:
        sources = ([{'type': 'star', 'value': s} for s in star]
                   + [{'type': 'keyword', 'value': k} for k in keyword])
        saved += bus_spider.batch_download(sources, pages=pages, movie_type=movie_type)
    click.echo(f'完成，共保存 {saved} 个影片')


@click.command()
@click.option("--keyword", help="搜索关键字", required=True)
@click.option("--pages", help="下载页数", type=int, default=1)
def search(keyword, pages):
    """
    搜索并下载影片
    """
    click.echo(f'搜索关键字: {keyword}')
    saved = bus_spider.search_and_download(keyword, pages=pages)
    click.echo(f'搜索完成，保存了 {saved} 个影片')


@click.group()
def main():
    pass


main.add_command(download)
main.add_command(recommend)
main.add_command(fetch)
main.add_command(search)

if __name__ == "__main__":
    main()