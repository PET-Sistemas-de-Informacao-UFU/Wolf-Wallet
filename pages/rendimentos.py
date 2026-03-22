"""
🐺 Wolf Wallet — Rendimentos (CDI Yields Page)

Página detalhada de rendimentos com:
    - Card de rendimento líquido acumulado
    - Breakdown mensal: bruto / imposto / líquido
    - Gráfico de linha com 3 séries (bruto, imposto, líquido)
    - Tabela de histórico mensal

Usage:
    from pages.rendimentos import render_rendimentos
"""

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go
import streamlit as st

from auth.session import is_visitor, render_visitor_banner, require_auth
from components.hide_balance import mask_value
from config.settings import Colors, Messages
from services.report_service import format_currency


def render_rendimentos() -> None:
    """Renderiza a página de rendimentos."""
    if not require_auth():
        return

    st.title("📈 Rendimentos CDI")
    st.caption(
        "Acompanhe os rendimentos diários do saldo em conta Mercado Pago. "
        "O CDI é creditado automaticamente e o imposto retido na fonte."
    )

    if is_visitor():
        _render_visitor()
    else:
        _render_real()


def _render_real() -> None:
    """Rendimentos com dados reais do banco."""
    from models.transaction import (
        get_monthly_yield_breakdown,
        get_yield_history,
    )

    today = date.today()
    hidden = False

    try:
        from auth.session import is_balance_hidden
        hidden = is_balance_hidden()
    except Exception:
        pass

    # Breakdown do mês atual
    current = get_monthly_yield_breakdown(today.year, today.month)

    # Histórico completo
    history_df = get_yield_history(months=24)

    # --- Cards do mês atual ---
    _render_yield_cards(current, hidden)

    st.divider()

    # --- Gráfico + Tabela ---
    if not history_df.empty:
        # Filtro de meses
        filtered_df = _render_month_filter(history_df)

        st.markdown("##### 📊 Evolução Mensal")
        fig = _yield_chart(filtered_df)
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # --- Tabela de histórico ---
        st.markdown("##### 📋 Histórico Detalhado")
        _render_yield_table(filtered_df, hidden)
    else:
        st.info(Messages.NO_DATA)


def _render_visitor() -> None:
    """Rendimentos com dados mock."""
    render_visitor_banner()

    from mock.mock_data import get_mock_dashboard_data

    mock = get_mock_dashboard_data()
    transactions = mock.get("transactions", [])

    # Simula breakdown a partir dos mock
    from config.settings import Finance
    threshold = float(Finance.YIELD_THRESHOLD)

    gross = sum(
        float(t["transaction_amount"])
        for t in transactions
        if t.get("transaction_type") == "SETTLEMENT"
        and not t.get("payment_method")
        and float(t.get("transaction_amount", 0)) > 0
        and abs(float(t.get("transaction_amount", 0))) < threshold
    )
    tax = sum(
        float(t["transaction_amount"])
        for t in transactions
        if t.get("transaction_type") == "SETTLEMENT"
        and not t.get("payment_method")
        and float(t.get("transaction_amount", 0)) < 0
        and abs(float(t.get("transaction_amount", 0))) < threshold
    )

    current = {"gross": gross, "tax": tax, "net": gross + tax}

    hidden = False
    try:
        from auth.session import is_balance_hidden
        hidden = is_balance_hidden()
    except Exception:
        pass

    _render_yield_cards(current, hidden)

    st.divider()
    st.info("📊 Gráfico de evolução disponível com dados reais (faça login).")


