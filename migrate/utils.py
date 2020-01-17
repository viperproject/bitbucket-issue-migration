import requests


def get_request_content(url, session=None):
    if session is None:
        session = requests
    res = session.get(url)
    if not res.ok:
        res.raise_for_status()
    return res.text


def get_request_json(url, session=None):
    if session is None:
        session = requests
    res = session.get(url)
    if not res.ok:
        res.raise_for_status()
    return res.json()
