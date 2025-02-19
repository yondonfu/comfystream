from concurrent.futures import ThreadPoolExecutor
import threading
import logging

logger = logging.getLogger(__name__)

thread_local = threading.local()

class DedicatedThreadPoolExecutor(ThreadPoolExecutor):
    def __init__(self, max_workers=2):
        super().__init__(max_workers=max_workers)
        self._worker_assignments = {}
        self._lock = threading.Lock()

    def assign_prompt(self, prompt_id: str, worker_type: str):
        """Assign a prompt to a specific worker type (video/audio)"""
        with self._lock:
            logger.debug(f"Assigning prompt {prompt_id} to worker type {worker_type}")
            self._worker_assignments[prompt_id] = worker_type

    def _initialize_thread(self, worker_type: str):
        """Initialize thread-local storage for worker type"""
        if not hasattr(thread_local, 'worker_type'):
            thread_local.worker_type = worker_type
            logger.debug(f"Thread {threading.current_thread().name} initialized for {worker_type}")

    def submit(self, fn, *args, **kwargs):
        prompt_id = kwargs.get('prompt_id')
        with self._lock:
            worker_type = self._worker_assignments.get(prompt_id)
            if not worker_type:
                logger.warning(f"No worker type assigned for prompt {prompt_id}")
                worker_type = 'default'

        def wrapped_fn(*args, **kwargs):
            self._initialize_thread(worker_type)
            if thread_local.worker_type != worker_type:
                logger.warning(
                    f"Task for {worker_type} incorrectly routed to {thread_local.worker_type} thread"
                )
            return fn(*args, **kwargs)

        return super().submit(wrapped_fn, *args, **kwargs)

    def shutdown(self, wait=True):
        super().shutdown(wait=wait)

