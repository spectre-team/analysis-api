import requests
import flask
import flask_cors

import discover
from http_helpers import Response, Matcher, http_get_selectively, proxy

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


@app.route('/schema/inputs/<string:task_name>/')
def get_inputs(task_name: str) -> Response:
    """Get inputs of the algorithm from its backend

    Returns:
        Normalized worker inputs definition.
    """
    return proxy(task_name, "/schema/inputs/{task_name}/".format(task_name=task_name))


@app.route('/schema/outputs/<string:task_name>/')
def get_outputs(task_name: str) -> Response:
    """Get output queries patterns from algorithm backend

    Returns:
        Normalized output query patterns definition.
    """
    return proxy(task_name, "/schema/outputs/{task_name}/".format(task_name=task_name))


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
    return proxy(task_name, url, method=http_get_selectively, selectors=selectors)


@app.route('/layout/inputs/<string:task_name>/')
def get_inputs_layout(task_name: str) -> Response:
    """Get the definition of algorithm parameterization form

    Returns:
        Definition of input form.
    """
    return proxy(task_name, "/layout/inputs/{task_name}/".format(task_name=task_name))


@app.route('/layout/outputs/<string:task_name>/')
def get_outputs_layout(task_name: str) -> Response:
    """Get the definition of result parameterization form

    Returns:
        Definitions of forms for narrowing down the result scope.
    """
    return proxy(task_name, "/layout/outputs/{task_name}/".format(task_name=task_name))


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
    return proxy(task_name, url, method=http_get_selectively, selectors=selectors)


@app.route('/results/')
def list_analyses():
    """Get list of all finished analyses."""
    return flask.jsonify(discover.finished_analyses()), 200


@app.route('/results/<string:task_name>/')
def list_analyses_of_some_type(task_name: str):
    """Get list of all finished analyses of some type."""
    return proxy(task_name, "/results/{task_name}/".format(task_name=task_name))


@app.route('/results/<string:task_name>/<string:task_id>/<string:aspect_name>/', methods=['POST'])
def get_result(task_name: str, task_id: str, aspect_name: str):
    """Get result of algorithm run from its backend.

    Query is parsed from JSON sent with the POST request.

    Returns:
        Normalized algorithms result.
    """
    return proxy(task_name, "/results/{task_name}/{task_id}/{aspect_name}/"
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
    task = scheduler.send_task(full_task_name, kwargs=config, queue=task_name)
    return flask.jsonify({"status": task.status}), 200 if not task.failed() else 500
