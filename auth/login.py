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
        <div style="text-align: center; padding: 2rem 0 1rem 0;">
            <h1 style="margin: 0; font-size: 2.2rem; letter-spacing: -0.5px;">🐺 {App.NAME} 💰</h1>
            <h4 style="color: #888; font-weight: 400; margin-top: 0.6rem;">Carteira virtual do PET-SI — UFU</h4>
            <p style="color: #666; font-size: 0.85rem; margin-top: 0.8rem; line-height: 1.5;">
                Visualize as movimentações financeiras da conta<br>
                compartilhada de forma transparente e automatizada.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_login_form() -> None:
    """Renderiza o formulário de login com email e senha."""
    with st.form("login_form", clear_on_submit=False):
        st.markdown("##### 🔐 Acesse sua conta")

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
                width="stretch",
                type="primary",
            )

        with col_forgot:
            forgot = st.form_submit_button(
                "Esqueci minha senha",
                width="stretch",
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
    Fluxo de redefinição de senha: gera senha temporária e envia por email.

    Args:
        email: Email digitado no formulário.
    """
    if not email:
        st.warning("Digite seu email no campo acima e clique em 'Esqueci minha senha'.")
        return

    email = email.strip().lower()

    try:
        from models.user import get_user_by_email, update_user
        from auth.password import generate_temp_password, hash_password
        from services.email_service import send_password_reset_email, is_email_configured

        user = get_user_by_email(email)

        if not user or not user.get("is_active"):
            # Mensagem genérica por segurança (não revela se email existe)
            time.sleep(Auth.FAILED_LOGIN_DELAY)
            st.info(
                f"📧 Se o email **{email}** estiver cadastrado, "
                "uma nova senha será enviada."
            )
            return

        temp_password = generate_temp_password()
        update_user(user["id"], password_hash=hash_password(temp_password), must_change_password=True)

        if is_email_configured():
            sent = send_password_reset_email(user["name"], email, temp_password)
            if sent:
                st.success(
                    f"📧 Nova senha enviada para **{email}**. "
                    "Verifique sua caixa de entrada."
                )
            else:
                st.warning(
                    "⚠️ Senha redefinida mas o email não pôde ser enviado. "
                    "Contacte um administrador."
                )
        else:
            st.info(
                f"📧 Se o email **{email}** estiver cadastrado, "
                "uma nova senha será enviada."
            )

    except Exception:
        st.info(
            f"📧 Se o email **{email}** estiver cadastrado, "
            "uma nova senha será enviada."
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
        if st.button("👀 Entrar como Visitante", width="stretch"):
            login_visitor()
            st.rerun()

    st.markdown(
        f"<p style='text-align: center; color: gray; font-size: 0.75rem; margin-top: 2rem;'>"
        f"v{App.VERSION} • {App.AUTHOR}"
        f"</p>",
        unsafe_allow_html=True,
    )
