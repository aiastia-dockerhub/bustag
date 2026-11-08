from unittest.mock import patch, MagicMock
from bustag.spider.bus_spider import (
    fetch_and_save_movie, download_by_fanhaos, download_by_star,
    search_and_download, batch_download, preview_sources)


class TestFetchAndSaveMovie:
    @patch('bustag.spider.bus_spider.Item')
    @patch('bustag.spider.bus_spider.get_movie_detail')
    @patch('bustag.spider.bus_spider.save')
    def test_fetch_and_save_movie_success(self, mock_save, mock_get_detail, mock_item_cls):
        mock_item_cls.get_by_fanhao.return_value = None
        mock_get_detail.return_value = {
            'id': 'SSIS-406',
            'title': 'SSIS-406 test title',
            'img': 'https://example.com/cover.jpg',
            'date': '2022-05-20',
            'videoLength': 120,
            'genres': [{'id': 'e', 'name': 'test_genre'}],
            'stars': [{'id': '2xi', 'name': 'test_star'}],
            'director': None,
            'producer': None,
            'publisher': None,
            'series': None,
        }
        result = fetch_and_save_movie('SSIS-406')
        assert result is True
        mock_save.assert_called_once()

    @patch('bustag.spider.bus_spider.Item')
    def test_fetch_and_save_movie_exists(self, mock_item_cls):
        mock_item_cls.get_by_fanhao.return_value = MagicMock()
        result = fetch_and_save_movie('SSIS-406')
        assert result is False


class TestDownloadByFanhaos:
    @patch('bustag.spider.bus_spider.fetch_and_save_movie')
    def test_download_by_fanhaos(self, mock_fetch):
        mock_fetch.return_value = True
        result = download_by_fanhaos(['SSIS-406', 'SSIS-407'])
        assert result == 2


def _movie_list_response(page):
    return {'movies': [{'id': f'SSIS-{400 + page}'}], 'pagination': {'page': page}}


class TestDownloadByStar:
    @patch('bustag.spider.bus_spider.fetch_and_save_movie')
    @patch('bustag.spider.bus_spider.get_movies')
    def test_download_by_star_filters_magnet_and_passes_star_filter(self, mock_get_movies, mock_fetch):
        mock_get_movies.return_value = _movie_list_response(1)
        mock_fetch.return_value = True
        result = download_by_star('qs6')
        assert result == 1
        mock_fetch.assert_called_once_with('SSIS-401', movie_type='normal')
        assert mock_get_movies.call_args.kwargs['filter_type'] == 'star'
        assert mock_get_movies.call_args.kwargs['filter_value'] == 'qs6'
        assert mock_get_movies.call_args.kwargs['magnet'] == 'exist'

    @patch('bustag.spider.bus_spider.time.sleep')
    @patch('bustag.spider.bus_spider.fetch_and_save_movie')
    @patch('bustag.spider.bus_spider.get_movies')
    def test_download_by_star_continues_past_duplicate_pages(self, mock_get_movies, mock_fetch, mock_sleep):
        mock_get_movies.return_value = _movie_list_response(1)
        mock_fetch.return_value = False  # all duplicates
        result = download_by_star('qs6', pages=3)
        assert result == 0
        # 整页重复不代表后面页也重复，按指定页数抓完
        assert mock_get_movies.call_count == 3


class TestSearchAndDownload:
    @patch('bustag.spider.bus_spider.fetch_and_save_movie')
    @patch('bustag.spider.bus_spider.search_movies')
    def test_search_and_download_filters_magnet(self, mock_search, mock_fetch):
        mock_search.return_value = _movie_list_response(1)
        mock_fetch.return_value = True
        result = search_and_download('三上')
        assert result == 1
        assert mock_search.call_args.kwargs['magnet'] == 'exist'
        assert mock_search.call_args.kwargs['keyword'] == '三上'

    @patch('bustag.spider.bus_spider.fetch_and_save_movie')
    @patch('bustag.spider.bus_spider.search_movies')
    def test_search_and_download_reports_progress(self, mock_search, mock_fetch):
        mock_search.return_value = _movie_list_response(1)
        mock_fetch.return_value = True
        progress = MagicMock()
        search_and_download('三上', progress=progress)
        progress.assert_called_once_with(stage='抓取关键词 三上', processed=1)


class TestBatchDownload:
    @patch('bustag.spider.bus_spider.search_and_download')
    @patch('bustag.spider.bus_spider.download_by_star')
    def test_batch_download_mixed_sources(self, mock_star, mock_search):
        mock_star.return_value = 3
        mock_search.return_value = 2
        sources = [
            {'type': 'star', 'value': 'qs6'},
            {'type': 'keyword', 'value': '三上'},
            {'type': 'keyword', 'value': ''},  # empty values are dropped
        ]
        result = batch_download(sources, pages=2)
        assert result == 5
        mock_star.assert_called_once_with('qs6', pages=2, progress=None, movie_type='normal')
        mock_search.assert_called_once_with('三上', pages=2, progress=None, movie_type='normal')

    @patch('bustag.spider.bus_spider.search_and_download')
    @patch('bustag.spider.bus_spider.download_by_star')
    def test_batch_download_passes_explicit_type(self, mock_star, mock_search):
        mock_star.return_value = 0
        mock_search.return_value = 0
        batch_download([{'type': 'star', 'value': 'qs6'}], movie_type='uncensored')
        assert mock_star.call_args.kwargs['movie_type'] == 'uncensored'

    @patch('bustag.spider.bus_spider.fetch_and_save_movie')
    @patch('bustag.spider.bus_spider.get_movies')
    def test_batch_download_wraps_progress_with_source_index(self, mock_get_movies, mock_fetch):
        mock_get_movies.return_value = _movie_list_response(1)
        mock_fetch.return_value = True
        progress = MagicMock()
        result = batch_download([{'type': 'star', 'value': 'qs6'}], progress=progress)
        assert result == 1
        progress.assert_called_once_with(stage='抓取演员 qs6（1/1）', processed=1)


