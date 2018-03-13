from functools import lru_cache
from typing import Tuple

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


def _proxy(request) -> Response:
    """Pass request data as a response"""
    return flask.jsonify(request.json()), request.status_code


def _ask_for(task: str, endpoint: str, protocol: str="http") -> Response:
    try:
        backend = protocol + "://" + discover.backend(task)
    except KeyError:
        return NOT_FOUND
    request = requests.get(backend + endpoint + task)
    return _proxy(request)


@app.route('/schema/inputs/<string:task_name>/')
def get_inputs(task_name: str) -> Response:
    """Get inputs of the algorithm from its backend

    Returns:
        Normalized worker inputs definition.
    """
    return _ask_for(task_name, "/schema/inputs/")


@app.route('/schema/outputs/<string:task_name>/')
def get_outputs(task_name: str) -> Response:
    """Get output queries patterns from algorithm backend

    Returns:
        Normalized output query patterns definition.
    """
    return _ask_for(task_name, "/schema/outputs/")


@app.route('/layout/inputs/<string:task_name>/')
def get_inputs_layout(task_name: str) -> Response:
    """Get the definition of algorithm parameterization form

    Returns:
        Definition of input form.
    """
    return _ask_for(task_name, "/layout/inputs/")


@app.route('/layout/outputs/<string:task_name>/')
def get_outputs_layout(task_name: str) -> Response:
    """Get the definition of result parameterization form

    Returns:
        Definitions of forms for narrowing down the result scope.
    """
    return _ask_for(task_name, "/layout/outputs/")


@app.route('/results/')
def list_analyses():
    """Get list of all finished analyses."""
    return flask.jsonify(discover.finished_analyses()), 200


@app.route('/results/<string:task_name>/<string:task_id>/<string:aspect>/', methods=['POST'])
def get_result(task_name: str, task_id: str, aspect: str):
    """Get result of algorithm run from its backend.

    Query is parsed from JSON sent with the POST request.

    Returns:
        Normalized algorithms result.
    """
    try:
        backend = "http://" + discover.backend(task_name)
    except KeyError:
        return NOT_FOUND
    url = backend + "/results/" + task_name + "/" + task_id + "/" + aspect
    json = flask.request.get_json()
    request = requests.post(url, json=json)
    return _proxy(request)


@app.route('/schedule/<string:task_name>/', methods=['POST'])
def schedule_task(task_name: str):
    """Schedule any task available in the cluster

    Arguments:
        task_name - name of the task to be scheduled
    """
    config = flask.request.get_json()
    full_task_name = '%s.%s' % (discover.role(task_name), task_name)
    task = scheduler.send_task(full_task_name, kwargs=config)
    if task.failed():
        return task.status, 500
    return task.status, 200
