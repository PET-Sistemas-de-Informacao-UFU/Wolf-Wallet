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
    render_visitor_banner,
    require_auth,
    require_admin,
)
from components.sidebar import render_sidebar
from config.settings import App, Pages, UI
from pages.admin_sync import render_admin_sync
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
    # Fases futuras adicionarão as páginas aqui:
    # Pages.ADMIN_USUARIOS: render_admin_usuarios,
}


def _route() -> None:
    """
    Determina e renderiza a página correta.

    Se não autenticado e não visitante → login.
    Se autenticado ou visitante → sidebar + página selecionada.
    """
    if not is_authenticated() and not is_visitor():
        render_login()
        return

    # Renderiza sidebar e obtém a página selecionada
    selected_page = render_sidebar()

    # Renderiza a página correspondente
    renderer = PAGE_RENDERERS.get(selected_page)
    if renderer:
        renderer()
    else:
        _render_coming_soon(selected_page)


# =============================================
# Main
# =============================================
def main() -> None:
    """Função principal — orquestra a inicialização e roteamento."""
    init_session_state()
    _route()


if __name__ == "__main__":
    main()
