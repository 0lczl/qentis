"""Streamlit presentation of completed scientific checkpoints."""
import numpy as np
import pandas as pd
import streamlit as st

from .charts import bloch_sphere
from .config import LearningConfig, ConfigurationError
from .learning import LearningRun
from .learning_charts import error_map, learning_curves, prediction_trajectory, uncertainty_map
from .exports import export_evidence
from .runtime import learning_session
from .repository import RepositoryError

PLOT_CONFIG = {"displaylogo": False, "displayModeBar": False, "scrollZoom": False}


def plot(figure, key):
    st.plotly_chart(figure, config=PLOT_CONFIG, use_container_width=True, theme=None, key=key)


def show_learning_result(run: LearningRun, source: str, theme: str):
    cfg = run.config
    status = run.metadata["status"]
    st.markdown(f'<div class="result-heading"><h2>Adaptive vs random</h2><span class="result-status">'
                f'{"Saved result" if source == "saved" else "Live computation"} · {status}</span></div>', unsafe_allow_html=True)
    st.caption(f"Single seed {cfg.seed} · γ ∈ [0, {cfg.gamma_max:g}] · t ∈ [0, {cfg.time_max:g}] · "
               f"{cfg.grid_size} × {cfg.grid_size} candidates · budget {cfg.total_budget} per strategy")
    st.caption(f"Created {run.metadata['created_at']} · {run.run_id}")
    if cfg.to_dict() == LearningConfig(seed=cfg.seed, total_budget=32).to_dict():
        st.info("Fixed benchmark protocol: 8 shared initial +24 acquired labels per strategy.")
    elif not cfg.preset:
        st.info("Exploratory protocol: settings differ from the short scientific preset.")
    if run.metadata.get("failure"):
        st.error(f"Stopped: {run.metadata['failure']['message']} Latest complete paired step is retained below.")
    with st.expander(f"Inspect model revisions · latest {run.latest.iteration + 8} labels each"):
        revision = st.select_slider("Inspect completed paired step", options=list(range(len(run.checkpoints))),
                                    value=len(run.checkpoints) - 1, format_func=lambda i: f"{i + 8} labels each",
                                    key=f"revision-{run.run_id}")
    checkpoint = run.checkpoints[revision]
    adaptive, random = (checkpoint.strategies[name] for name in ("adaptive", "random"))
    st.caption(f"Model revision {revision} · {8 + revision} acquired labels per strategy · "
               "8 shared initial observations. Inspecting a revision performs no fitting or acquisition.")
    difference = adaptive.metrics['rmse'] - random.metrics['rmse']
    outcome = "Adaptive lower" if difference < -1e-8 else "Random lower" if difference > 1e-8 else "Numerical tie"
    st.markdown(f'<div class="readout"><span>Adaptive RMSE<strong>{adaptive.metrics["rmse"]:.6f}</strong></span>'
                f'<span>Random RMSE<strong>{random.metrics["rmse"]:.6f}</strong></span>'
                f'<span>Δ adaptive − random<strong>{difference:+.6f}</strong></span></div>', unsafe_allow_html=True)
    st.caption(f"{outcome} at this budget (tie tolerance 1e−8). One seed does not establish a general advantage. "
               "Error may increase after an acquisition.")
    tabs = st.tabs(["Learning curves", "Selection and error", "Qubit trajectory", "Record and diagnostics"])
    with tabs[0]:
        plot(learning_curves(run, theme), f"learning-{run.run_id}")
        st.caption("Both curves use the same 400 held-out coordinates, model policy, and label budget. "
                   "The full recorded history stays visible; the step selector controls the maps and trajectory.")
    with tabs[1]:
        left, right = st.columns(2)
        with left:
            st.markdown("### Estimated uncertainty · adaptive")
            plot(uncertainty_map(run, checkpoint, theme), f"uncertainty-{run.run_id}")
            selection = adaptive.next_selection
            if selection:
                point = run.candidates[selection['candidate_id']]
                st.write(f"Next: γ = {point[0]:.3f}, t = {point[1]:.3f}; estimated σ = {selection['score']:.6f}.")
            else:
                st.write("Budget reached. No further point is scheduled; the cross marks the last acquisition.")
            st.caption("The largest estimated standard deviation among unqueried candidates chooses the next point. "
                       "Acquisition cannot see the evaluation labels or error map. Ties use candidate order.")
            overflow = int(np.sum(adaptive.candidate_std > 1))
            st.caption(f"Fixed σ scale 0–1 throughout this run; {overflow} candidate values above 1 (inspect in tooltips).")
        with right:
            strategy = st.selectbox("Error-map strategy", ["adaptive", "random"], key=f"error-strategy-{run.run_id}")
            st.markdown("### Measured absolute error · evaluation only")
            plot(error_map(run, checkpoint, strategy, theme), f"error-{run.run_id}")
            errors = np.abs(checkpoint.strategies[strategy].evaluation_mean - run.evaluation.labels)
            st.caption(f"400 separate interior coordinates. Fixed |error| scale 0–1; "
                       f"{int(np.sum(errors > 1))} values above 1. Tooltips retain the full values. "
                       "This map is never an acquisition input.")
    with tabs[2]:
        gamma_index = st.select_slider("Trajectory rate γ (1/time)", options=list(range(cfg.grid_size)),
                                       value=cfg.grid_size // 2, format_func=lambda i: f"{run.visualization_slices[i].gamma:.3f}",
                                       key=f"gamma-slice-{run.run_id}")
        data = run.visualization_slices[gamma_index]
        index = st.select_slider("Inspect time (dimensionless units)", options=list(range(len(data.times))),
                                 value=0, format_func=lambda i: f"{data.times[i]:.3f}", key=f"learn-time-{run.run_id}")
        sphere, trajectory = st.columns([0.85, 1.3])
        with sphere:
            st.markdown("### Bloch sphere · numerical reference")
            plot(bloch_sphere(data, index, theme), f"learn-sphere-{run.run_id}")
        with trajectory:
            st.markdown("### Reference and learned coherence")
            plot(prediction_trajectory(data, checkpoint, index, theme), f"learn-trajectory-{run.run_id}")
        point = [[data.gamma, float(data.times[index])]]
        estimates = [checkpoint.strategies[name].model.predict(point) for name in ("adaptive", "random")]
        st.write(f"At γ = {data.gamma:.3f}, t = {data.times[index]:.3f}: reference x = {data.bloch[index, 0]:.6f}; "
                 f"adaptive x̂ = {estimates[0][0][0]:.6f} ± {1.96 * estimates[0][1][0]:.6f}; "
                 f"random x̂ = {estimates[1][0][0]:.6f} ± {1.96 * estimates[1][1][0]:.6f}.")
        st.caption("Shaded bands are estimated mean ± 1.96σ, not guaranteed physical bounds or calibrated confidence. "
                   "The model learns one observable, not a full quantum state. All numerical slices were saved separately "
                   "for visualization; changing sliders predicts from the stored model and performs no solver calls.")
        excursions = []
        coords = np.column_stack((np.full_like(data.times, data.gamma), data.times))
        for name in ("adaptive", "random"):
            mean, std = checkpoint.strategies[name].model.predict(coords)
            excursions.append(f"{name}: {np.count_nonzero((mean < -1) | (mean > 1))}/{len(mean)} means; "
                              f"{np.count_nonzero((mean - 1.96 * std < -1) | (mean + 1.96 * std > 1))}/{len(mean)} bands")
        st.caption("Outside physical range [−1, 1] on this slice — " + "; ".join(excursions) + ". Estimates are never clipped.")
    with tabs[3]:
        rows = [{"Strategy": name.title(), **checkpoint.strategies[name].metrics} for name in ("adaptive", "random")]
        st.table(pd.DataFrame(rows).set_index("Strategy"))
        st.caption("Interval coverage is the empirical fraction inside mean ± 1.96σ; interval width and coverage are diagnostics.")
        st.write("Counts at this completed paired step")
        st.json(checkpoint.counts)
        st.caption("Each strategy pays one label per acquired point, including shared/cache-reused values. "
                   "Cache hits save numerical work, not learning budget. Zero-time labels use the exact initial condition. "
                   "Evaluation labels and visualization trajectories never enter training.")
        timing_scope = ("includes preparation; excludes checkpoint writes, idle pause time, and rendering"
                        if run.metadata['schema_version'] == 3 else
                        "includes preparation and earlier checkpoints; excludes this checkpoint's disk commit and rendering")
        st.write(f"Elapsed computation through this step: {checkpoint.elapsed_seconds:.3f} s; {timing_scope}. "
                 "Time is not sample efficiency.")
        st.write(f"Run ID: `{run.run_id}` · model revision {revision} · created {run.metadata['created_at']}")
        st.write(f"Evaluation identity: `{run.evaluation.identity}`")
        for name in ("adaptive", "random"):
            with st.expander(f"{name.title()} observations, fitted kernel, and warnings"):
                state = checkpoint.strategies[name]
                st.table(pd.DataFrame([{"Candidate ID": item.candidate_id,
                    "γ": run.candidates[item.candidate_id, 0], "t": run.candidates[item.candidate_id, 1],
                    "Numerical x": item.value} for item in state.observations]).set_index("Candidate ID"))
                st.json({"amplitude": state.model.amplitude, "scaled_length_scales": state.model.length_scales.tolist(),
                         "warnings": list(state.model.warnings), "selection": state.selection})
        with st.expander("Configuration, validation, and provenance"):
            st.json(run.metadata)

    with st.expander("Download evidence"):
        st.caption(f"Completed revision {revision} · {revision + 8} labels each. Observations use this revision; metrics include history through it.")
        files = export_evidence(run, revision)
        for column, (kind, label) in zip(st.columns(3), (("configuration", "Configuration JSON"),
                                         ("observations", "Observations CSV"), ("metrics", "Metrics CSV"))):
            item = files[kind]
            with column:
                st.download_button(label, item.content, file_name=item.filename, mime=item.mime,
                                   key=f"export-{run.run_id}-{revision}-{kind}", on_click="ignore", width="stretch")