def _render_yield_cards(data: dict, hidden: bool = False) -> None:
    """Renderiza os 3 cards de rendimento: bruto, imposto, líquido."""
    gross = float(data.get("gross", 0))
    tax = float(data.get("tax", 0))
    net = float(data.get("net", 0))

    # Taxa efetiva de imposto
    tax_rate = (abs(tax) / gross * 100) if gross > 0 else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            _card_html(
                "Rendimento Bruto",
                mask_value(format_currency(gross)) if hidden else format_currency(gross),
                "💰",
                Colors.POSITIVE,
            ),
            unsafe_allow_html=True,
        )

    with col2:
        tax_label = f"Imposto ({tax_rate:.1f}%)" if tax_rate > 0 else "Imposto"
        st.markdown(
            _card_html(
                tax_label,
                mask_value(format_currency(abs(tax))) if hidden else format_currency(abs(tax)),
                "🏛️",
                Colors.NEGATIVE,
            ),
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            _card_html(
                "Rendimento Líquido",
                mask_value(format_currency(net)) if hidden else format_currency(net),
                "📈",
                Colors.YIELD,
            ),
            unsafe_allow_html=True,
        )

    st.caption(f"📅 Mês atual: {date.today().strftime('%B %Y').capitalize()}")


def _card_html(title: str, value: str, icon: str, color: str) -> str:
    """Gera HTML de um card de rendimento."""
    return f"""
    <div style="
        background: linear-gradient(135deg, #1E1E2E 0%, #252540 100%);
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        border-left: 4px solid {color};
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    ">
        <div style="font-size: 1.4rem; margin-bottom: 0.3rem;">{icon}</div>
        <p style="font-size: 0.85rem; color: #B0B0B0; margin: 0;">{title}</p>
        <p style="font-size: 1.5rem; font-weight: 700; margin: 0.3rem 0 0 0; color: {color};">{value}</p>
    </div>
    """


def _render_month_filter(df) -> "pd.DataFrame":
    """Filtro de meses acima do gráfico. Retorna DataFrame filtrado."""
    # Gera labels legíveis para cada mês
    month_map: dict[str, str] = {}  # label -> YYYY-MM
    for m in df["month"].tolist():
        parts = str(m).split("-")
        if len(parts) == 2:
            label = f"{parts[1]}/{parts[0]}"
        else:
            label = str(m)
        month_map[label] = str(m)

    all_labels = list(month_map.keys())

    selected = st.multiselect(
        "📅 Filtrar por mês",
        options=all_labels,
        default=all_labels,
        key="rendimentos_month_filter",
        help="Selecione os meses que deseja visualizar no gráfico e na tabela.",
    )

    if not selected:
        # Se nenhum selecionado, mostra todos
        return df

    selected_months = [month_map[label] for label in selected]
    return df[df["month"].astype(str).isin(selected_months)].reset_index(drop=True)


def _yield_chart(df) -> go.Figure:
    """Gráfico de linha com 3 séries: bruto, imposto, líquido."""
    fig = go.Figure()

    # Formata labels
    months = df["month"].tolist()
    labels = []
    for m in months:
        parts = str(m).split("-")
        if len(parts) == 2:
            labels.append(f"{parts[1]}/{parts[0]}")
        else:
            labels.append(str(m))

    # Bruto
    fig.add_trace(go.Scatter(
        name="💰 Rendimento Bruto",
        x=labels,
        y=df["gross"].astype(float),
        mode="lines+markers",
        line={"color": Colors.POSITIVE, "width": 2, "dash": "dot"},
        marker={"size": 7},
        hovertemplate="R$ %{y:,.2f}<extra></extra>",
    ))

    # Imposto (como valor positivo para visualização)
    fig.add_trace(go.Scatter(
        name="🏛️ Imposto",
        x=labels,
        y=df["tax"].astype(float),
        mode="lines+markers",
        line={"color": Colors.NEGATIVE, "width": 2, "dash": "dot"},
        marker={"size": 7},
        hovertemplate="R$ %{y:,.2f}<extra></extra>",
    ))

    # Líquido (destaque)
    fig.add_trace(go.Scatter(
        name="📈 Rendimento Líquido",
        x=labels,
        y=df["net_yield"].astype(float),
        mode="lines+markers",
        line={"color": Colors.YIELD, "width": 3},
        marker={"size": 9, "color": Colors.YIELD, "line": {"width": 1, "color": "#FFF"}},
        fill="tozeroy",
        fillcolor="rgba(255, 214, 0, 0.08)",
        hovertemplate="R$ %{y:,.2f}<extra></extra>",
    ))

    fig.update_layout(
        title={"text": "Rendimentos CDI — Evolução Mensal", "font": {"size": 16, "color": "#FAFAFA"}},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#B0B0B0", "size": 12},
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 13},
        },
        xaxis={
            "gridcolor": "rgba(255,255,255,0.05)",
            "showgrid": False,
            "showspikes": True,
            "spikecolor": "rgba(255,255,255,0.15)",
            "spikethickness": 1,
            "spikedash": "dot",
            "spikemode": "across",
        },
        yaxis={
            "gridcolor": "rgba(255,255,255,0.08)",
            "tickprefix": "R$ ",
            "tickformat": ",.2f",
            "showspikes": True,
            "spikecolor": "rgba(255,255,255,0.15)",
            "spikethickness": 1,
            "spikedash": "dot",
        },
        hovermode="x unified",
        hoverlabel={
            "bgcolor": "#1E1E2E",
            "bordercolor": "rgba(255,255,255,0.1)",
            "font": {"size": 13, "color": "#FAFAFA"},
            "namelength": -1,
        },
    )

    return fig


