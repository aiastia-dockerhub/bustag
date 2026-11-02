"""Atomically publish model artifacts; readers always see a complete file."""
import os
import pickle
import tempfile


def dump_model(path, models):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.model-', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            pickle.dump(models, stream, protocol=pickle.HIGHEST_PROTOCOL)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_model(path):
    with open(path, 'rb') as stream:
        return pickle.load(stream)
