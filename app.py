"""The single local Qentis dashboard. Launch with ./run.sh."""

import base64
from datetime import datetime, timezone
import os
from pathlib import Path

import streamlit as st

from qentis.charts import bloch_sphere, coherence_trajectory
from qentis.config import ConfigurationError, ExperimentConfig
from qentis.experiment import Run, create_run
from qentis.physics import SimulationError
from qentis.repository import RepositoryError, RunRepository
from qentis.learning import LearningRun
from qentis.runtime import learning_session
from qentis.learning_ui import learning_view, learning_panel
from qentis.theme import palette
from qentis.benchmark_ui import benchmark_view, presentation_opening

ROOT = Path(__file__).resolve().parent
PLOT_CONFIG = {"displaylogo": False, "displayModeBar": False, "scrollZoom": False}


def install_design(theme="Dark") -> None:
    fonts = []
    for family, filename in (("IBM Plex Sans", "IBMPlexSans-Regular.woff2"),
                             ("IBM Plex Mono", "IBMPlexMono-Regular.woff2")):
        path = ROOT / "assets/fonts" / filename
        if path.exists():
            encoded = base64.b64encode(path.read_bytes()).decode()
            fonts.append(f'@font-face {{font-family:"{family}";src:url(data:font/woff2;base64,{encoded}) format("woff2");font-weight:400;font-display:swap;}}')
    st.markdown(f"<style>{''.join(fonts)}{(ROOT / 'assets/dashboard.css').read_text()}</style>", unsafe_allow_html=True)
    tokens = ";".join(f"--{key}:{value}" for key, value in palette(theme).items())
    st.markdown(f"<style>:root {{{tokens};color-scheme:{theme.lower()};}}</style>", unsafe_allow_html=True)
    logo = base64.b64encode((ROOT / "assets/brand/qentis-logo-reference.png").read_bytes()).decode()
    st.markdown(f"""<header class="brand-header">
      <div class="brand-lockup"><img src="data:image/png;base64,{logo}" alt="" />
      <div><div class="brand-name">Qentis</div><div class="brand-description">Adaptive Quantum Discovery</div></div></div>
      <span class="scope-label">Simulation only</span>
    </header>""", unsafe_allow_html=True)


def display_date(value: str) -> str:
    # Keep timestamps explicit and unambiguous across machines and time zones.
    return datetime.fromisoformat(value).astimezone(timezone.utc).strftime("%d %b %Y · %H:%M UTC")


def show_result(run: Run, source: str) -> None:
    theme = "Dark" if st.session_state.get("dark_mode", True) else "Light"
    if isinstance(run, LearningRun):
        learning_panel(RunRepository(os.environ.get("QENTIS_RUNS_DIR", str(ROOT / "runs"))), theme, run.run_id, source)
        return
    data, metadata = run.trajectory, run.metadata
    is_saved = source == "saved"
    label = "Saved result" if is_saved else "Live computation · complete"
    st.markdown(f'<div class="result-heading"><h2>Numerical reference</h2>'
                f'<span class="result-status {"saved" if is_saved else ""}">{label}</span></div>', unsafe_allow_html=True)
    st.caption(f"γ = {run.config.gamma:g} inverse time units · |+⟩ initial state · {display_date(metadata['created_at'])}")
    index = st.select_slider("Inspect time (dimensionless units)", options=list(range(len(data.times))),
                             value=0, format_func=lambda i: f"{data.times[i]:.3f}", key=f"time-{run.run_id}",
                             help="Use the arrow keys to step through stored time samples. Both charts show the same time.")
    sphere, trajectory = st.columns([0.9, 1.25], gap="medium")
    with sphere:
        st.markdown("### Bloch sphere")
        st.plotly_chart(bloch_sphere(data, index, theme), config=PLOT_CONFIG, use_container_width=True, theme=None, key=f"sphere-{run.run_id}")
    with trajectory:
        st.markdown("### Coherence trajectory")
        st.plotly_chart(coherence_trajectory(data, index, theme), config=PLOT_CONFIG, use_container_width=True, theme=None, key=f"trajectory-{run.run_id}")
    x, y, z = data.bloch[index]
    p0, p1 = data.populations[index]
    st.markdown(f'<div class="readout"><span>t<strong>{data.times[index]:.3f}</strong></span>'
                f'<span>x<strong>{x:.5f}</strong></span><span>y<strong>{y:.5f}</strong></span>'
                f'<span>z<strong>{z:.5f}</strong></span><span>p₀ / p₁<strong>{p0:.3f} / {p1:.3f}</strong></span>'
                f'<span>Purity<strong>{data.purity[index]:.5f}</strong></span></div>', unsafe_allow_html=True)
    report = metadata["trajectory_validation"]
    st.caption(f"Validation passed · max |x − exp(−γt)| = {report['max_analytical_error']:.2e} (limit 1e−6). "
               "Trace, Hermiticity, eigenvalues, Bloch radius, and populations pass at 1e−8.")
    st.caption(f"{len(data.times)} time samples · 1 visualization solve · "
               f"{metadata['counts']['validation_solver_calls']} validation solves · 0 acquired training labels")
    if metadata["numerical_warnings"]:
        st.warning("Solver warnings: " + "; ".join(metadata["numerical_warnings"]))
    with st.expander("Saved record and numerical validation"):
        st.markdown(f"**Run ID**  \n`{run.run_id}`")
        st.write("Saved on this laptop. The configuration is immutable; changing settings creates a new run.")
        st.write(f"Simulation and validation: {metadata['timing']['reference_and_validation_seconds']:.3f} s. "
                 "Inspecting the time slider performs no solver calls.")
        st.json(metadata)


