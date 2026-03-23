"""
🐺 Wolf Wallet — Sidebar Navigation

Sidebar responsiva com:
    - Branding do projeto
    - Info do usuário logado
    - Navegação condicional por role
    - Toggle ocultar saldo
    - Botão de logout

Usage:
    from components.sidebar import render_sidebar
"""

from __future__ import annotations

import streamlit as st

from auth.session import (
    get_current_user,
    is_admin,
    is_visitor,
    logout_user,
    toggle_hide_balance,
    is_balance_hidden,
)
from config.settings import App, Pages, SessionKeys, UI


def render_sidebar() -> str:
    """
    Renderiza o sidebar completo e retorna a página selecionada.

    Returns:
        str: Identificador da página selecionada pelo usuário.
    """
    with st.sidebar:
        _render_brand()
        _render_user_info()
        st.divider()
        selected_page = _render_navigation()
        st.divider()
        _render_controls()
        _render_logout()

    return selected_page


def _render_brand() -> None:
    """Logo e título do app no topo do sidebar."""
    st.markdown(
        f"""
        <div style="text-align: center; padding: 0.5rem 0;">
            <h3 style="margin: 0; letter-spacing: -0.3px;">🐺 {App.NAME} 💰</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_user_info() -> None:
    """Exibe informações do usuário logado ou modo visitante."""
    user = get_current_user()

    if user:
        role_badge = "🔑 Admin" if user["role"] == "admin" else "👤 Membro"
        st.markdown(
            f"""
            <div style="text-align: center; padding: 0.3rem 0;">
                <p style="margin: 0; font-weight: bold;">{user['name']}</p>
                <p style="margin: 0; color: gray; font-size: 0.85rem;">
                    {role_badge} • {user['email']}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif is_visitor():
        st.markdown(
            """
            <div style="text-align: center; padding: 0.3rem 0;">
                <p style="margin: 0; font-weight: bold;">👀 Visitante</p>
                <p style="margin: 0; color: gray; font-size: 0.85rem;">
                    Modo demonstração
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_navigation() -> str:
    """
    Renderiza os links de navegação baseados no role do usuário.

    Returns:
        str: Identificador da página selecionada.
    """
    # Páginas acessíveis por todos (logados + visitantes)
    nav_items: dict[str, str] = {
        f"{UI.ICONS['dashboard']} Dashboard": Pages.HOME,
        f"{UI.ICONS['extrato']} Extrato": Pages.EXTRATO,
        f"{UI.ICONS['rendimentos']} Rendimentos": Pages.RENDIMENTOS,
        f"{UI.ICONS['contas']} Contas Mensais": Pages.CONTAS,
    }

    # Páginas admin
    if is_admin():
        nav_items.update({
            f"{UI.ICONS['admin_usuarios']} Usuários": Pages.ADMIN_USUARIOS,
            f"{UI.ICONS['admin_sync']} Sincronização": Pages.ADMIN_SYNC,
        })

    # Determina o index atual
    current_page = st.session_state.get(SessionKeys.CURRENT_PAGE, Pages.HOME)
    current_index = 0
    page_values = list(nav_items.values())
    if current_page in page_values:
        current_index = page_values.index(current_page)

    selected_label = st.radio(
        "Navegação",
        options=list(nav_items.keys()),
        index=current_index,
        label_visibility="collapsed",
    )

    selected_page = nav_items.get(selected_label, Pages.HOME)
    st.session_state[SessionKeys.CURRENT_PAGE] = selected_page

    return selected_page


def _render_controls() -> None:
    """Renderiza controles globais: ocultar saldo + alterar senha."""
    hidden = is_balance_hidden()
    icon = "👁️" if not hidden else "✕"
    label = "Mostrar saldo" if hidden else "Ocultar saldo"

    if st.button(f"{icon} {label}", use_container_width=True, key="toggle_balance"):
        toggle_hide_balance()
        st.rerun()

    # Alterar senha (somente para usuários logados, não visitantes)
    if not is_visitor() and get_current_user():
        _render_change_password()


def _render_change_password() -> None:
    """Formulário de alteração de senha no sidebar."""
    with st.expander("🔑 Alterar Senha", expanded=False):
        current_pw = st.text_input(
            "Senha atual", type="password", key="sidebar_current_pw"
        )
        new_pw = st.text_input(
            "Nova senha", type="password", key="sidebar_new_pw"
        )
        confirm_pw = st.text_input(
            "Confirmar nova senha", type="password", key="sidebar_confirm_pw"
        )

        if st.button("💾 Salvar", key="sidebar_save_pw", use_container_width=True):
            if not current_pw or not new_pw or not confirm_pw:
                st.error("Preencha todos os campos.")
                return

            if new_pw != confirm_pw:
                st.error("As senhas não coincidem.")
                return

            from auth.password import (
                hash_password,
                validate_password_strength,
                verify_password,
            )
            from models.user import get_user_by_id, update_user

            user = get_current_user()
            db_user = get_user_by_id(user["id"])

            if not db_user or not verify_password(current_pw, db_user["password_hash"]):
                st.error("Senha atual incorreta.")
                return

            errors = validate_password_strength(new_pw)
            if errors:
                for err in errors:
                    st.error(err)
                return

            if update_user(user["id"], password_hash=hash_password(new_pw)):
                st.success("✅ Senha alterada!")
            else:
                st.error("Erro ao salvar.")


def _render_logout() -> None:
    """Renderiza o botão de logout na parte inferior do sidebar."""
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🚪 Sair", use_container_width=True, key="logout_btn"):
        logout_user()
        st.rerun()
