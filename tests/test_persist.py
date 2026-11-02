import pytest
from bustag.model.persist import load_model, dump_model


def test_atomic_publish(tmp_path, monkeypatch):
    path = tmp_path / 'model.pkl'
    dump_model(str(path), {'version': 1})
    def fail(*args, **kwargs):
        raise OSError('simulated disk error')
    monkeypatch.setattr('bustag.model.persist.pickle.dump', fail)
    with pytest.raises(OSError):
        dump_model(str(path), {'version': 2})
    assert load_model(path) == {'version': 1}
    assert list(tmp_path.glob('.model-*')) == []
