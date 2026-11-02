"""Reuse upstream connections without sharing mutable sessions between threads."""
import threading
import requests
from requests.adapters import HTTPAdapter

_local = threading.local()


def session():
    if not hasattr(_local, 'session'):
        client = requests.Session()
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10)
        client.mount('http://', adapter)
        client.mount('https://', adapter)
        _local.session = client
    return _local.session
