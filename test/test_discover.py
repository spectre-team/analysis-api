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
        self.assertSetEqual(set(tasks["analysis"]), {"divik", "gasvm"})
        self.assertSetEqual(set(tasks["modelling"]), {"gmm"})


@patch('celery.task.control.inspect', new=INSPECT_MOCK)
class TestRole(unittest.TestCase):
    def test_finds_type_of_the_task(self):
        role = discover.role("divik")
        self.assertEqual(role, "analysis")

    def test_throws_for_nonexistent_task(self):
        with self.assertRaises(ValueError):
            discover.role("blah")


@patch('celery.task.control.inspect', new=INSPECT_MOCK)
class TestBackend(unittest.TestCase):
    def test_finds_the_execution_backend(self):
        backend = discover.backend("divik")
        self.assertEqual(backend, "divik-worker")

    def test_finds_any_of_workers_that_support_algorithm(self):
        backend = discover.backend("gmm")
        self.assertIn(backend, {"gmm-worker", "multitask-worker"})

    def test_throws_for_nonexistent_task(self):
        with self.assertRaises(ValueError):
            discover.backend("blah")


SAMPLE_FINISHED_ANALYSES = {
    "divik-worker/results/divik": [
        {
            "id": 123,
            "name": "Some DiviK",
        },
    ],
    "gmm-worker/results/gmm": [
        {
            "id": 456,
            "name": "Some GMM",
        },
        {
            "id": 789,
            "name": "Another GMM",
        },
    ],
    "multitask-worker/results/gmm": [
        {
            "id": 456,
            "name": "Some GMM",
        },
        {
            "id": 789,
            "name": "Another GMM",
        },
    ],
    "multitask-worker/results/gasvm": [
    ],
}


def get_request_mock(json, side_effect: bool=False):
    mock = MagicMock()
    if not side_effect:
        mock.__call__().json.return_value = json
    else:
        def side_effect(url):
            another_mock = MagicMock()
            another_mock.json.return_value = json[url]
            return another_mock
        mock.side_effect = side_effect
    return mock


@patch('requests.get', new=get_request_mock(SAMPLE_FINISHED_ANALYSES, True))
class TestFinishedAnalyses(unittest.TestCase):
    def setUp(self):
        with patch('celery.task.control.inspect', new=INSPECT_MOCK):
            self.workers = discover.workers()

    def test_groups_analyses_by_task_name(self):
        analyses = discover.finished_analyses(self.workers)
        self.assertIn("divik", analyses)
        self.assertIn("gmm", analyses)
        self.assertIn("gasvm", analyses)

    def test_proxies_all_tasks(self):
        analyses = discover.finished_analyses(self.workers)
        self.assertEqual(1, len(analyses["divik"]))
        self.assertEqual(2, len(analyses["gmm"]))
        self.assertEqual(0, len(analyses["gasvm"]))

    def test_proxies_task_details(self):
        analyses = discover.finished_analyses(self.workers)
        divik = analyses["divik"][0]
        self.assertEqual(divik["id"], 123)
        self.assertEqual(divik["name"], "Some DiviK")