def learning_panel(repository, theme, run_id, source="saved"):
    interval = 0.25 if learning_session(repository.root).snapshot().active else None
    st.fragment(_learning_panel, run_every=interval)(repository, theme, run_id, source)


def _learning_panel(repository, theme, run_id, source="saved"):
    session = learning_session(repository.root)
    live = session.snapshot()
    run = live.run if live.run is not None and live.run.run_id == run_id else st.session_state.get("active_run")
    if run is None or run.run_id != run_id:
        return
    st.session_state["active_run"] = run
    active = live.active and live.run.run_id == run_id
    if not live.active and st.session_state.pop('learning_active_at_render', False):
        st.rerun()
    if active:
        st.write(f"**Live computation · {live.stage}**")
        st.progress(min(1., live.done / max(live.total, 1)), text=f"{live.done}/{live.total} · {live.stage}")
        if st.button("Pause after this step", key=f"pause-{run_id}", disabled=live.pause_requested):
            session.request_pause()
        if live.pause_requested:
            st.info("Pause requested. Finishing and saving the whole paired step before stopping.")
        if run.checkpoints:
            st.caption(f"Latest confirmed paired step: {run.latest.iteration} · {run.latest.iteration + 8} labels each.")
            plot(learning_curves(run, theme), f"live-learning-{run_id}")
            selection = run.latest.strategies['adaptive'].next_selection
            if selection:
                point = run.candidates[selection['candidate_id']]
                st.caption(f"Next adaptive point: γ = {point[0]:.3f}, t = {point[1]:.3f}; estimated σ = {selection['score']:.6f}.")
        else:
            st.caption("Preparing the first shared fit. A pause takes effect after that checkpoint is saved.")
        return
    if live.run is not None and live.run.run_id == run_id and live.error:
        st.error(live.error)
    elif not run.checkpoints and run.metadata.get('failure'):
        st.error(f"Stopped: {run.metadata['failure']['message']}")
    if run.metadata['status'] in {'paused', 'interrupted', 'failed'}:
        status = run.metadata['status'].capitalize()
        if run.checkpoints:
            st.info(f"{status} · saved paired step {run.latest.iteration}, {run.latest.iteration + 8} labels each. "
                    "Resume uses this run's original settings, observations, models, and random state.")
            if st.button("Resume experiment", key=f"resume-{run_id}", type="primary", disabled=live.active):
                try:
                    session.resume(run_id)
                    st.session_state.pop(f'revision-{run_id}', None)
                    st.session_state['result_source'] = 'live'
                    st.rerun()
                except RepositoryError as exc:
                    st.error(str(exc))
        else:
            st.warning(f"{status} before the first complete checkpoint. There is no saved model to resume.")
            if st.button("Restart as new run", key=f"restart-{run_id}", type="primary", disabled=live.active):
                try:
                    new_id = session.start(run.config)
                    st.session_state['active_run'] = session.snapshot().run
                    st.session_state['saved_opened_id'] = new_id
                    st.session_state['result_source'] = 'live'
                    st.rerun()
                except RepositoryError as exc:
                    st.error(str(exc))
    if run.checkpoints:
        show_learning_result(run, source, theme)
    else:
        st.caption(f"Run ID: {run.run_id} · original seed {run.config.seed}. The original record is preserved.")
        with st.expander("Original configuration and provenance"):
            st.json(run.metadata)


