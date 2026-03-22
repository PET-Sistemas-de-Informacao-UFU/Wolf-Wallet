"""
🐺 Wolf Wallet — Login Page

Tela de login com:
    - Formulário de email/senha
    - Botão "Entrar como Visitante"
    - Link "Esqueci minha senha" (placeholder para Fase 8)
    - Branding do projeto

Usage:
    from auth.login import render_login
"""

from __future__ import annotations

import time

import streamlit as st

from auth.password import hash_password, verify_password
from auth.session import login_user, login_visitor
from config.settings import App, Auth, Messages


def render_login() -> None:
    """Renderiza a tela de login completa."""
    # Esconde o sidebar no login
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] { display: none; }
            [data-testid="stSidebarCollapsedControl"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Layout centralizado
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        _render_header()
        st.divider()
        _render_login_form()
        st.divider()
        _render_visitor_button()


def _render_header() -> None:
    """Renderiza o cabeçalho com branding do projeto."""
    st.markdown(
        f"""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="margin-bottom: 0.2rem;">{App.TITLE}</h1>
            <p style="color: gray; font-size: 1.05rem;">
                {App.DESCRIPTION}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_login_form() -> None:
    """Renderiza o formulário de login com email e senha."""
    with st.form("login_form", clear_on_submit=False):
        st.markdown("##### 🔐 Entrar na sua conta")

        email = st.text_input(
            "Email",
            placeholder="seu.email@ufu.br",
            key="login_email",
        )

        password = st.text_input(
            "Senha",
            type="password",
            placeholder="Digite sua senha",
            key="login_password",
        )

        col_submit, col_forgot = st.columns([2, 1])

        with col_submit:
            submitted = st.form_submit_button(
                "🔐 Entrar",
                use_container_width=True,
                type="primary",
            )

        with col_forgot:
            forgot = st.form_submit_button(
                "Esqueci minha senha",
                use_container_width=True,
            )

    # Processa login
    if submitted:
        _handle_login(email, password)

    # Esqueci minha senha
    if forgot:
        _handle_forgot_password(email)


def _handle_login(email: str, password: str) -> None:
    """
    Processa a tentativa de login.

    Args:
        email: Email digitado.
        password: Senha digitada.
    """
    if not email or not password:
        st.error("Preencha o email e a senha.")
        return

    email = email.strip().lower()

    try:
        from models.user import get_user_by_email

        user = get_user_by_email(email)

        if not user:
            time.sleep(Auth.FAILED_LOGIN_DELAY)
            st.error(Messages.LOGIN_FAILED)
            return

        if not user["is_active"]:
            time.sleep(Auth.FAILED_LOGIN_DELAY)
            st.error(Messages.LOGIN_INACTIVE)
            return

        if not verify_password(password, user["password_hash"]):
            time.sleep(Auth.FAILED_LOGIN_DELAY)
            st.error(Messages.LOGIN_FAILED)
            return

        # Login bem-sucedido
        login_user(user)
        st.success(Messages.LOGIN_SUCCESS)
        time.sleep(0.5)
        st.rerun()

    except Exception as e:
        st.error(
            "⚠️ Não foi possível conectar ao banco de dados. "
            "Use o modo visitante ou entre em contato com um administrador."
        )


def _handle_forgot_password(email: str) -> None:
    """
    Placeholder para o fluxo de redefinição de senha.
    Será implementado completamente na Fase 8 (com envio de email).

    Args:
        email: Email digitado no formulário.
    """
    if not email:
        st.warning("Digite seu email no campo acima e clique em 'Esqueci minha senha'.")
        return

    st.info(
        f"📧 Se o email **{email}** estiver cadastrado, "
        "você receberá um link de redefinição.\n\n"
        "*(Funcionalidade completa será ativada em breve)*"
    )


def _render_visitor_button() -> None:
    """Renderiza o botão de acesso como visitante."""
    st.markdown(
        "<p style='text-align: center; color: gray; font-size: 0.9rem;'>"
        "Não tem conta? Explore o sistema com dados de demonstração."
        "</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("👀 Entrar como Visitante", use_container_width=True):
            login_visitor()
            st.rerun()

    st.markdown(
        f"<p style='text-align: center; color: gray; font-size: 0.75rem; margin-top: 2rem;'>"
        f"v{App.VERSION} • {App.AUTHOR}"
        f"</p>",
        unsafe_allow_html=True,
    )
