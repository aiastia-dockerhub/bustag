from click.testing import CliRunner
from bustag.main import recommend


def test_recommend_without_model():
    result = CliRunner().invoke(recommend)
    assert result.exit_code == 0
    assert '还没有训练好的模型' in result.output