def _preview_item_response():
    return {'movies': [
        {'id': 'SSIS-401', 'title': 'SSIS-401 new movie', 'img': '/thumbs/a.jpg', 'date': '2024-01-01'},
        {'id': 'SSIS-402', 'title': 'SSIS-402 kept', 'img': '/thumbs/b.jpg', 'date': '2024-01-02'},
    ]}


class TestPreviewSources:
    @patch('bustag.spider.bus_spider.SkipItem.is_skipped', return_value=False)
    @patch('bustag.spider.bus_spider.Item')
    @patch('bustag.spider.bus_spider.get_movies')
    def test_preview_filters_existing_and_builds_candidates(self, mock_get_movies, mock_item_cls, mock_skip):
        mock_get_movies.return_value = _preview_item_response()

        def get_by_fanhao(fanhao):
            return MagicMock() if fanhao == 'SSIS-402' else None
        mock_item_cls.get_by_fanhao.side_effect = get_by_fanhao

        result = preview_sources([{'type': 'star', 'value': 'qs6'}])
        assert [m['fanhao'] for m in result['movies']] == ['SSIS-401']
        assert result['skipped'] == 1
        movie = result['movies'][0]
        assert movie['title'] == 'new movie'  # fanhao prefix stripped
        assert movie['img'].endswith('/thumbs/a.jpg')
        assert movie['url'] == 'https://www.javbus.com/SSIS-401'
        assert movie['source'] == '演员 qs6'
        assert mock_get_movies.call_args.kwargs['magnet'] == 'exist'
        assert mock_get_movies.call_args.kwargs['filter_value'] == 'qs6'

    @patch('bustag.spider.bus_spider.SkipItem.is_skipped', return_value=True)
    @patch('bustag.spider.bus_spider.Item')
    @patch('bustag.spider.bus_spider.search_movies')
    def test_preview_skips_dead_fanhaos(self, mock_search, mock_item_cls, mock_skip):
        mock_item_cls.get_by_fanhao.return_value = None
        mock_search.return_value = {'movies': [{'id': 'ABP-123', 'title': 'x', 'img': '', 'date': ''}]}
        result = preview_sources([{'type': 'keyword', 'value': '三上'}])
        assert result['movies'] == []
        assert result['skipped'] == 1

    @patch('bustag.spider.bus_spider.SkipItem.is_skipped', return_value=False)
    @patch('bustag.spider.bus_spider.Item')
    @patch('bustag.spider.bus_spider.get_movies')
    @patch('bustag.spider.bus_spider.search_movies')
    def test_preview_dedups_across_sources_and_reports_progress(
            self, mock_search, mock_get_movies, mock_item_cls, mock_skip):
        mock_item_cls.get_by_fanhao.return_value = None
        mock_skip.return_value = False
        mock_get_movies.return_value = {'movies': [{'id': 'SSIS-401', 'title': 'a', 'img': '', 'date': ''}]}
        mock_search.return_value = {'movies': [{'id': 'SSIS-401', 'title': 'a', 'img': '', 'date': ''},
                                               {'id': 'MIDV-001', 'title': 'b', 'img': '', 'date': ''}]}
        progress = MagicMock()
        result = preview_sources([{'type': 'star', 'value': 'qs6'},
                                  {'type': 'keyword', 'value': '三上'}], progress=progress)
        # SSIS-401 appears in both sources but is kept once
        assert [m['fanhao'] for m in result['movies']] == ['SSIS-401', 'MIDV-001']
        assert result['movies'][1]['source'] == '关键词 三上'
        progress.assert_called_with(stage='预览关键词 三上（2/2）', processed=2)

    @patch('bustag.spider.bus_spider.time.sleep')
    @patch('bustag.spider.bus_spider.SkipItem.is_skipped', return_value=False)
    @patch('bustag.spider.bus_spider.Item')
    @patch('bustag.spider.bus_spider.get_movies')
    def test_preview_continues_past_all_duplicate_page(
            self, mock_get_movies, mock_item_cls, mock_skip, mock_sleep):
        mock_item_cls.get_by_fanhao.return_value = MagicMock()  # 第一页全在库中
        mock_get_movies.return_value = _preview_item_response()
        result = preview_sources([{'type': 'star', 'value': 'qs6'}], pages=2)
        assert result['movies'] == []
        # 第一页全重复时仍继续抓第二页
        assert mock_get_movies.call_count == 2