def assumptions() -> None:
    with st.expander("Physical assumptions and solver convention"):
        st.markdown("""
**One qubit, initially |+⟩ = (|0⟩ + |1⟩) / √2.** The Hamiltonian is H = 0 and ℏ = 1.
Pure dephasing uses **L = √(γ / 2) σz**, so dρ/dt = (γ/2)(σz ρ σz − ρ).

Time is in dimensionless units; γ is in inverse time units. The displayed
coherence is **x = 2 Re(ρ₀₁)**. Dephasing reduces x while populations stay at ½.
The Bloch components are x, y = −2 Im(ρ₀₁), and z = ρ₀₀ − ρ₁₁. Purity is Tr(ρ²).

**Numerical method:** QuTiP `mesolve`, Adams integrator, absolute tolerance 1e−10,
relative tolerance 1e−8, maximum 10,000 internal steps, output normalization off.
All plotted states are numerical reference data. The analytical x = exp(−γt)
is used only for validation, with a maximum discrepancy of 1e−6. Physical
invariants use tolerance 1e−8. Every run checks γ = 0, 1, 2 and t = 0 boundaries
before presentation data can be saved.

The learned output is one coherence observable, not full-state tomography.
The response depends simply on γt. This is a workflow proof of concept, not
new quantum physics, quantum advantage, or guaranteed adaptive superiority.
""")


def simulation_view(repository: RunRepository) -> None:
    st.title("Qubit dephasing")
    st.markdown('<p class="intro">Follow a quantum state as phase coherence decays.</p>', unsafe_allow_html=True)
    controls, evidence = st.columns([1, 3.4], gap="large")
    with controls:
        st.markdown("### Experiment settings")
        st.markdown('<div class="fixed-state">Fixed initial state<strong>|+⟩ = (|0⟩ + |1⟩) / √2</strong></div>', unsafe_allow_html=True)
        with st.form("simulation-settings", border=False):
            gamma = st.number_input("Dephasing rate γ (1/time)", min_value=0.0, max_value=2.0, value=1.0,
                                    step=0.1, format="%.2f", help="Inverse time units. At γ = 0 there is no dephasing.")
            max_time = st.number_input("Maximum time (units)", min_value=0.01, max_value=5.0, value=5.0,
                                       step=0.01, format="%.2f", help="Dimensionless time units. Must be greater than zero.")
            with st.expander("Sampling settings"):
                samples = st.number_input("Time samples", min_value=2, max_value=1001, value=201, step=1,
                                          help="Visualization samples; these are not acquired training labels.")
            submitted = st.form_submit_button("Run simulation", type="primary", width="stretch",
                                             disabled=learning_session(repository.root).snapshot().active)
        st.caption("Validates the solver, computes the trajectory, and saves a new result locally.")
    with evidence:
        if submitted:
            try:
                configuration = ExperimentConfig(gamma, max_time, samples)
                with st.status("Live computation · checking the numerical reference", expanded=True) as progress:
                    st.write("Checking analytical agreement, physical invariants, and boundary cases.")
                    run = create_run(configuration)
                    progress.update(label="Live computation · saving validated numerical states")
                    repository.save(run)
                    progress.update(label="Simulation complete · saved on this laptop", state="complete", expanded=False)
                st.session_state["active_run"] = run
                st.session_state["result_source"] = "live"
                st.rerun()
            except (ConfigurationError, SimulationError, RepositoryError, OSError) as exc:
                st.error(f"Simulation was not completed and confirmed saved. {exc}")
        run = st.session_state.get("active_run")
        if isinstance(run, Run):
            show_result(run, st.session_state.get("result_source", "saved"))
        else:
            st.markdown('''<section class="ready"><h2>See what dephasing changes.</h2>
              <p>Start with a qubit in an equal superposition. Choose a dephasing rate,
              then inspect its numerical state at any sampled time.</p>
              <div class="ready-equation" aria-label="The initial plus state evolves to a density matrix at time t">|+⟩ → ρ(t)</div>
              <div class="protocol-strip"><div><strong>Compute</strong>Numerical Lindblad evolution</div>
              <div><strong>Check</strong>Analytical and physical validation</div>
              <div><strong>Keep</strong>Saved states and provenance</div></div>
              <p class="quiet">No result has been computed yet. Select Run simulation to begin.</p></section>''', unsafe_allow_html=True)
    assumptions()


