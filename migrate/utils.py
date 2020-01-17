import requests

def get_request_content(url):
    res = requests.get(url)
    if not res.ok:
        res.raise_for_status()
    return res.text


def get_request_json(url):
    res = requests.get(url)
    if not res.ok:
        res.raise_for_status()
    return res.json()
