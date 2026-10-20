"""Predeclared benchmark preparation, durable outcomes, and honest aggregation.

Run once before the meeting: python -m qentis.benchmark --root runs
No protocol decisions are made from evaluation results.
"""
from datetime import datetime, timezone
import argparse
import csv
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import platform
import subprocess
from time import perf_counter
from uuid import uuid4

import numpy as np

from .config import LearningConfig, SolverSettings
from .learning import new_comparison, advance_comparison, resume_comparison
from .runtime import LearningSession
from .repository import RepositoryError, RunRepository, RUN_ID_PATTERN
from .surrogate import FIT_POLICY
from .provenance import capture_provenance

SEEDS = tuple(range(10))
TIE_TOLERANCE = 1e-8
BENCHMARK_CONFIG = LearningConfig(total_budget=32).to_dict()


def _write(path, data):
    raw = (json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    temporary = path.with_name(f'.{path.name}-{uuid4().hex}')
    try:
        with temporary.open('xb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def load_benchmark(root):
    path = Path(root) / 'benchmark.json'
    try:
        data = json.loads(path.read_text())
        if (data['schema_version'] != 1 or data['seeds'] != list(SEEDS)
                or data['configuration'] != BENCHMARK_CONFIG
                or data['fit_policy'] != FIT_POLICY or data['tie_tolerance'] != TIE_TOLERANCE
                or len(data['outcomes']) != 10
                or [row['seed'] for row in data['outcomes']] != list(SEEDS)):
            raise ValueError('unsupported benchmark protocol')
        identities = set()
        for row in data['outcomes']:
            if row.get('run_id') and not RUN_ID_PATTERN.fullmatch(row['run_id']):
                raise ValueError('invalid benchmark run identity')
            if row['status'] not in {'pending', 'running', 'complete', 'failed'}:
                raise ValueError('invalid seed status')
            if row['status'] == 'complete':
                identities.add(row['evaluation_identity'])
                for name, digest in row['artifact_sha256'].items():
                    if name not in {'run.json', 'latest.json', 'iteration-024/checkpoint.json'}:
                        raise ValueError('unsupported benchmark artifact')
                    if sha256((Path(root) / row['run_id'] / name).read_bytes()).hexdigest() != digest:
                        raise ValueError(f"Seed {row['seed']} artifact differs: {name}")
                if len(row['artifact_sha256']) != 3:
                    raise ValueError('incomplete benchmark integrity record')
                curves = row['rmse']
                for index in range(25):
                    folder = Path(root) / row['run_id'] / f'iteration-{index:03d}'
                    raw = (folder / 'checkpoint.json').read_bytes()
                    manifest = json.loads((folder / 'manifest.json').read_text())
                    if manifest['artifacts']['checkpoint.json'] != {'sha256': sha256(raw).hexdigest(), 'bytes': len(raw)}:
                        raise ValueError(f"Seed {row['seed']} checkpoint checksum differs")
                    checkpoint = json.loads(raw)
                    for name in ('adaptive', 'random'):
                        if curves[name][index] != checkpoint['strategies'][name]['metrics']['rmse']:
                            raise ValueError(f"Seed {row['seed']} summary differs from saved metrics")
                if any(len(curves[name]) != 25 or not np.isfinite(curves[name]).all()
                       or np.any(np.asarray(curves[name]) < 0) for name in ('adaptive', 'random')):
                    raise ValueError('invalid complete error history')
        if len(identities) > 1:
            raise ValueError('benchmark evaluation identities differ')
        return data
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        raise RepositoryError(f'Cannot open prepared benchmark: {exc}. Preserve the record and restore its backup.') from exc


def summarize_benchmark(data):
    """Only complete equal-budget outcomes enter means; denominator is explicit."""
    complete = [row for row in data['outcomes'] if row['status'] == 'complete']
    result = {'completed': len(complete), 'failed': sum(row['status'] == 'failed' for row in data['outcomes']),
              'pending': sum(row['status'] in {'pending', 'running'} for row in data['outcomes']),
              'wins': 0, 'ties': 0, 'losses': 0, 'curves': {}, 'mean_final_difference': None}
    differences = []
    for row in complete:
        difference = row['rmse']['adaptive'][-1] - row['rmse']['random'][-1]
        differences.append(difference)
        result['wins' if difference < -TIE_TOLERANCE else 'losses' if difference > TIE_TOLERANCE else 'ties'] += 1
    if complete:
        for name in ('adaptive', 'random'):
            values = np.asarray([row['rmse'][name] for row in complete])
            result['curves'][name] = {'mean': values.mean(axis=0).tolist(),
                                      'std': values.std(axis=0, ddof=0).tolist()}
        result['mean_final_difference'] = float(np.mean(differences))
    return result


def benchmark_csv(data):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['seed', 'status', 'run_id', 'acquired_labels_per_strategy', 'adaptive_rmse',
                     'random_rmse', 'difference_adaptive_minus_random', 'failure'])
    for row in data['outcomes']:
        if row['status'] == 'complete':
            for offset, (adaptive, random) in enumerate(zip(row['rmse']['adaptive'], row['rmse']['random'])):
                writer.writerow([row['seed'], row['status'], row['run_id'], offset + 8,
                                 adaptive, random, adaptive - random, ''])
        else:
            writer.writerow([row['seed'], row['status'], row.get('run_id'), '', '', '', '', row.get('failure', '')])
    return output.getvalue().encode()


def hardware():
    result = {'system': platform.platform(), 'machine': platform.machine(),
              'processor': platform.processor(), 'logical_cpus': os.cpu_count()}
    if platform.system() == 'Darwin':
        for name, key in [('hw.model', 'model'), ('machdep.cpu.brand_string', 'cpu'), ('hw.memsize', 'memory_bytes')]:
            try:
                result[key] = subprocess.check_output(['sysctl', '-n', name], text=True, stderr=subprocess.DEVNULL).strip()
            except (OSError, subprocess.CalledProcessError):
                pass
    if platform.system() == 'Darwin' and 'model' not in result:
        try:
            raw = subprocess.check_output(['system_profiler', 'SPHardwareDataType', '-json'],
                                          text=True, stderr=subprocess.DEVNULL, timeout=10)
            item = json.loads(raw)['SPHardwareDataType'][0]
            # Only hardware capacity: never retain device serial numbers or UUIDs.
            for key in ('machine_name', 'machine_model', 'chip_type', 'physical_memory'):
                if key in item:
                    result[key] = item[key]
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError):
            pass
    return result