def learning_view(repository, theme, opening=None):
    st.title("Learn where to simulate next")
    st.markdown('<p class="intro">Qentis learns from simulated qubit behavior and chooses where to simulate next.</p>', unsafe_allow_html=True)
    if opening is not None:
        opening(repository)
    session = learning_session(repository.root)
    live = session.snapshot()
    controls, evidence = st.columns([1, 3.4], gap="large")
    with controls:
        st.markdown("### Short live comparison")
        st.caption("Fixed |+⟩ initial state · pure dephasing · learned coherence x")
        st.write("**8 shared starting points**  \n+16 acquired points per strategy")
        defaults = st.session_state.get('next_learning_config', LearningConfig().to_dict())
        with st.form("learning-settings", border=False):
            seed = st.number_input("Seed", min_value=0, max_value=4294967295, value=defaults['seed'], step=1)
            with st.expander("Advanced protocol"):
                gamma = st.number_input("Rate upper bound γ (1/time)", min_value=0.01, max_value=2., value=defaults['gamma_max'], step=0.01)
                time = st.number_input("Time upper bound (units)", min_value=0.01, max_value=5., value=defaults['time_max'], step=0.01)
                budget = st.number_input("Total labels per strategy", min_value=8, max_value=64, value=defaults['total_budget'], step=1)
                grid = st.number_input("Candidates per axis", min_value=3, max_value=31, value=defaults['grid_size'], step=1)
            submitted = st.form_submit_button("Run experiment", type="primary", width="stretch", disabled=live.active)
        st.caption("Settings apply to a new run. Resume keeps the saved protocol. No result is guaranteed to favor adaptive selection.")
    with evidence:
        if submitted:
            try:
                config = LearningConfig(seed=seed, gamma_max=gamma, time_max=time, grid_size=grid, total_budget=budget)
                session.start(config)
                st.session_state['active_run'] = session.snapshot().run
                st.session_state['result_source'] = 'live'
                st.rerun()
            except (ConfigurationError, RepositoryError) as exc:
                st.error(str(exc))
        live = session.snapshot()
        if live.active:
            st.session_state['active_run'] = live.run
            st.session_state['result_source'] = 'live'
        run = st.session_state.get('active_run')
        if isinstance(run, LearningRun):
            learning_panel(repository, theme, run.run_id, st.session_state.get('result_source', 'saved'))
        else:
            st.markdown('''<section class="ready"><h2>Observe. Learn. Choose. Repeat.</h2>
              <p>Two models start with the same eight numerical observations.
              One chooses the point with the most estimated uncertainty;
              the other chooses randomly. Compare their measured error at equal budgets.</p>
              <div class="protocol-strip"><div><strong>Acquire</strong>One numerical label per point</div>
              <div><strong>Fit</strong>The same Gaussian-process policy</div>
              <div><strong>Evaluate</strong>400 separate held-out points</div></div>
              <p class="quiet">Select Run experiment to compute and save a real comparison.</p></section>''', unsafe_allow_html=True)
