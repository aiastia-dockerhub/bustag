import pytest
from unittest.mock import patch, MagicMock
from bustag.spider.bus_spider import fetch_and_save_movie, download_by_fanhaos


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
