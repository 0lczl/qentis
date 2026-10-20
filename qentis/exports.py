"""Inspectable evidence exports from one confirmed paired revision, never live work."""
from dataclasses import dataclass
import csv
import io
import json

from .learning import LearningRun, STRATEGIES


@dataclass(frozen=True)
class EvidenceFile:
    filename: str
    mime: str
    content: bytes


def _csv(fields, rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8')


def export_evidence(run: LearningRun, revision: int | None = None) -> dict[str, EvidenceFile]:
    if not run.checkpoints:
        raise ValueError('No complete paired checkpoint exists to export.')
    if revision is None:
        revision = len(run.checkpoints) - 1
    if type(revision) is not int or not 0 <= revision < len(run.checkpoints):
        raise ValueError('Choose a completed model revision.')
    checkpoint = run.checkpoints[revision]
    record = {'export_schema_version': 1, 'run_id': run.run_id, 'run_status': run.metadata['status'],
              'selected_iteration': checkpoint.iteration, 'checkpoint_created_at': checkpoint.created_at,
              'configuration': run.config.to_dict(), 'physical_convention': run.metadata['physical_convention'],
              'solver': run.metadata['solver'], 'fit_policy': run.metadata['fit_policy'],
              'seed_streams': run.metadata['seed_streams'], 'evaluation_identity': run.evaluation.identity,
              'reference_validation': run.metadata['reference_validation'], 'provenance': run.metadata['provenance'],
              'counts': checkpoint.counts, 'elapsed_seconds': checkpoint.elapsed_seconds,
              'metrics': {name: checkpoint.strategies[name].metrics for name in STRATEGIES},
              'model_warnings': {name: list(checkpoint.strategies[name].model.warnings) for name in STRATEGIES},
              'limits': ['Simulation only; single seed does not establish a general advantage.',
                         'Intervals estimate mean ± 1.96σ and are not calibrated confidence or physical bounds.',
                         ('Timing excludes checkpoint writes, idle pause time and rendering; time is not sample efficiency.'
                          if run.metadata['schema_version'] == 3 else
                          'Legacy timing includes earlier commits; excludes this commit and rendering; time is not sample efficiency.')]}
    observations = []
    for name in STRATEGIES:
        for order, observation in enumerate(checkpoint.strategies[name].observations):
            gamma, time = run.candidates[observation.candidate_id]
            observations.append({'run_id': run.run_id, 'iteration': checkpoint.iteration, 'strategy': name,
                'acquired_order': order + 1, 'shared_initial': order < 8, 'candidate_id': observation.candidate_id,
                'gamma_inverse_time_units': float(gamma), 'time_dimensionless_units': float(time),
                'numerical_coherence_x': observation.value})
    metrics = [{'run_id': run.run_id, 'iteration': item.iteration, 'labels_per_strategy': item.iteration + 8,
                'strategy': name, **item.strategies[name].metrics}
               for item in run.checkpoints[:revision + 1] for name in STRATEGIES]
    prefix = f'{run.run_id}-revision-{checkpoint.iteration:03d}'
    return {
        'configuration': EvidenceFile(f'{prefix}-configuration.json', 'application/json',
                                     (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()),
        'observations': EvidenceFile(f'{prefix}-observations.csv', 'text/csv', _csv(list(observations[0]), observations)),
        'metrics': EvidenceFile(f'{prefix}-metrics.csv', 'text/csv', _csv(list(metrics[0]), metrics))}
