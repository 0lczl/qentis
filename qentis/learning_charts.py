"""Measured learning evidence, with distinct estimated and held-out quantities."""
import numpy as np
import plotly.graph_objects as go

from .charts import _layout
from .theme import palette


def _axes(fig, theme, x, y):
    c = palette(theme)
    _layout(fig, theme)
    fig.update_layout(height=360, margin={"l": 70, "r": 60, "t": 24, "b": 100},
                      xaxis={"title": {"text": x, "standoff": 12, "font_size": 14}, "automargin": True,
                             "gridcolor": c["border"], "zeroline": False, "tickfont_size": 13},
                      yaxis={"title": {"text": y, "standoff": 12, "font_size": 14}, "automargin": True,
                             "gridcolor": c["border"], "zeroline": False, "tickfont_size": 13},
                      legend={"orientation": "h", "y": -0.45, "x": 0, "font_size": 13},
                      hovermode="closest")
    return fig


def learning_curves(run, theme="Dark"):
    c = palette(theme)
    fig = go.Figure()
    for name, color, dash, symbol in (("adaptive", c["accent"], "solid", "circle"),
                                       ("random", c["random"], "dash", "diamond")):
        fig.add_trace(go.Scatter(x=[8 + item.iteration for item in run.checkpoints],
                                 y=[item.strategies[name].metrics["rmse"] for item in run.checkpoints],
                                 mode="lines+markers", name=name.title(),
                                 line={"color": color, "dash": dash, "width": 2}, marker={"symbol": symbol, "size": 6},
                                 hovertemplate="%{x} labels<br>RMSE %{y:.6f}<extra>%{fullData.name}</extra>"))
    _axes(fig, theme, "Acquired labels per strategy (including 8 shared)", "Held-out RMSE of x")
    fig.update_xaxes(range=[7.5, run.config.total_budget + 0.5], dtick=4)
    fig.update_yaxes(rangemode="tozero")
    return fig


def prediction_trajectory(data, checkpoint, index, theme="Dark"):
    c = palette(theme)
    points = np.column_stack((np.full_like(data.times, data.gamma), data.times))
    fig = go.Figure()
    for name, color, dash in (("adaptive", c["accent"], "dashdot"), ("random", c["random"], "dash")):
        mean, std = checkpoint.strategies[name].model.predict(points)
        fig.add_trace(go.Scatter(x=np.r_[data.times, data.times[::-1]],
                                 y=np.r_[mean + 1.96 * std, (mean - 1.96 * std)[::-1]],
                                 fill="toself", fillcolor=color, opacity=0.12, line_width=0,
                                 name=f"{name.title()} estimated 95% interval", hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=data.times, y=mean, name=f"{name.title()} estimate", mode="lines",
                                 line={"color": color, "dash": dash, "width": 2},
                                 hovertemplate="x̂ = %{y:.6f}<extra>%{fullData.name}</extra>"))
    fig.add_trace(go.Scatter(x=data.times, y=data.bloch[:, 0], name="Numerical reference", mode="lines",
                             line={"color": c["reference"], "width": 3},
                             hovertemplate="x = %{y:.6f}<extra>Numerical reference</extra>"))
    fig.add_vline(x=data.times[index], line_dash="dot", line_color=c["muted"])
    _axes(fig, theme, "Time (dimensionless units)", "Coherence x / learned x̂")
    fig.update_layout(hovermode="x unified")
    return fig


def uncertainty_map(run, checkpoint, theme="Dark"):
    c = palette(theme)
    state = checkpoint.strategies["adaptive"]
    grid = run.config.grid_size
    values = state.candidate_std.reshape(grid, grid)
    fig = go.Figure(go.Heatmap(x=np.linspace(0, run.config.gamma_max, grid),
                               y=np.linspace(0, run.config.time_max, grid), z=values.T,
                               zmin=0, zmax=1, colorscale=[[0, c["surface"]], [1, c["accent"]]],
                               colorbar={"title": "σ̂", "thickness": 12, "len": 0.8},
                               hovertemplate="γ %{x:.2f}<br>t %{y:.2f}<br>Estimated σ %{z:.6f}<extra></extra>"))
    points = run.candidates[state.ids]
    fig.add_trace(go.Scatter(x=points[:, 0], y=points[:, 1], mode="markers", name="Acquired",
                             marker={"color": c["text"], "size": 6, "symbol": "circle-open"}))
    selection = state.next_selection or state.selection
    if selection:
        point = run.candidates[selection["candidate_id"]]
        fig.add_trace(go.Scatter(x=[point[0]], y=[point[1]], mode="markers", name="Next point" if state.next_selection else "Last acquired",
                                 marker={"color": c["reference"], "size": 13, "symbol": "x"}))
    return _axes(fig, theme, "Dephasing rate γ (1/time)", "Time (dimensionless units)")


def error_map(run, checkpoint, strategy, theme="Dark"):
    c = palette(theme)
    errors = np.abs(checkpoint.strategies[strategy].evaluation_mean - run.evaluation.labels)
    fig = go.Figure(go.Scatter(x=run.evaluation.points[:, 0], y=run.evaluation.points[:, 1], mode="markers",
                               customdata=errors, marker={"size": 7, "color": errors, "cmin": 0, "cmax": 1,
                                    "colorscale": [[0, c["surface"]], [1, c["random"]]],
                                    "line": {"width": 0.3, "color": c["muted"]},
                                    "colorbar": {"title": "|error|", "thickness": 12, "len": 0.8}},
                               hovertemplate="γ %{x:.3f}<br>t %{y:.3f}<br>|error| %{customdata:.6f}<extra>Evaluation only</extra>",
                               showlegend=False))
    _axes(fig, theme, "Dephasing rate γ (1/time)", "Time (dimensionless units)")
    fig.update_xaxes(range=[0, run.config.gamma_max])
    fig.update_yaxes(range=[0, run.config.time_max])
    return fig
