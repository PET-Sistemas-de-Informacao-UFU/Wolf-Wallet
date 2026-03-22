"""
🐺 Wolf Wallet — Filter Components

Componentes reutilizáveis de filtro para páginas de listagem.
Usado no Extrato e Rendimentos.

Usage:
    from components.filters import render_transaction_filters
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st


def render_transaction_filters(key_prefix: str = "extrato") -> dict:
    """
    Renderiza filtros para transações e retorna os valores selecionados.

    Args:
        key_prefix: Prefixo para keys do session_state (evita colisão).

    Returns:
        Dict com: start_date, end_date, transaction_type, direction, search.
    """
    with st.expander("🔍 Filtros", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            start_date = st.date_input(
                "Data início",
                value=date.today() - timedelta(days=90),
                key=f"{key_prefix}_start_date",
            )

        with col2:
            end_date = st.date_input(
                "Data fim",
                value=date.today(),
                key=f"{key_prefix}_end_date",
            )

        with col3:
            direction = st.selectbox(
                "Direção",
                options=["Todas", "Entradas", "Saídas"],
                key=f"{key_prefix}_direction",
            )

        col4, col5, col6 = st.columns(3)

        with col4:
            transaction_type = st.selectbox(
                "Tipo de transação",
                options=["Todos", "SETTLEMENT", "REFUND", "PAYOUTS"],
                key=f"{key_prefix}_type",
            )

        with col5:
            payment_method = st.selectbox(
                "Método",
                options=["Todos", "pix", "account_money", "available_money", "(vazio)"],
                key=f"{key_prefix}_method",
            )

        with col6:
            search = st.text_input(
                "Buscar (source_id ou ref.)",
                value="",
                key=f"{key_prefix}_search",
                placeholder="Ex: 1274390661073",
            )

    # Mapeia para valores do model
    direction_map = {"Todas": None, "Entradas": "inflows", "Saídas": "outflows"}
    type_map = {"Todos": None}
    method_map = {"Todos": None, "(vazio)": ""}

    return {
        "start_date": start_date,
        "end_date": end_date,
        "transaction_type": type_map.get(transaction_type, transaction_type),
        "payment_method": method_map.get(payment_method, payment_method),
        "direction": direction_map.get(direction),
        "search": search.strip() or None,
    }


def render_pagination(total: int, per_page: int, key_prefix: str = "extrato") -> int:
    """
    Renderiza controles de paginação e retorna a página atual.

    Args:
        total: Total de registros.
        per_page: Itens por página.
        key_prefix: Prefixo para keys do session_state.

    Returns:
        Número da página atual (1-based).
    """
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Inicializa página no session_state
    page_key = f"{key_prefix}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    current_page = st.session_state[page_key]

    # Garante que a página está dentro do range
    current_page = max(1, min(current_page, total_pages))

    if total_pages <= 1:
        return 1

    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("◀ Anterior", key=f"{key_prefix}_prev", disabled=current_page <= 1):
            st.session_state[page_key] = current_page - 1
            st.rerun()

    with col_info:
        st.markdown(
            f"<div style='text-align: center; padding: 8px;'>"
            f"Página <strong>{current_page}</strong> de <strong>{total_pages}</strong>"
            f" ({total} registros)"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_next:
        if st.button("Próxima ▶", key=f"{key_prefix}_next", disabled=current_page >= total_pages):
            st.session_state[page_key] = current_page + 1
            st.rerun()

    return current_page
