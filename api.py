import flask
import flask_cors

import discover

from spectre_analyses.celery import app as scheduler

app = flask.Flask(__name__)
flask_cors.CORS(app)


@app.route('/schedule/<string:task_name>', methods=['POST'])
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
