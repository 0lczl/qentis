"""Charts use stored numerical states only; inspecting a chart never solves again."""

import numpy as np
import plotly.graph_objects as go

from .physics import Trajectory
from .theme import palette

TEXT = "#F4F1FA"
MUTED = "#B9B2C8"
REFERENCE = "#68D9D1"
ACCENT = "#B89AFF"
SURFACE = "#121218"


def _layout(figure: go.Figure, theme="Dark") -> go.Figure:
    c = palette(theme)
    TEXT, SURFACE = c["text"], c["surface"]
    figure.update_layout(
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font={"family": "IBM Plex Sans, sans-serif", "size": 14, "color": TEXT},
        height=300, margin={"l": 8, "r": 8, "t": 8, "b": 8},
        hoverlabel={"bgcolor": c["surface-raised"], "font_size": 14, "font_color": TEXT},
    )
    return figure


def bloch_sphere(trajectory: Trajectory, index: int, theme="Dark") -> go.Figure:
    c = palette(theme)
    TEXT, MUTED, REFERENCE, ACCENT, SURFACE = (c[k] for k in ("text", "muted", "reference", "accent", "surface"))
    figure = go.Figure()
    circle = np.linspace(0, 2 * np.pi, 81)
    for angle in np.linspace(0, np.pi, 6, endpoint=False):
        figure.add_trace(go.Scatter3d(
            x=np.sin(circle) * np.cos(angle), y=np.sin(circle) * np.sin(angle), z=np.cos(circle),
            mode="lines", line={"color": "#777180", "width": 1}, opacity=0.45,
            hoverinfo="skip", showlegend=False,
        ))
    for latitude in (-np.pi / 4, 0, np.pi / 4):
        figure.add_trace(go.Scatter3d(
            x=np.cos(latitude) * np.cos(circle), y=np.cos(latitude) * np.sin(circle),
            z=np.full_like(circle, np.sin(latitude)),
            mode="lines", line={"color": "#777180", "width": 1}, opacity=0.45,
            hoverinfo="skip", showlegend=False,
        ))
    for end, label in (((1.14, 0, 0), "+x"), ((0, 1.14, 0), "+y"),
                       ((0, 0, 1.14), "|0⟩"), ((0, 0, -1.14), "|1⟩")):
        figure.add_trace(go.Scatter3d(
            x=[0, end[0]], y=[0, end[1]], z=[0, end[2]], mode="lines+text",
            text=["", label], textposition="middle center", textfont={"color": MUTED, "size": 14},
            line={"color": "#777180", "width": 2, "dash": "dot"}, hoverinfo="skip", showlegend=False,
        ))
    vector = trajectory.bloch[index]
    figure.add_trace(go.Scatter3d(
        x=[0, vector[0]], y=[0, vector[1]], z=[0, vector[2]], mode="lines+markers",
        name="Numerical reference state", line={"color": REFERENCE, "width": 7},
        marker={"color": REFERENCE, "size": [3, 7]},
        hovertemplate="x = %{x:.5f}<br>y = %{y:.5f}<br>z = %{z:.5f}<extra>Numerical reference</extra>",
        showlegend=False,
    ))
    figure.update_layout(scene={
        "xaxis": {"visible": False, "range": [-1.25, 1.25]},
        "yaxis": {"visible": False, "range": [-1.25, 1.25]},
        "zaxis": {"visible": False, "range": [-1.25, 1.25]},
        "bgcolor": SURFACE, "aspectmode": "cube",
        "camera": {"eye": {"x": 0.85, "y": 0.95, "z": 0.5}},
    }, uirevision=trajectory.gamma, dragmode="orbit")
    return _layout(figure, theme)


def coherence_trajectory(trajectory: Trajectory, index: int, theme="Dark") -> go.Figure:
    c = palette(theme)
    TEXT, MUTED, REFERENCE, ACCENT, SURFACE = (c[k] for k in ("text", "muted", "reference", "accent", "surface"))
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=trajectory.times, y=trajectory.bloch[:, 0], mode="lines", name="Coherence x · reference",
        line={"color": REFERENCE, "width": 3},
        hovertemplate="x = %{y:.6f}<extra>Numerical reference</extra>",
    ))
    figure.add_trace(go.Scatter(
        x=trajectory.times, y=trajectory.populations[:, 0], mode="lines", name="Populations p₀ = p₁",
        line={"color": MUTED, "width": 2, "dash": "dash"},
        hovertemplate="p₀ = p₁ = %{y:.6f}<extra>Numerical reference</extra>",
    ))
    time, value = trajectory.times[index], trajectory.bloch[index, 0]
    figure.add_vline(x=time, line={"color": ACCENT, "width": 1, "dash": "dot"})
    figure.add_trace(go.Scatter(
        x=[time], y=[value], mode="markers", name="Selected time", showlegend=False,
        marker={"color": SURFACE, "line": {"color": REFERENCE, "width": 3}, "size": 10},
        hovertemplate="t = %{x:.3f}<br>x = %{y:.6f}<extra>Selected time</extra>",
    ))
    _layout(figure, theme)
    figure.update_layout(
        margin={"l": 0, "r": 16, "t": 6, "b": 0}, hovermode="x unified",
        xaxis={"title": "Time (dimensionless units)", "range": [0, float(trajectory.times[-1])],
               "gridcolor": c["border"], "zeroline": False, "fixedrange": True},
        yaxis={"title": "Coherence / population", "range": [-0.05, 1.08], "tickvals": [0, 0.5, 1],
               "gridcolor": c["border"], "zeroline": False, "fixedrange": True},
        legend={"orientation": "h", "y": -0.27, "x": 0, "font": {"size": 14},
                "itemclick": False, "itemdoubleclick": False},
    )
    figure.update_xaxes(automargin=True)
    figure.update_yaxes(automargin=True)
    return figure
