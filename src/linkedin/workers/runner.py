from __future__ import annotations

import logging
import multiprocessing
from collections.abc import Callable

from linkedin.workers.glassdoor_worker import run_forever as run_glassdoor_worker
from linkedin.workers.workable_worker import run_forever as run_workable_worker
from linkedin.workers.wellfound_worker import run_forever as run_wellfound_worker

logger = logging.getLogger(__name__)


WorkerTarget = Callable[[], None]


def _start_worker_process(name: str, target: WorkerTarget) -> multiprocessing.Process:
    process = multiprocessing.Process(
        target=target,
        name=name,
        daemon=False,
    )
    process.start()
    logger.info("Started %s with pid=%s", name, process.pid)
    return process


def run_all_workers() -> None:
    raise RuntimeError("Redis-backed workers are disabled for this deployment.")
    logging.basicConfig(level=logging.INFO)
    processes = [
        _start_worker_process("glassdoor-worker", run_glassdoor_worker),
        _start_worker_process("wellfound-worker", run_wellfound_worker),
        _start_worker_process("workable-worker", run_workable_worker),
    ]

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        logger.info("Stopping all worker processes...")
        for process in processes:
            if process.is_alive():
                process.terminate()
        for process in processes:
            process.join(timeout=5)


def main() -> None:
    multiprocessing.set_start_method("spawn", force=True)
    run_all_workers()


if __name__ == "__main__":
    main()
