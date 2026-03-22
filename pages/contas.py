"""
🐺 Wolf Wallet — Contas Mensais

Página de gestão de contas recorrentes com:
    - Lista de contas com status de vencimento
    - Cadastro/edição (admin)
    - Histórico de pagamentos
    - Alertas de vencimento

Usage:
    from pages.contas import render_contas
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from auth.session import (
    is_admin,
    is_balance_hidden,
    is_visitor,
    render_visitor_banner,
    require_auth,
)
from components.hide_balance import mask_value
from config.settings import Colors, Messages
from services.report_service import format_currency


def render_contas() -> None:
    """Renderiza a página de contas mensais."""
    if not require_auth():
        return

    st.title("💳 Contas Mensais")
    st.caption(
        "Controle das despesas recorrentes do projeto. "
        "Acompanhe vencimentos e mantenha as contas em dia."
    )

    if is_visitor():
        _render_visitor()
    else:
        _render_real()


def _render_real() -> None:
    """Contas com dados reais do banco."""
    from models.bill import get_all_bills, get_active_bills

    hidden = is_balance_hidden()

    try:
        bills = get_all_bills() if is_admin() else get_active_bills()
    except Exception as e:
        st.warning(f"⚠️ Erro ao carregar contas: {e}")
        bills = []

    if not bills:
        st.info("Nenhuma conta cadastrada.")
        if is_admin():
            st.caption("Use o formulário abaixo para adicionar a primeira conta.")
            st.divider()
            _render_admin_form()
        return

    # Cards resumo
    _render_bill_summary(bills, hidden)

    st.divider()

    # Lista de contas
    _render_bill_list(bills, hidden)

    # Admin: ações de gerenciamento
    if is_admin():
        _render_admin_actions(bills)
        st.divider()
        _render_admin_form()


def _render_visitor() -> None:
    """Contas com dados mock para visitantes."""
    render_visitor_banner()

    from mock.mock_data import get_mock_bills

    bills = get_mock_bills()
    hidden = is_balance_hidden()

    _render_bill_summary(bills, hidden)

    st.divider()

    _render_bill_list(bills, hidden)

    # Mostra formulário admin como preview (desabilitado)
    st.divider()
    _render_admin_form_preview()


def _render_bill_summary(bills: list[dict], hidden: bool) -> None:
    """Cards de resumo: total mensal, próximo vencimento, contas ativas."""
    today = date.today()

    total_monthly = sum(float(b.get("amount", 0)) for b in bills)
    active_count = len(bills)

    # Próximo vencimento
    upcoming = []
    for b in bills:
        due = b.get("due_day", 0)
        try:
            due_date = today.replace(day=due)
            if due_date < today:
                if today.month == 12:
                    due_date = due_date.replace(year=today.year + 1, month=1)
                else:
                    due_date = due_date.replace(month=today.month + 1)
            days = (due_date - today).days
            upcoming.append((b, days))
        except ValueError:
            pass

    upcoming.sort(key=lambda x: x[1])
    next_bill = upcoming[0] if upcoming else None

    col1, col2, col3 = st.columns(3)

    with col1:
        val = mask_value(format_currency(total_monthly)) if hidden else format_currency(total_monthly)
        st.markdown(
            _summary_card("Total Mensal", val, "💰", Colors.NEUTRAL),
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            _summary_card("Contas Ativas", str(active_count), "📋", Colors.POSITIVE),
            unsafe_allow_html=True,
        )

    with col3:
        if next_bill:
            bill, days = next_bill
            if days == 0:
                label = f"{bill['name']} — vence hoje!"
                color = Colors.NEGATIVE
            elif days <= 3:
                label = f"{bill['name']} — {days} dia(s)"
                color = Colors.ALERT
            else:
                label = f"{bill['name']} — {days} dias"
                color = Colors.POSITIVE
        else:
            label = "—"
            color = Colors.NEUTRAL

        st.markdown(
            _summary_card("Próximo Vencimento", label, "📅", color),
            unsafe_allow_html=True,
        )


def _summary_card(title: str, value: str, icon: str, color: str) -> str:
    """HTML de um card de resumo."""
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
        <p style="font-size: 1.3rem; font-weight: 700; margin: 0.3rem 0 0 0; color: {color};">{value}</p>
    </div>
    """


