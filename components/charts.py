"""
🐺 Wolf Wallet — Charts Component

Gráficos reutilizáveis com Plotly, alinhados à paleta do projeto.

Usage:
    from components.charts import bar_chart_inflows_outflows, line_chart_yields
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from config.settings import Colors


def _base_layout(title: str = "") -> dict:
    """Layout base para todos os gráficos Plotly."""
    return {
        "title": {"text": title, "font": {"size": 16, "color": "#FAFAFA"}},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": "#B0B0B0", "size": 12},
        "margin": {"l": 40, "r": 20, "t": 50, "b": 40},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 11},
        },
        "xaxis": {
            "gridcolor": "rgba(255,255,255,0.05)",
            "showgrid": False,
            "fixedrange": True,
        },
        "yaxis": {
            "gridcolor": "rgba(255,255,255,0.08)",
            "tickprefix": "R$ ",
            "tickformat": ",.0f",
            "fixedrange": True,
        },
        "dragmode": False,
        "hovermode": "x unified",
    }


def bar_chart_inflows_outflows(df: pd.DataFrame) -> go.Figure:
    """
    Gráfico de barras agrupadas: Entradas vs Saídas por mês.

    Args:
        df: DataFrame com colunas: month, inflows, outflows.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    if df.empty:
        fig.add_annotation(
            text="Sem dados para o período selecionado",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font={"size": 16, "color": "#B0B0B0"},
        )
        fig.update_layout(**_base_layout())
        return fig

    # Formata labels dos meses (YYYY-MM → MM/YYYY)
    months = df["month"].tolist()
    labels = []
    for m in months:
        parts = str(m).split("-")
        if len(parts) == 2:
            labels.append(f"{parts[1]}/{parts[0]}")
        else:
            labels.append(str(m))

    fig.add_trace(go.Bar(
        name="Entradas",
        x=labels,
        y=df["inflows"].astype(float),
        marker_color=Colors.POSITIVE,
        marker_line_width=0,
        hovertemplate="Entradas: R$ %{y:,.2f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        name="Saídas",
        x=labels,
        y=df["outflows"].astype(float),
        marker_color=Colors.NEGATIVE,
        marker_line_width=0,
        hovertemplate="Saídas: R$ %{y:,.2f}<extra></extra>",
    ))

    layout = _base_layout("Entradas vs Saídas")
    layout["barmode"] = "group"
    layout["bargap"] = 0.2
    layout["bargroupgap"] = 0.1
    fig.update_layout(**layout)

    return fig


def line_chart_yields(df: pd.DataFrame) -> go.Figure:
    """
    Gráfico de linha: Rendimento líquido mensal.

    Args:
        df: DataFrame com colunas: month, net_yield.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    if df.empty:
        fig.add_annotation(
            text="Sem dados de rendimento",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font={"size": 16, "color": "#B0B0B0"},
        )
        fig.update_layout(**_base_layout())
        return fig

    months = df["month"].tolist()
    labels = []
    for m in months:
        parts = str(m).split("-")
        if len(parts) == 2:
            labels.append(f"{parts[1]}/{parts[0]}")
        else:
            labels.append(str(m))

    fig.add_trace(go.Scatter(
        name="Rendimento Líquido",
        x=labels,
        y=df["net_yield"].astype(float),
        mode="lines+markers",
        line={"color": Colors.YIELD, "width": 3},
        marker={"size": 8, "color": Colors.YIELD},
        fill="tozeroy",
        fillcolor="rgba(255, 214, 0, 0.1)",
        hovertemplate="Rendimento: R$ %{y:,.2f}<extra></extra>",
    ))

    fig.update_layout(**_base_layout("Rendimento Mensal (CDI)"))

    return fig
