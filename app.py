"""
🐺 Wolf Wallet — Entry Point

Ponto de entrada da aplicação Streamlit.
Responsável por:
    - Configuração da página (título, ícone, layout)
    - Inicialização do session_state
    - Roteamento entre páginas baseado na autenticação

Usage:
    streamlit run app.py
"""

import streamlit as st

from auth.login import render_login
from auth.session import (
    init_session_state,
    is_authenticated,
    is_visitor,
    get_current_page,
    get_current_user,
    render_visitor_banner,
    require_auth,
    require_admin,
)
from components.sidebar import render_sidebar
from components.mobile_css import inject_mobile_css
from config.settings import App, Pages, SessionKeys, UI
from pages.admin_sync import render_admin_sync
from pages.admin_usuarios import render_admin_usuarios
from pages.contas import render_contas
from pages.extrato import render_extrato
from pages.home import render_home
from pages.rendimentos import render_rendimentos


# =============================================
# Page Config (DEVE ser a primeira chamada Streamlit)
# =============================================
st.set_page_config(
    page_title=App.TITLE,
    page_icon=App.EMOJI,
    layout=UI.LAYOUT,
    initial_sidebar_state="expanded",
    menu_items={
        "About": f"### {App.TITLE} v{App.VERSION}\n{App.DESCRIPTION}",
    },
)

# CSS responsivo para mobile (deve vir logo após set_page_config)
inject_mobile_css()


# =============================================
# Page Renderers (placeholders para fases futuras)
# =============================================
def _render_coming_soon(page: str) -> None:
    """Placeholder genérico para páginas ainda não implementadas."""
    if page in Pages.ADMIN_PAGES:
        if not require_admin():
            return
    elif not require_auth():
        return

    st.title(f"🚧 {page.replace('_', ' ').title()}")
    st.info("Esta página será implementada em uma fase futura.")


# =============================================
# Router
# =============================================
PAGE_RENDERERS: dict = {
    Pages.HOME: render_home,
    Pages.EXTRATO: render_extrato,
    Pages.RENDIMENTOS: render_rendimentos,
    Pages.CONTAS: render_contas,
    Pages.ADMIN_SYNC: render_admin_sync,
    Pages.ADMIN_USUARIOS: render_admin_usuarios,
}


def _route() -> None:
    """
    Determina e renderiza a página correta.

    Se não autenticado e não visitante → login.
    Se must_change_password → tela obrigatória de troca.
    Se autenticado ou visitante → sidebar + página selecionada.
    """
    if not is_authenticated() and not is_visitor():
        render_login()
        return

    # Intercepta troca obrigatória de senha
    if st.session_state.get(SessionKeys.MUST_CHANGE_PASSWORD, False):
        _render_force_change_password()
        return

    # Renderiza sidebar e obtém a página selecionada
    selected_page = render_sidebar()

    # Renderiza a página correspondente
    renderer = PAGE_RENDERERS.get(selected_page)
    if renderer:
        renderer()
    else:
        _render_coming_soon(selected_page)


def _render_force_change_password() -> None:
    """Tela obrigatória de troca de senha (primeiro acesso ou após reset)."""
    # Esconde sidebar
    st.markdown(
        "<style>[data-testid='stSidebar']{display:none;}"
        "[data-testid='stSidebarCollapsedControl']{display:none;}</style>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"<div style='text-align:center;padding:1rem 0;'>"
            f"<span style='font-size:2.5rem;'>🔐</span>"
            f"<h2>Defina sua nova senha</h2>"
            f"<p style='color:#888;'>Sua senha precisa ser atualizada antes de continuar.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

        with st.form("force_change_pw"):
            new_pw = st.text_input("Nova senha", type="password")
            confirm_pw = st.text_input("Confirmar nova senha", type="password")
            submitted = st.form_submit_button("✅ Salvar nova senha", type="primary", width="stretch")

        if submitted:
            if not new_pw or not confirm_pw:
                st.error("Preencha ambos os campos.")
            elif new_pw != confirm_pw:
                st.error("As senhas não coincidem.")
            else:
                from auth.password import hash_password, validate_password_strength
                from models.user import update_user

                errors = validate_password_strength(new_pw)
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    user = get_current_user()
                    if user and update_user(user["id"], password_hash=hash_password(new_pw), must_change_password=False):
                        st.session_state[SessionKeys.MUST_CHANGE_PASSWORD] = False
                        st.success("✅ Senha atualizada! Redirecionando...")
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar senha.")


# =============================================
# Main
# =============================================
def main() -> None:
    """Função principal — orquestra a inicialização e roteamento."""
    init_session_state()

    # Sincronização automática D-1 (roda 1x por cold start)
    from services.auto_sync import start_auto_sync, ensure_sync_freshness
    start_auto_sync()

    # Verifica se os dados estão desatualizados (roda em cada page load)
    ensure_sync_freshness()

    _route()


if __name__ == "__main__":
    main()
