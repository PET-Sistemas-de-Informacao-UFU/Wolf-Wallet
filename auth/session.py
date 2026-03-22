"""
🐺 Wolf Wallet — Session Management

Gerencia o estado da sessão do usuário no Streamlit.
Centraliza login, logout, guards de autenticação e helpers de estado.

Usage:
    from auth.session import init_session_state, login_user, is_authenticated, require_auth
"""

from __future__ import annotations

import streamlit as st

from config.settings import Messages, Pages, SessionKeys


# =============================================
# Initialization
# =============================================

def init_session_state() -> None:
    """
    Inicializa todas as chaves do session_state com valores padrão.

    Deve ser chamada UMA VEZ no início de cada execução do app.
    Se a chave já existe, não sobrescreve (preserva estado entre reruns).
    """
    defaults: dict = {
        SessionKeys.AUTHENTICATED: False,
        SessionKeys.USER: None,
        SessionKeys.ROLE: None,
        SessionKeys.IS_VISITOR: False,
        SessionKeys.HIDE_BALANCE: False,
        SessionKeys.CURRENT_PAGE: Pages.LOGIN,
        SessionKeys.THEME: "dark",
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


# =============================================
# Login / Logout
# =============================================

def login_user(user: dict) -> None:
    """
    Registra o login de um usuário na sessão.

    Args:
        user: Dicionário com dados do usuário (id, name, email, role).
    """
    st.session_state[SessionKeys.AUTHENTICATED] = True
    st.session_state[SessionKeys.IS_VISITOR] = False
    st.session_state[SessionKeys.USER] = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }
    st.session_state[SessionKeys.ROLE] = user["role"]
    st.session_state[SessionKeys.CURRENT_PAGE] = Pages.HOME


def login_visitor() -> None:
    """Registra o acesso como visitante (modo demo)."""
    st.session_state[SessionKeys.AUTHENTICATED] = False
    st.session_state[SessionKeys.IS_VISITOR] = True
    st.session_state[SessionKeys.USER] = None
    st.session_state[SessionKeys.ROLE] = None
    st.session_state[SessionKeys.CURRENT_PAGE] = Pages.HOME


def logout_user() -> None:
    """
    Limpa a sessão e reseta para o estado inicial.

    Preserva apenas o tema escolhido pelo usuário.
    """
    current_theme = st.session_state.get(SessionKeys.THEME, "dark")

    keys_to_clear = [
        SessionKeys.AUTHENTICATED,
        SessionKeys.USER,
        SessionKeys.ROLE,
        SessionKeys.IS_VISITOR,
        SessionKeys.HIDE_BALANCE,
        SessionKeys.CURRENT_PAGE,
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # Reinicializa com defaults
    init_session_state()
    st.session_state[SessionKeys.THEME] = current_theme


# =============================================
# State Getters
# =============================================

def is_authenticated() -> bool:
    """Retorna True se o usuário está logado (não visitante)."""
    return st.session_state.get(SessionKeys.AUTHENTICATED, False)


def is_admin() -> bool:
    """Retorna True se o usuário logado é admin."""
    return (
        is_authenticated()
        and st.session_state.get(SessionKeys.ROLE) == "admin"
    )


def is_visitor() -> bool:
    """Retorna True se está no modo visitante."""
    return st.session_state.get(SessionKeys.IS_VISITOR, False)


def is_balance_hidden() -> bool:
    """Retorna True se o saldo está oculto."""
    return st.session_state.get(SessionKeys.HIDE_BALANCE, False)


def get_current_user() -> dict | None:
    """
    Retorna os dados do usuário logado.

    Returns:
        Dicionário com id, name, email, role. Ou None se não logado.
    """
    return st.session_state.get(SessionKeys.USER)


def get_current_page() -> str:
    """Retorna o identificador da página atual."""
    return st.session_state.get(SessionKeys.CURRENT_PAGE, Pages.LOGIN)


def set_current_page(page: str) -> None:
    """Define a página atual."""
    st.session_state[SessionKeys.CURRENT_PAGE] = page


def toggle_hide_balance() -> None:
    """Alterna a visibilidade do saldo."""
    current = st.session_state.get(SessionKeys.HIDE_BALANCE, False)
    st.session_state[SessionKeys.HIDE_BALANCE] = not current


# =============================================
# Route Guards
# =============================================

def require_auth() -> bool:
    """
    Guard: verifica se o usuário está autenticado OU é visitante.

    Se não estiver, redireciona para o login.

    Returns:
        True se pode acessar a página. False se foi redirecionado.
    """
    if is_authenticated() or is_visitor():
        return True

    st.session_state[SessionKeys.CURRENT_PAGE] = Pages.LOGIN
    st.warning("🔒 Você precisa fazer login para acessar esta página.")
    return False


def require_admin() -> bool:
    """
    Guard: verifica se o usuário logado é admin.

    Se não for, exibe mensagem de acesso negado.

    Returns:
        True se é admin. False caso contrário.
    """
    if not is_authenticated():
        st.session_state[SessionKeys.CURRENT_PAGE] = Pages.LOGIN
        st.warning("🔒 Você precisa fazer login para acessar esta página.")
        return False

    if not is_admin():
        st.error("🚫 Acesso restrito. Apenas administradores podem acessar esta página.")
        return False

    return True


def render_visitor_banner() -> None:
    """Exibe o banner de modo visitante se aplicável."""
    if is_visitor():
        st.warning(Messages.VISITOR_BANNER)