def _render_bill_list(bills: list[dict], hidden: bool) -> None:
    """Renderiza a lista de contas com status de vencimento."""
    st.markdown("##### 📋 Contas Cadastradas")

    today = date.today()

    for bill in bills:
        name = bill.get("name", "Conta")
        description = bill.get("description", "")
        amount = float(bill.get("amount", 0))
        due_day = bill.get("due_day", 0)
        recurrence = bill.get("recurrence", "monthly")

        # Calcula dias até vencimento
        try:
            due_date = today.replace(day=due_day)
            if due_date < today:
                if today.month == 12:
                    due_date = due_date.replace(year=today.year + 1, month=1)
                else:
                    due_date = due_date.replace(month=today.month + 1)
            days_until = (due_date - today).days
        except ValueError:
            days_until = 99

        # Status visual
        if days_until == 0:
            status_icon = "🔴"
            status_text = "Vence hoje!"
            status_color = Colors.NEGATIVE
        elif days_until <= 3:
            status_icon = "🟡"
            status_text = f"Vence em {days_until} dia(s)"
            status_color = Colors.ALERT
        elif days_until <= 7:
            status_icon = "🟢"
            status_text = f"Vence em {days_until} dias"
            status_color = Colors.POSITIVE
        else:
            status_icon = "⚪"
            status_text = f"Dia {due_day} ({days_until} dias)"
            status_color = "#888"

        amount_display = mask_value(format_currency(amount)) if hidden else format_currency(amount)

        recurrence_label = "🔄 Mensal" if recurrence == "monthly" else "📌 Temporário"

        st.markdown(
            f"""
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.8rem 1rem;
                margin: 0.4rem 0;
                border-radius: 10px;
                background: rgba(255,255,255,0.03);
                border-left: 3px solid {status_color};
            ">
                <div>
                    <span style="font-size: 1rem; font-weight: 600;">{name}</span>
                    <span style="color: #888; font-size: 0.8rem; margin-left: 0.5rem;">{recurrence_label}</span>
                    <br>
                    <span style="color: #888; font-size: 0.82rem;">{description}</span>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 1.1rem; font-weight: 700; color: {Colors.NEUTRAL};">{amount_display}</span>
                    <br>
                    <span style="font-size: 0.82rem; color: {status_color};">{status_icon} {status_text}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_admin_actions(bills: list[dict]) -> None:
    """Ações de admin: desativar contas."""
    st.divider()
    st.markdown("##### ⚙️ Gerenciar Contas")

    active_bills = [b for b in bills if b.get("is_active", True)]
    if not active_bills:
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        bill_options = {f"{b['name']} (dia {b['due_day']})": b["id"] for b in active_bills}
        selected = st.selectbox(
            "Selecionar conta",
            options=list(bill_options.keys()),
            key="admin_bill_select",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Desativar", key="deactivate_bill", type="secondary"):
            if selected:
                try:
                    from models.bill import deactivate_bill
                    bill_id = bill_options[selected]
                    if deactivate_bill(bill_id):
                        st.success(f"✅ Conta desativada!")
                        st.rerun()
                    else:
                        st.warning("Conta já estava desativada.")
                except Exception as e:
                    st.error(f"Erro: {e}")


def _render_admin_form() -> None:
    """Formulário de cadastro de nova conta (admin)."""
    st.markdown("##### ➕ Cadastrar Nova Conta")

    with st.form("new_bill_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Nome da conta *", placeholder="Ex: Servidor Cloud")
            amount = st.number_input("Valor (R$) *", min_value=0.01, step=0.01, format="%.2f")

        with col2:
            due_day = st.number_input("Dia de vencimento *", min_value=1, max_value=31, value=10)
            recurrence = st.selectbox("Recorrência", ["monthly", "temporary"])

        description = st.text_input("Descrição (opcional)", placeholder="Detalhes da conta")

        submitted = st.form_submit_button("💾 Cadastrar Conta", type="primary")

        if submitted:
            if not name:
                st.error("Nome é obrigatório.")
                return

            try:
                from auth.session import get_current_user
                from models.bill import create_bill

                user = get_current_user()
                user_id = user["id"] if user else 1

                result = create_bill(
                    name=name,
                    amount=amount,
                    due_day=due_day,
                    start_date=date.today(),
                    created_by=user_id,
                    recurrence=recurrence,
                    description=description or None,
                )
                st.success(f"✅ Conta '{name}' cadastrada!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")


def _render_admin_form_preview() -> None:
    """Preview do formulário admin para visitantes (desabilitado)."""
    st.markdown("##### ➕ Cadastrar Nova Conta")
    st.caption("🔒 Área exclusiva para administradores")

    with st.form("preview_bill_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.text_input("Nome da conta *", value="Servidor Cloud", disabled=True)
            st.number_input("Valor (R$) *", value=49.90, disabled=True)

        with col2:
            st.number_input("Dia de vencimento *", value=10, disabled=True)
            st.selectbox("Recorrência", ["monthly", "temporary"], disabled=True)

        st.text_input("Descrição (opcional)", value="Hospedagem do site", disabled=True)

        st.form_submit_button("💾 Cadastrar Conta", disabled=True)
