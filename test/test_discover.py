import unittest
from unittest.mock import MagicMock, patch

import discover


SIMPLIFIED_RESPONSE = {
    "divik-worker@blah": [
        "analysis.divik",
    ],
    "gmm-worker@blah": [
        "modelling.gmm",
    ],
    "multitask-worker@blah": [
        "analysis.gasvm",
        "modelling.gmm",
    ],
}
INSPECT_MOCK = MagicMock()
REGISTERED_MOCK = MagicMock()
REGISTERED_MOCK.registered.return_value = SIMPLIFIED_RESPONSE
INSPECT_MOCK.return_value = REGISTERED_MOCK


@patch('celery.task.control.inspect', new=INSPECT_MOCK)
class TestWorkers(unittest.TestCase):
    def test_finds_all_workers(self):
        workers = discover.workers()
        self.assertSetEqual(
            set(workers.keys()),
            {"divik-worker", "gmm-worker", "multitask-worker"})

    def test_finds_tasks_for_workers(self):
        workers = discover.workers()
        self.assertEqual(len(workers["divik-worker"]), 1)
        self.assertEqual(workers["divik-worker"][0].name, "divik")
        self.assertEqual(workers["divik-worker"][0].type, "analysis")


@patch('celery.task.control.inspect', new=INSPECT_MOCK)
class TestTasks(unittest.TestCase):
    def test_organizes_tasks_by_types(self):
        tasks = discover.tasks()
        self.assertSetEqual(set(tasks.keys()), {"analysis", "modelling"})
        self.assertSetEqual(tasks["analysis"], {"divik", "gasvm"})
        self.assertSetEqual(tasks["modelling"], {"gmm"})


@patch('celery.task.control.inspect', new=INSPECT_MOCK)
class TestRole(unittest.TestCase):
    def test_finds_type_of_the_task(self):
        role = discover.role("divik")
        self.assertEqual(role, "analysis")

    def test_throws_for_nonexistent_task(self):
        with self.assertRaises(KeyError):
            discover.role("blah")
