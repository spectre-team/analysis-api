from functools import partial
from typing import Callable, Dict, List, NamedTuple, Tuple, Union

import requests
import flask
import flask_cors

import discover

from spectre_analyses.celery import app as scheduler

app = flask.Flask(__name__)
flask_cors.CORS(app)


@app.route('/algorithms/')
def get_algorithms():
    """Discover algorithms supported by the cluster

    Returns:
        Dictionary with category name as key and list of algorithms as value.
    """
    return flask.jsonify(discover.tasks()), 200


NOT_FOUND = "", 404
Response = Tuple[str, int]


def _jsonify(response) -> Response:
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


def _http_get_selectively(url: str, selectors: List[Selector]=None, *args, **kwargs):
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


def _proxy(task: str, endpoint: str, protocol: str="http", method=requests.get, *args, **kwargs) -> Response:
    try:
        worker_url = protocol + "://" + discover.backend(task)
    except KeyError:
        return NOT_FOUND
    request = method(worker_url + endpoint, *args, **kwargs)
    return _jsonify(request)


@app.route('/schema/inputs/<string:task_name>/')
def get_inputs(task_name: str) -> Response:
    """Get inputs of the algorithm from its backend

    Returns:
        Normalized worker inputs definition.
    """
    return _proxy(task_name, "/schema/inputs/{task_name}".format(task_name=task_name))


@app.route('/schema/outputs/<string:task_name>/')
def get_outputs(task_name: str) -> Response:
    """Get output queries patterns from algorithm backend

    Returns:
        Normalized output query patterns definition.
    """
    return _proxy(task_name, "/schema/outputs/{task_name}".format(task_name=task_name))


@app.route('/schema/outputs/<string:task_name>/<string:aspect_name>/')
def get_output_by_aspect(task_name: str, aspect_name: str) -> Response:
    """Get specific aspect's output query pattern from algorithm backend

    Returns:
        Normalized output query pattern definition.
    """
    url = "/schema/outputs/{task_name}/".format(task_name=task_name)
    selectors = [
        Matcher(key='aspect', value=aspect_name),
        'query_format'
    ]
    return _proxy(task_name, url, method=_http_get_selectively, selectors=selectors)


@app.route('/layout/inputs/<string:task_name>/')
def get_inputs_layout(task_name: str) -> Response:
    """Get the definition of algorithm parameterization form

    Returns:
        Definition of input form.
    """
    return _proxy(task_name, "/layout/inputs/{task_name}".format(task_name=task_name))


@app.route('/layout/outputs/<string:task_name>/')
def get_outputs_layout(task_name: str) -> Response:
    """Get the definition of result parameterization form

    Returns:
        Definitions of forms for narrowing down the result scope.
    """
    return _proxy(task_name, "/layout/outputs/{task_name}".format(task_name=task_name))


@app.route('/layout/outputs/<string:task_name>/<string:aspect_name>/')
def get_output_layout_by_aspect(task_name: str, aspect_name: str) -> Response:
    """Get the specific aspect's definition of result parameterization form

    Returns:
        Definition of form for narrowing down the result scope.
    """
    url = "/layout/outputs/{task_name}/".format(task_name=task_name)
    selectors = [
        Matcher(key='aspect', value=aspect_name),
        'layout'
    ]
    return _proxy(task_name, url, method=_http_get_selectively, selectors=selectors)


@app.route('/results/')
def list_analyses():
    """Get list of all finished analyses."""
    return flask.jsonify(discover.finished_analyses()), 200


@app.route('/results/<string:task_name>/')
def list_analyses_of_some_type(task_name: str):
    """Get list of all finished analyses of some type."""
    return _proxy(task_name, "/results/{task_name}/".format(task_name=task_name))


@app.route('/results/<string:task_name>/<string:task_id>/<string:aspect_name>/', methods=['POST'])
def get_result(task_name: str, task_id: str, aspect_name: str):
    """Get result of algorithm run from its backend.

    Query is parsed from JSON sent with the POST request.

    Returns:
        Normalized algorithms result.
    """
    return _proxy(task_name, "/results/{task_name}/{task_id}/{aspect_name}"
                             .format(task_name=task_name, task_id=task_id, aspect_name=aspect_name),
                  method=requests.post, json=flask.request.get_json())


@app.route('/schedule/<string:task_name>/', methods=['POST'])
def schedule_task(task_name: str):
    """Schedule any task available in the cluster

    Arguments:
        task_name - name of the task to be scheduled
    """
    config = flask.request.get_json()
    full_task_name = '%s.%s' % (discover.role(task_name), task_name)
    task = scheduler.send_task(full_task_name, kwargs=config)
    return flask.jsonify({"status": task.status}), 200 if not task.failed() else 500
