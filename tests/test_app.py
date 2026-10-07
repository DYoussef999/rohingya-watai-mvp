import time

from rohingya_translate.app import Worker


def wait_for(worker: Worker, results: list, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not results and time.monotonic() < deadline:
        worker.poll()
        time.sleep(0.01)


def test_worker_returns_results_to_the_caller():
    worker, results = Worker(), []
    worker.submit(lambda: 6 * 7, results.append, results.append)
    wait_for(worker, results)
    assert results == [42]


def test_worker_reports_errors_and_keeps_running(capsys):
    worker, errors, results = Worker(), [], []
    worker.submit(lambda: 1 / 0, results.append, errors.append)
    wait_for(worker, errors)
    assert isinstance(errors[0], ZeroDivisionError) and not results

    worker.submit(lambda: "still alive", results.append, errors.append)
    wait_for(worker, results)
    assert results == ["still alive"]
