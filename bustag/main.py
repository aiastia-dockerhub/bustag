'''
命令行入口点
使用 javbus-api 替代原有的 aspider 爬虫
'''

import click
import bustag.model.classifier as clf
from bustag.spider import bus_spider
from bustag.util import logger, APP_CONFIG


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
def fetch(fanhao):
    """
    根据番号下载指定影片
    """
    if not fanhao:
        click.echo('请使用 --fanhao 指定番号，如: bustag fetch --fanhao SSIS-406')
        return
    bus_spider.download_by_fanhaos(list(fanhao))


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