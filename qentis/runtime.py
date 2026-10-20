"""One background writer per local results library; no Streamlit in worker threads."""
from copy import deepcopy
from dataclasses import dataclass
import fcntl
from pathlib import Path
from threading import Event, Lock, Thread

from .config import LearningConfig
from .learning import (LearningRun, advance_comparison,
                       new_comparison, resume_comparison)
from .repository import RepositoryError, RunRepository


class RunBusy(RepositoryError):
    """Another worker already owns this library's live learning experiment."""


@dataclass(frozen=True)
class LiveSnapshot:
    run: LearningRun | None
    active: bool
    stage: str
    done: int
    total: int
    pause_requested: bool
    error: str | None


def _snapshot(run):
    if run is None:
        return None
    # Checkpoints/models are immutable; isolate metadata and the growing list.
    return LearningRun(deepcopy(run.metadata), run.candidates, run.evaluation, run.trajectory,
                       list(run.checkpoints), run.visualization_slices)


class LearningSession:
    """Live work survives view changes; a process exit releases the OS writer lock."""
    def __init__(self, root):
        self.repository = RunRepository(root)
        self._lock = Lock()
        self._pause = Event()
        self._thread = None
        self._run = None
        self._stage, self._done, self._total, self._error = "Ready", 0, 1, None

    def snapshot(self) -> LiveSnapshot:
        with self._lock:
            return LiveSnapshot(_snapshot(self._run), self._thread is not None and self._thread.is_alive(),
                                self._stage, self._done, self._total, self._pause.is_set(), self._error)

    def request_pause(self):
        self._pause.set()

    def wait(self, timeout=None):
        """Wait for work, primarily for command-line callers and integration tests."""
        with self._lock:
            thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return self.snapshot()

    def start(self, config: LearningConfig) -> str:
        return self._launch(config=config)

    def resume(self, run_id: str) -> str:
        return self._launch(run_id=run_id)

    def _launch(self, config=None, run_id=None):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RunBusy("A learning experiment is already active. Pause it before starting another.")
            lease = None
            try:
                self.repository.root.mkdir(parents=True, exist_ok=True)
                lease = (self.repository.root / '.learning-writer.lock').open('a+')
                try:
                    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise RunBusy("A learning experiment is active in another session. Pause it there or wait for completion.") from exc
                if run_id is None:
                    run = new_comparison(config)
                    self.repository.begin_learning(run)
                else:
                    # Load inside the lease; never continue a stale browser snapshot.
                    run = self.repository.load(run_id)
                    if not isinstance(run, LearningRun) or not run.checkpoints:
                        raise RepositoryError("No complete learning checkpoint exists. Restart as a new run.")
                    if run.latest.iteration + 8 >= run.config.total_budget:
                        raise RepositoryError("This learning comparison is already complete.")
                    run.metadata.pop('failure', None)
                    run.metadata['status'] = 'running'
                    self.repository.save_status(run, 'running')
                self._pause.clear()
                self._run = _snapshot(run)
                self._error = None
                self._stage, self._done, self._total = ('Starting' if run_id is None else 'Resuming',
                                                       len(run.latest.strategies['adaptive'].ids) if run.checkpoints else 0,
                                                       run.config.total_budget)
                self._thread = Thread(target=self._work, args=(run, lease), daemon=True,
                                      name=f'qentis-{run.run_id}')
                self._thread.start()
                return run.run_id
            except Exception as exc:
                if lease is not None:
                    lease.close()
                if isinstance(exc, RepositoryError):
                    raise
                raise RepositoryError(f"Cannot start learning: {exc}.") from exc

    def _work(self, run, lease):
        def progress(stage, done, total):
            with self._lock:
                self._stage, self._done, self._total = stage, done, total

        def commit(current):
            self.repository.save_checkpoint(current)
            with self._lock:
                self._run = _snapshot(current)

        try:
            if not run.checkpoints:
                advance_comparison(run, commit, progress)
            resume_comparison(run, commit, progress, self._pause.is_set)
            # A pause never splits a pair, including the initial shared fit.
            with self._lock:
                self._run = _snapshot(run)
                self._stage = 'Paused at saved paired step' if run.metadata['status'] == 'paused' else 'Complete'
        except Exception as exc:
            run.metadata['status'] = 'failed'
            if not run.metadata.get('failure'):
                run.metadata['failure'] = {'message': str(exc), 'latest_complete_iteration':
                                           run.latest.iteration if run.checkpoints else None}
            message = str(exc)
            try:
                self.repository.record_failure(run)
            except RepositoryError as failure:
                message += f' {failure}'
            with self._lock:
                self._run, self._error, self._stage = _snapshot(run), message, 'Stopped'
        finally:
            lease.close()


_SESSIONS = {}
_SESSIONS_LOCK = Lock()


def learning_session(root) -> LearningSession:
    """Shared across Streamlit sessions in this process, keyed by canonical library."""
    key = str(Path(root).expanduser().resolve())
    with _SESSIONS_LOCK:
        if key not in _SESSIONS:
            _SESSIONS[key] = LearningSession(key)
        return _SESSIONS[key]
