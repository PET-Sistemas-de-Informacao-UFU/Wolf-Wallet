"""
🐺 Wolf Wallet — Dashboard Cards Component

Cards estilizados para o dashboard com CSS customizado,
ícones, bordas coloridas e suporte a ocultação de saldo.

Usage:
    from components.cards import render_dashboard_cards
"""

from __future__ import annotations

import streamlit as st

from components.hide_balance import mask_value
from config.settings import Colors
from services.report_service import format_currency


def _card_css() -> str:
    """Retorna o CSS para estilizar os cards do dashboard."""
    return """
    <style>
    .wolf-card {
        background: linear-gradient(135deg, var(--card-bg) 0%, var(--card-bg-end) 100%);
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        border-left: 4px solid var(--card-color);
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 0.5rem;
    }
    .wolf-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    }
    .wolf-card-icon {
        font-size: 1.6rem;
        margin-bottom: 0.3rem;
    }
    .wolf-card-title {
        font-size: 0.85rem;
        color: #B0B0B0;
        margin: 0;
        font-weight: 500;
    }
    .wolf-card-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0.3rem 0 0 0;
        color: var(--card-color);
    }
    </style>
    """


def render_metric_card(
    title: str,
    value: str,
    icon: str,
    color: str,
    hidden: bool = False,
) -> None:
    """
    Renderiza um card de métrica estilizado.

    Args:
        title: Título do card (ex: "Saldo Atual").
        value: Valor formatado (ex: "R$ 1.234,56").
        icon: Emoji do ícone.
        color: Cor da borda e do valor (hex).
        hidden: Se True, exibe valor mascarado.
    """
    display_value = mask_value(value) if hidden else value

    st.markdown(
        f"""
        <div class="wolf-card" style="--card-color: {color}; --card-bg: #1E1E2E; --card-bg-end: #252540;">
            <div class="wolf-card-icon">{icon}</div>
            <p class="wolf-card-title">{title}</p>
            <p class="wolf-card-value" style="color: {color};">{display_value}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_cards(data: dict, hidden: bool = False) -> None:
    """
    Renderiza os 4 cards principais do dashboard.

    Args:
        data: Dict com keys: balance, inflows, outflows, yields.
        hidden: Se True, oculta todos os valores.
    """
    # Injeta CSS uma vez
    st.markdown(_card_css(), unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card(
            title="Saldo Atual",
            value=format_currency(data.get("balance", 0)),
            icon="💰",
            color=Colors.NEUTRAL,
            hidden=hidden,
        )

    with col2:
        render_metric_card(
            title="Entradas do Mês",
            value=format_currency(data.get("inflows", 0)),
            icon="📥",
            color=Colors.POSITIVE,
            hidden=hidden,
        )

    with col3:
        render_metric_card(
            title="Saídas do Mês",
            value=format_currency(abs(float(data.get("outflows", 0)))),
            icon="📤",
            color=Colors.NEGATIVE,
            hidden=hidden,
        )

    with col4:
        render_metric_card(
            title="Rendimento Líquido",
            value=format_currency(data.get("yields", 0)),
            icon="📈",
            color=Colors.YIELD,
            hidden=hidden,
        )