def experiment_view(repository):
    kind = st.radio("Experiment type", ["Learning comparison", "Qubit simulation"], horizontal=True, key="experiment_type", label_visibility="collapsed")
    if kind == "Learning comparison":
        learning_view(repository, "Dark" if st.session_state.get("dark_mode", True) else "Light", presentation_opening)
        assumptions()
    else:
        simulation_view(repository)


def saved_view(repository: RunRepository) -> None:
    st.title("Saved runs")
    st.markdown('<p class="intro">Reopen saved evidence, recover an interrupted experiment, or download its record.</p>', unsafe_allow_html=True)
    try:
        runs = repository.list_runs()
    except RepositoryError as exc:
        st.error(str(exc))
        return
    if not runs:
        st.info("No saved runs yet. Open Experiment and select Run simulation to save your first result.")
        if st.button("Go to Experiment"):
            st.session_state["go_experiment"] = True
            st.rerun()
        return
    summaries = {item.run_id: item for item in runs}

    def label(run_id: str) -> str:
        summary = summaries[run_id]
        if summary.error:
            return f"{run_id} · unavailable"
        if "seed" in summary.configuration:
            return f"{display_date(summary.created_at)} · learning · seed {summary.configuration['seed']} · {run_id}"
        return (f"{display_date(summary.created_at)} · γ = {summary.configuration['gamma']:g} · "
                f"t ≤ {summary.configuration['max_time']:g} · {run_id}")

    selected = st.selectbox("Choose a saved run", options=list(summaries), format_func=label)
    if st.button("Open selected run", type="primary"):
        try:
            run = repository.load(selected)
            st.session_state["active_run"] = run
            st.session_state["result_source"] = "saved"
            st.session_state["saved_opened_id"] = selected
        except RepositoryError as exc:
            st.session_state.pop("saved_opened_id", None)
            st.error(f"Could not open {selected}. {exc}")
            st.info("Restore the complete original run folder from a backup, or use its recorded pinned environment. "
                    "The original files have not been changed. A damaged model cannot be resumed.")
            if summaries[selected].configuration is not None:
                st.write("Intact configuration and date")
                st.json({"created_at": summaries[selected].created_at, "configuration": summaries[selected].configuration})
    if (st.session_state.get("saved_opened_id") == selected
            and st.session_state.get("active_run") is not None
            and st.session_state["active_run"].run_id == selected):
        show_result(st.session_state["active_run"], "saved")
        assumptions()
    st.caption(f"Results folder: {repository.root}")


def main() -> None:
    st.set_page_config(page_title="Qentis · Qubit dephasing", layout="wide", initial_sidebar_state="collapsed")
    theme = "Dark" if st.session_state.get("dark_mode", True) else "Light"
    install_design(theme)
    # An explicit view switch is handled before creating the navigation widget.
    if st.session_state.pop("go_experiment", False):
        st.session_state["view"] = "Experiment"
    nav, appearance = st.columns([5, 1])
    with nav:
        view = st.radio("Dashboard view", ["Experiment", "Saved runs", "Benchmark"], horizontal=True,
                        key="view", label_visibility="collapsed")
    with appearance:
        st.toggle("Dark mode", value=True, key="dark_mode")
    repository = RunRepository(os.environ.get("QENTIS_RUNS_DIR", str(ROOT / "runs")))
    st.session_state['learning_active_at_render'] = learning_session(repository.root).snapshot().active
    if view == "Experiment":
        experiment_view(repository)
    elif view == "Saved runs":
        saved_view(repository)
    else:
        benchmark_view(repository, theme)
        assumptions()


if __name__ == "__main__":
    main()
