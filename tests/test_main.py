from bustag.model import classifier as clf


def test_recommend():
    '''
    测试推荐功能
    直接调用 classifier.recommend()，避免 Click 装饰器的影响
    '''
    result = clf.recommend()
    # 如果没有模型文件会抛出 FileNotFoundError，测试会跳过
    if result is not None:
        total, count = result
        assert total >= 0
        assert count >= 0