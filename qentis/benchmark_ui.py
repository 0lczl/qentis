"""Saved benchmark evidence, distinct from live single-seed computation."""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .benchmark import benchmark_csv, load_benchmark, load_presentation, summarize_benchmark
from .learning_charts import _axes
from .learning_ui import show_learning_result, plot
from .repository import RepositoryError
from .theme import palette


def benchmark_curves(summary, theme='Dark'):
    figure = go.Figure()
    colors = palette(theme)
    for name, color, dash, symbol in [('adaptive', colors['accent'], 'solid', 'circle'),
                                       ('random', colors['random'], 'dash', 'diamond')]:
        if name not in summary['curves']:
            continue
        values = summary['curves'][name]
        mean, std = np.array(values['mean']), np.array(values['std'])
        x = np.arange(8, 33)
        figure.add_trace(go.Scatter(x=np.r_[x, x[::-1]], y=np.r_[mean + std, (mean - std)[::-1]],
                                   fill='toself', fillcolor=color, opacity=.12, line_width=0,
                                   name=f'{name.title()} ±1 SD variability', hoverinfo='skip', showlegend=False))
        figure.add_trace(go.Scatter(x=x, y=mean, name=f'{name.title()} mean', mode='lines+markers',
                                   line=dict(color=color, dash=dash), marker=dict(symbol=symbol, size=5)))
    _axes(figure, theme, 'Acquired labels per strategy (8 shared initial)', 'Held-out RMSE of x')
    figure.update_yaxes(rangemode='tozero')
    figure.update_xaxes(dtick=4)
    return figure


def presentation_opening(repository):
    path = repository.root / 'presentation.json'
    if not path.exists():
        st.caption('No prepared presentation result in this library. Run a short experiment, or prepare evidence using the documented setup command.')
        return
    try:
        record = load_presentation(repository.root)
        if record['schema_version'] != 1:
            raise ValueError('Unsupported presentation schema')
        st.markdown('### Start with saved evidence')
        st.caption(f"Saved presentation result · {record['created_at']} · seed 0 · 24 labels per strategy. No replay or live animation.")
        if st.button('Open saved run', type='primary'):
            run = repository.load(record['run_id'])
            if run.config.to_dict() != record['configuration'] or run.metadata['status'] != 'complete':
                raise ValueError('Presentation result is incomplete or its protocol differs')
            st.session_state['active_run'] = run
            st.session_state['result_source'] = 'saved'
        st.caption(f"Measured short computation: {record['wall_seconds']:.2f} s against a 60 s target; includes saving, excludes rendering. "
                   'The short live form below uses the same default protocol.')
    except (RepositoryError, OSError, ValueError, KeyError, TypeError) as exc:
        st.error(f'Prepared opening is unavailable: {exc}. Restore the original record or use the short live form.')


def benchmark_view(repository, theme):
    st.title('Ten seeds, one fixed protocol')
    st.write('Prepared numerical evidence · 8 shared initial + 24 additional labels per strategy · seeds 0–9.')
    if not (repository.root / 'benchmark.json').exists():
        st.info('No prepared benchmark in this library. See the setup instructions to compute and save all ten seeds before the meeting.')
        return
    try:
        data = load_benchmark(repository.root)
    except RepositoryError as exc:
        st.error(str(exc))
        return
    summary = summarize_benchmark(data)
    st.caption(f"Saved benchmark · {data['created_at']} · 21 × 21 candidates · γ ∈ [0, 2], t ∈ [0, 5].")
    st.write(f"**{summary['completed']}/10 complete · {summary['failed']} failed · {summary['pending']} unfinished**")
    st.write(f"Adaptive wins / ties / losses: **{summary['wins']} / {summary['ties']} / {summary['losses']}**. "
             'Tie tolerance: |adaptive RMSE − random RMSE| ≤ 1e−8 at 32 labels.')
    if summary['mean_final_difference'] is not None:
        st.write(f"Mean final RMSE difference (adaptive − random): **{summary['mean_final_difference']:+.6f}**. Negative favors adaptive.")
        st.caption('Shaded bands: mean ±1 across-seed standard deviation (variability, not confidence).')
        plot(benchmark_curves(summary, theme), 'benchmark-mean-curves')
    st.caption(f"Bands show mean ± one population standard deviation across {summary['completed']} complete seeds: "
               'variability, not confidence intervals or statistical significance. Failed and unfinished seeds are listed below and excluded from means; denominator is explicit. Bands are not clipped at zero.')
    rows = []
    for row in data['outcomes']:
        complete = row['status'] == 'complete'
        adaptive = row['rmse']['adaptive'][-1] if complete else None
        random = row['rmse']['random'][-1] if complete else None
        rows.append({'Seed': row['seed'], 'Status': row['status'], 'Adaptive RMSE': adaptive,
                     'Random RMSE': random, 'Δ adaptive − random': adaptive - random if complete else None,
                     'Failure': row.get('failure', ''), 'Run ID': row.get('run_id', '')})
    table = pd.DataFrame(rows).drop(columns='Run ID')
    st.table(table.style.hide(axis='index').format(
        {name: '{:.6f}' for name in ('Adaptive RMSE', 'Random RMSE', 'Δ adaptive − random')}, na_rep='—'))
    st.caption('Every predeclared seed is retained. Results may favor either strategy; this simple γt response does not establish a general adaptive advantage.')
    with st.expander('Protocol, timing and downloadable benchmark'):
        st.write(data['protocol_adjustments'])
        st.write('Same Gaussian-process policy and fixed 400-point numerical evaluation identity within and across these seeds. Evaluation never guides acquisition.')
        st.json({key: value for key, value in data.items() if key != 'outcomes'})
        timing = repository.root / 'presentation.json'
        if timing.exists():
            st.json(load_presentation(repository.root))
        st.download_button('Benchmark JSON', json.dumps(data, indent=2, allow_nan=False).encode(),
                           file_name='qentis-benchmark.json', mime='application/json', on_click='ignore')
        st.download_button('Benchmark metrics CSV', benchmark_csv(data), file_name='qentis-benchmark-metrics.csv',
                           mime='text/csv', on_click='ignore')
    chosen = st.selectbox('Inspect seed (all outcomes)', list(range(10)),
                          format_func=lambda seed: f"Seed {seed} · {data['outcomes'][seed]['status']}")
    row = data['outcomes'][chosen]
    if row.get('failure'):
        st.error(row['failure'])
    if st.button('Open seed evidence', disabled=not row.get('run_id')):
        st.session_state['benchmark_opened_id'] = row['run_id']
    if st.session_state.get('benchmark_opened_id') == row.get('run_id') and row.get('run_id'):
        try:
            run = repository.load(row['run_id'])
            if run.checkpoints:
                show_learning_result(run, 'saved', theme)
            else:
                st.info('No complete checkpoint for this seed. The failed outcome is retained without retry or replacement.')
                st.json(run.metadata)
        except RepositoryError as exc:
            st.error(f'Could not restore this seed: {exc}. The summary and failure record remain available.')
