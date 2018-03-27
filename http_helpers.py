"""HTTP helper functions"""
from functools import partial
from typing import Tuple, NamedTuple, Callable, Dict, Union, List

import flask
import requests

import discover

NOT_FOUND = "", 404
Response = Tuple[str, int]


def jsonify(response) -> Response:
    """Pass request data as a response"""
    if response.ok:
        return flask.jsonify(response.json()), response.status_code
    return "{}", response.status_code


CustomResponse = NamedTuple('CustomResponse', [
    ('json', Callable[[], Dict]),
    ('status_code', int),
    ('ok', bool)
])
Matcher = NamedTuple('Matcher', [
    ('key', str),
    ('value', object)
])
Selector = Union[Matcher, str, int]


def _match_item(matcher: Matcher, collection: Dict) -> bool:
    return collection[matcher.key] == matcher.value


def _matching(matcher: Matcher, collection: List[Dict]) -> List[Dict]:
    match = partial(_match_item, matcher)
    return list(filter(match, collection))


def _select(data, selectors: List[Selector]):
    for selector in selectors:
        if isinstance(selector, Matcher):
            data = _matching(selector, data)[0]
        else:
            data = data[selector]
    return data


def http_get_selectively(url: str, selectors: List[Selector]=None, *args, **kwargs):
    """HTTP GET with selection of field"""
    if selectors is None:
        selectors = []
    request = requests.get(url, *args, **kwargs)

    if not request.ok:
        data = {}
    else:
        data = _select(request.json(), selectors)

    return CustomResponse(json=lambda: data,
                          status_code=request.status_code,
                          ok=request.ok)


def proxy(task: str, endpoint: str, protocol: str= "http", method=requests.get, *args, **kwargs) -> Response:
    """Proxy call to another REST API"""
    try:
        worker_url = protocol + "://" + discover.backend(task)
    except KeyError:
        return NOT_FOUND
    request = method(worker_url + endpoint, *args, **kwargs)
    return jsonify(request)
