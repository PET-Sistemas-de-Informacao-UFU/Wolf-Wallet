"""
🐺 Wolf Wallet — Painel de Auditoria (Admin)

Visualização de acessos ao sistema (somente admin):
    - Cards: total, logins de membros, visitantes, usuários únicos
    - Ranking: quem mais acessa (por email)
    - Série temporal: acessos de membros x visitantes
    - Tabela: últimos acessos

Usage:
    from pages.admin_auditoria import render_admin_auditoria
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth.session import require_admin
from config.settings import Colors, to_brasilia


_PERIODS: dict[str, int] = {
    "Últimos 7 dias": 7,
    "Últimos 30 dias": 30,
    "Últimos 90 dias": 90,
    "Último ano": 365,
}


def render_admin_auditoria() -> None:
    """Renderiza o painel de auditoria de acessos."""
    if not require_admin():
        return

    st.title("📊 Auditoria de Acessos")
    st.caption("Quem acessa o Wolf Wallet, com que frequência, e o volume de visitantes.")

    period_label = st.selectbox(
        "Período",
        options=list(_PERIODS.keys()),
        index=1,  # 30 dias
        key="audit_period",
    )
    days = _PERIODS[period_label]

    try:
        from models.access_log import (
            get_access_stats,
            get_access_timeseries,
            get_recent_accesses,
            get_top_users,
        )

        stats = get_access_stats(days)
        _render_cards(stats)

        st.divider()
        col_rank, col_chart = st.columns([1, 1.3])
        with col_rank:
            _render_ranking(get_top_users(days))
        with col_chart:
            _render_timeseries(get_access_timeseries(days))

        st.divider()
        _render_recent(get_recent_accesses(30))

    except Exception as e:
        st.error(f"⚠️ Erro ao carregar auditoria: {e}")
        st.info("Verifique se a tabela `access_log` existe no banco (sql/schema.sql).")


def _render_cards(stats: dict) -> None:
    """Cards com os números principais."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de acessos", int(stats.get("total", 0) or 0))
    with col2:
        st.metric("👤 Logins de membros", int(stats.get("logins", 0) or 0))
    with col3:
        st.metric("👀 Visitantes", int(stats.get("visitors", 0) or 0))
    with col4:
        st.metric("Membros únicos", int(stats.get("unique_users", 0) or 0))


def _render_ranking(rows: list[dict]) -> None:
    """Ranking de quem mais acessa (por email)."""
    st.markdown("##### 🏆 Quem mais acessa")

    if not rows:
        st.info("Nenhum login de membro no período.")
        return

    df = pd.DataFrame(rows)
    df = df.rename(columns={
        "user_email": "Membro",
        "role": "Papel",
        "accesses": "Acessos",
        "last_access": "Último acesso",
    })
    df["Último acesso"] = df["Último acesso"].apply(_format_dt)

    st.dataframe(
        df[["Membro", "Papel", "Acessos", "Último acesso"]],
        hide_index=True,
        use_container_width=True,
    )


def _render_timeseries(rows: list[dict]) -> None:
    """Série temporal: membros x visitantes por dia."""
    st.markdown("##### 📈 Acessos ao longo do tempo")

    fig = go.Figure()
    layout = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": "#B0B0B0", "size": 12},
        "margin": {"l": 40, "r": 20, "t": 20, "b": 40},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom", "y": 1.02,
            "xanchor": "right", "x": 1,
            "font": {"size": 11},
        },
        "xaxis": {"showgrid": False, "fixedrange": True},
        "yaxis": {
            "gridcolor": "rgba(255,255,255,0.08)",
            "tickformat": "d",
            "fixedrange": True,
            "rangemode": "tozero",
        },
        "dragmode": False,
        "hovermode": "x unified",
        "height": 320,
    }

    if not rows:
        fig.add_annotation(
            text="Sem acessos no período",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font={"size": 15, "color": "#B0B0B0"},
        )
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        return

    df = pd.DataFrame(rows)
    dias = [d.strftime("%d/%m") if hasattr(d, "strftime") else str(d) for d in df["dia"]]

    fig.add_trace(go.Bar(
        name="Membros",
        x=dias, y=df["logins"].astype(int),
        marker_color=Colors.NEUTRAL, marker_line_width=0,
        hovertemplate="Membros: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Visitantes",
        x=dias, y=df["visitors"].astype(int),
        marker_color=Colors.YIELD, marker_line_width=0,
        hovertemplate="Visitantes: %{y}<extra></extra>",
    ))
    layout["barmode"] = "stack"
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_recent(rows: list[dict]) -> None:
    """Tabela dos últimos acessos."""
    st.markdown("##### 🕑 Últimos acessos")

    if not rows:
        st.info("Nenhum acesso registrado ainda.")
        return

    df = pd.DataFrame(rows)
    df["Quando"] = df["created_at"].apply(_format_dt)
    df["Tipo"] = df["event_type"].map({"login": "👤 Membro", "visitor": "👀 Visitante"})
    df["Membro"] = df["user_email"].fillna("—")
    df["Papel"] = df["role"].fillna("—")

    st.dataframe(
        df[["Quando", "Tipo", "Membro", "Papel"]],
        hide_index=True,
        use_container_width=True,
    )


def _format_dt(dt: datetime | str | None) -> str:
    """Formata datetime para exibição (horário de Brasília)."""
    if dt is None:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    return to_brasilia(dt).strftime("%d/%m/%Y %H:%M")