def _render_yield_table(df, hidden: bool = False) -> None:
    """Tabela de histórico de rendimentos por mês."""
    # Header
    cols = st.columns([1.5, 1.5, 1.5, 1.5, 1])
    headers = ["Mês", "Bruto", "Imposto", "Líquido", "Taxa"]
    for col, header in zip(cols, headers):
        with col:
            st.markdown(f"**{header}**")

    st.divider()

    # Rows (mais recente primeiro)
    for _, row in df.iloc[::-1].iterrows():
        month_str = row["month"]
        parts = str(month_str).split("-")
        label = f"{parts[1]}/{parts[0]}" if len(parts) == 2 else str(month_str)

        gross = float(row["gross"])
        tax = float(row["tax"])
        net = float(row["net_yield"])
        rate = (tax / gross * 100) if gross > 0 else 0

        cols = st.columns([1.5, 1.5, 1.5, 1.5, 1])

        with cols[0]:
            st.markdown(f"📅 **{label}**")

        with cols[1]:
            val = mask_value(format_currency(gross)) if hidden else format_currency(gross)
            st.markdown(f"<span style='color: {Colors.POSITIVE}'>{val}</span>", unsafe_allow_html=True)

        with cols[2]:
            val = mask_value(format_currency(tax)) if hidden else format_currency(tax)
            st.markdown(f"<span style='color: {Colors.NEGATIVE}'>{val}</span>", unsafe_allow_html=True)

        with cols[3]:
            val = mask_value(format_currency(net)) if hidden else format_currency(net)
            st.markdown(f"<span style='color: {Colors.YIELD}; font-weight: bold'>{val}</span>", unsafe_allow_html=True)

        with cols[4]:
            st.markdown(f"`{rate:.1f}%`")

    # Totais
    st.divider()
    total_gross = df["gross"].astype(float).sum()
    total_tax = df["tax"].astype(float).sum()
    total_net = df["net_yield"].astype(float).sum()
    total_rate = (total_tax / total_gross * 100) if total_gross > 0 else 0

    cols = st.columns([1.5, 1.5, 1.5, 1.5, 1])
    with cols[0]:
        st.markdown("**🔢 TOTAL**")
    with cols[1]:
        val = mask_value(format_currency(total_gross)) if hidden else format_currency(total_gross)
        st.markdown(f"**{val}**")
    with cols[2]:
        val = mask_value(format_currency(total_tax)) if hidden else format_currency(total_tax)
        st.markdown(f"**{val}**")
    with cols[3]:
        val = mask_value(format_currency(total_net)) if hidden else format_currency(total_net)
        st.markdown(f"<span style='color: {Colors.YIELD}; font-weight: bold'>{val}</span>", unsafe_allow_html=True)
    with cols[4]:
        st.markdown(f"**`{total_rate:.1f}%`**")
