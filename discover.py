from itertools import chain, groupby
from operator import attrgetter
from typing import Dict, NamedTuple, List

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


def tasks() -> Dict[TaskType, List[TaskName]]:
    """Find tasks available in the cluster

    Returns:
        Dictionary of task types with their algorithm.
    """
    all_tasks = list(chain.from_iterable(workers().values()))
    all_tasks = sorted(all_tasks, key=attrgetter('type'))
    return {
        task_type: {task.name for task in unitype_tasks}
        for task_type, unitype_tasks in groupby(all_tasks, key=attrgetter('type'))
    }


def role(task_name: TaskName) -> TaskType:
    """Find type of the task.

    Returns:
        Type of the task.
    """
    all_tasks = tasks()
    for task_type in all_tasks:
        if task_name in all_tasks[task_type]:
            return task_type
    raise KeyError(task_name)
