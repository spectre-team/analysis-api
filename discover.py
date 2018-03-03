from itertools import chain, groupby
from operator import attrgetter
from typing import Dict, NamedTuple, List

import requests
import celery.task.control

WorkerName = str
TaskName = str
TaskType = str
Task = NamedTuple('Task', [
    ('type', TaskType),
    ('name', TaskName),
])


def worker_name(full_name: WorkerName) -> WorkerName:
    return full_name.split('@')[0]


def workers() -> Dict[WorkerName, List[Task]]:
    """Find workers available in the cluster

    Returns:
        Dictionary of workers with their tasks.
    """
    workers_info = celery.task.control.inspect().registered()
    return {
        worker_name(full_name): [
            Task(*task_name.split('.'))
            for task_name in workers_info[full_name]
        ]
        for full_name in workers_info
    }


def tasks(all_workers: Dict[WorkerName, List[Task]]=None) \
        -> Dict[TaskType, List[TaskName]]:
    """Find tasks available in the cluster

    Returns:
        Dictionary of task types with their algorithm.
    """
    if all_workers is None:
        all_workers = workers()
    all_tasks = list(chain.from_iterable(all_workers.values()))
    all_tasks = sorted(all_tasks, key=attrgetter('type'))
    return {
        task_type: list({task.name for task in unitype_tasks})
        for task_type, unitype_tasks in groupby(all_tasks, key=attrgetter('type'))
    }


def role(task_name: TaskName,
         all_tasks: Dict[TaskType, List[TaskName]]=None) -> TaskType:
    """Find type of the task.

    Returns:
        Type of the task.
    """
    if all_tasks is None:
        all_tasks = tasks()
    for task_type in all_tasks:
        if task_name in all_tasks[task_type]:
            return task_type
    raise ValueError(task_name)


def backend(task_name: TaskName,
            all_workers: Dict[WorkerName, List[Task]]=None) -> WorkerName:
    """Find any worker on which the task is supported.

    Returns:
        Name of the worker that supports execution of particular task.
    """
    if all_workers is None:
        all_workers = workers()
    for worker in all_workers:
        for some_task in all_workers[worker]:
            if some_task.name == task_name:
                return worker
    raise ValueError(task_name)


def _analyses_done(backend_name: WorkerName, task: TaskName):
    return requests.get(backend_name + '/results/' + task).json()


FinishedTask = Dict[str, object]


def finished_analyses(all_workers: Dict[WorkerName, List[Task]]=None) \
        -> Dict[TaskType, List[FinishedTask]]:
    """Find all the finished analyses for each task."""
    if all_workers is None:
        all_workers = workers()
    all_tasks = set(chain.from_iterable(tasks(all_workers).values()))
    backends = [backend(task, all_workers) for task in all_tasks]
    analyses = map(_analyses_done, backends, all_tasks)
    listed = {task: finished for task, finished in zip(all_tasks, analyses)}
    return listed
