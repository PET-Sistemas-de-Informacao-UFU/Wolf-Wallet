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
# Page Renderers
# =============================================
def _render_home() -> None:
    """Dashboard placeholder — será substituído na Fase 2."""
    if not require_auth():
        return

    render_visitor_banner()

    st.title(f"{App.EMOJI} Dashboard")

    user = st.session_state.get("user")
    if user:
        st.success(f"Logado como **{user['name']}** ({user['role']})")
    elif is_visitor():
        st.info("Modo visitante ativo")

    # Cards placeholder
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Saldo Atual", "R$ ••••••")
    with col2:
        st.metric("📥 Entradas do Mês", "R$ ••••••")
    with col3:
        st.metric("📤 Saídas do Mês", "R$ ••••••")
    with col4:
        st.metric("📈 Rendimentos", "R$ ••••••")

    st.divider()
    st.info(
        "🔧 **Fase 1 concluída!** Autenticação e navegação funcionais.\n\n"
        "Próximo passo: **Fase 2** — Dashboard com dados reais."
    )


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
    Pages.HOME: _render_home,
    # Fases futuras adicionarão as páginas aqui:
    # Pages.EXTRATO: render_extrato,
    # Pages.RENDIMENTOS: render_rendimentos,
    # Pages.CONTRIBUICOES: render_contribuicoes,
    # Pages.CONTAS: render_contas,
    # Pages.ADMIN_USUARIOS: render_admin_usuarios,
    # Pages.ADMIN_SYNC: render_admin_sync,
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