def _finish_seed(repository, row, run):
    if run.metadata['status'] != 'complete' or run.config != LearningConfig(seed=row['seed'], total_budget=32):
        raise RepositoryError('Seed did not finish the fixed benchmark protocol.')
    row.update(status='complete', evaluation_identity=run.evaluation.identity,
               rmse={name: [checkpoint.strategies[name].metrics['rmse'] for checkpoint in run.checkpoints]
                     for name in ('adaptive', 'random')},
               final_metrics={name: run.latest.strategies[name].metrics for name in ('adaptive', 'random')},
               source_digest=run.metadata['provenance']['source_digest'])
    # Bind recorded outcome to the exact final durable pointer and checkpoint.
    path = repository.root / run.run_id
    row['artifact_sha256'] = {name: sha256((path / name).read_bytes()).hexdigest()
                              for name in ('run.json', 'latest.json', 'iteration-024/checkpoint.json')}


def prepare_benchmark(root):
    """Resume an interrupted preparation; terminal failures are retained, never retried."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Separate preparation lease; each learning run also takes the shared writer lease.
    import fcntl
    with (root / '.benchmark-writer.lock').open('a+') as lease:
        try:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RepositoryError('Benchmark preparation is already active.') from exc
        path = root / 'benchmark.json'
        if path.exists():
            data = load_benchmark(root)
        else:
            data = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                    'seeds': list(SEEDS), 'configuration': BENCHMARK_CONFIG, 'fit_policy': FIT_POLICY,
                    'solver': SolverSettings().to_dict(), 'tie_tolerance': TIE_TOLERANCE,
                    'variability': 'population standard deviation across complete seeds (ddof=0), not confidence',
                    'protocol_adjustments': 'None. Existing phase-two/three model, grid and solver policy retained.',
                    'provenance': capture_provenance(), 'outcomes': [dict(seed=seed, status='pending') for seed in SEEDS]}
            _write(path, data)
        repository = RunRepository(root)
        writer = (root / '.learning-writer.lock').open('a+')
        try:
            fcntl.flock(writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            writer.close()
            raise RepositoryError('A live experiment is active. Pause it before benchmark preparation.') from exc
        with writer:
            return _prepare_rows(root, path, data, repository)


def _prepare_rows(root, path, data, repository):
    for row in data['outcomes']:
        if row['status'] in {'complete', 'failed'}:
            continue
        try:
            if row.get('run_id'):
                if not (root / row['run_id']).exists():
                    run = new_comparison(LearningConfig(seed=row['seed'], total_budget=32))
                    run.metadata['run_id'] = row['run_id']
                    repository.begin_learning(run)
                else:
                    run = repository.load(row['run_id'])
                if run.metadata['status'] == 'complete':
                    _finish_seed(repository, row, run)
                    _write(path, data)
                    continue

            else:
                run = new_comparison(LearningConfig(seed=row['seed'], total_budget=32))
                row['run_id'] = run.run_id
                row['status'] = 'running'
                _write(path, data)
                repository.begin_learning(run)
            if not run.checkpoints:
                advance_comparison(run, repository.save_checkpoint)
            resume_comparison(run, repository.save_checkpoint)
            run = repository.load(row['run_id'])
            _finish_seed(repository, row, run)
        except Exception as exc:
            row.update(status='failed', failure=str(exc))
            if 'run' in locals() and run.run_id == row.get('run_id'):
                run.metadata['failure'] = {'message': str(exc)}
                try:
                    repository.record_failure(run)
                except RepositoryError:
                    pass
        _write(path, data)
        print(f"Seed {row['seed']}: {row['status']}", flush=True)
    data['finished_at'] = data.get('finished_at', datetime.now(timezone.utc).isoformat())
    _write(path, data)
    return data

def load_presentation(root):
    try:
        record = json.loads((Path(root) / 'presentation.json').read_text())
        if (record['schema_version'] != 1 or record['configuration'] != LearningConfig().to_dict()
                or not RUN_ID_PATTERN.fullmatch(record['run_id'])
                or not np.isfinite(record['wall_seconds']) or record['wall_seconds'] < 0):
            raise ValueError('invalid presentation record')
        return record
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        raise RepositoryError(f'Cannot open presentation record: {exc}. Restore the original record.') from exc


def prepare_presentation(root):
    """Measure the unchanged short preset before the final benchmark is generated."""
    root = Path(root).resolve()
    path = root / 'presentation.json'
    if path.exists():
        record = load_presentation(root)
        run = RunRepository(root).load(record['run_id'])
        if run.metadata['status'] != 'complete' or run.config != LearningConfig():
            raise RepositoryError('Prepared short run is not complete or has different settings.')
        return record
    session = LearningSession(root)
    started = perf_counter()
    run_id = session.start(LearningConfig())
    snapshot = session.wait()
    elapsed = perf_counter() - started
    if snapshot.error or snapshot.run.metadata['status'] != 'complete':
        raise RepositoryError(snapshot.error or 'Short run incomplete; presentation not prepared.')
    record = {'schema_version': 1, 'run_id': run_id, 'created_at': snapshot.run.metadata['created_at'],
              'configuration': LearningConfig().to_dict(), 'wall_seconds': elapsed,
              'timing_scope': 'start through final durable checkpoint, including reference preparation, fitting and writes; excludes dashboard rendering',
              'target_seconds': 60, 'target_met': elapsed <= 60, 'hardware': hardware(),
              'protocol_adjustments': 'None', 'provenance': capture_provenance()}
    _write(path, record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='runs')
    args = parser.parse_args()
    timing = prepare_presentation(args.root)
    print(f"Short preset: {timing['wall_seconds']:.3f}s; target met: {timing['target_met']}", flush=True)
    result = prepare_benchmark(args.root)
    print(json.dumps(summarize_benchmark(result), indent=2), flush=True)


if __name__ == '__main__':
    main()
