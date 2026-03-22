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

from config.settings import App, Pages, SessionKeys, UI


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
# Session State Initialization
# =============================================
def _init_session_state() -> None:
    """
    Inicializa todas as chaves do session_state com valores padrão.

    Chamado uma vez no início de cada sessão do usuário.
    Garante que todas as chaves existam antes de serem acessadas,
    evitando KeyError em qualquer parte do código.
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
# Routing
# =============================================
def _get_current_page() -> str:
    """
    Determina qual página renderizar com base no estado da sessão.

    Returns:
        str: Identificador da página atual.
    """
    if not st.session_state.get(SessionKeys.AUTHENTICATED) and \
       not st.session_state.get(SessionKeys.IS_VISITOR):
        return Pages.LOGIN

    return st.session_state.get(SessionKeys.CURRENT_PAGE, Pages.HOME)


def _render_page(page: str) -> None:
    """
    Renderiza a página correspondente ao identificador.

    Na Fase 0, apenas exibe placeholders. As páginas reais
    serão implementadas nas fases subsequentes.

    Args:
        page: Identificador da página (ex: 'home', 'extrato').
    """
    if page == Pages.LOGIN:
        _render_login_placeholder()
    elif page == Pages.HOME:
        _render_home_placeholder()
    else:
        _render_coming_soon(page)


# =============================================
# Placeholders (serão substituídos nas próximas fases)
# =============================================
def _render_login_placeholder() -> None:
    """Placeholder da tela de login — será substituído na Fase 1."""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            f"<h1 style='text-align: center;'>{App.TITLE}</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align: center; color: gray;'>{App.DESCRIPTION}</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        st.info("🔧 Sistema em desenvolvimento — Fase 0 concluída.")
        st.caption(f"v{App.VERSION} • {App.AUTHOR}")

        # Botão temporário para testar navegação
        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔐 Simular Login (Admin)", use_container_width=True):
                st.session_state[SessionKeys.AUTHENTICATED] = True
                st.session_state[SessionKeys.ROLE] = "admin"
                st.session_state[SessionKeys.CURRENT_PAGE] = Pages.HOME
                st.session_state[SessionKeys.USER] = {
                    "id": 0, "name": "Admin (Dev)", "email": "dev@ufu.br", "role": "admin"
                }
                st.rerun()
        with col_b:
            if st.button("👀 Entrar como Visitante", use_container_width=True):
                st.session_state[SessionKeys.IS_VISITOR] = True
                st.session_state[SessionKeys.CURRENT_PAGE] = Pages.HOME
                st.rerun()


def _render_home_placeholder() -> None:
    """Placeholder do dashboard — será substituído na Fase 2."""
    _render_dev_sidebar()

    st.title(f"{App.EMOJI} Dashboard")

    # Banner de visitante
    if st.session_state.get(SessionKeys.IS_VISITOR):
        st.warning(
            "🔍 Você está no modo visitante. "
            "Os dados exibidos são fictícios para demonstração."
        )

    # Info do usuário
    user = st.session_state.get(SessionKeys.USER)
    if user:
        st.success(f"Logado como **{user['name']}** ({user['role']})")
    else:
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
        "🔧 **Fase 0 concluída!** Estrutura do projeto criada com sucesso.\n\n"
        "Próximo passo: **Fase 1** — Sistema de autenticação e navegação."
    )


def _render_coming_soon(page: str) -> None:
    """Placeholder genérico para páginas ainda não implementadas."""
    _render_dev_sidebar()
    st.title(f"🚧 {page.replace('_', ' ').title()}")
    st.info(f"Esta página será implementada em uma fase futura.")


def _render_dev_sidebar() -> None:
    """Sidebar temporário para desenvolvimento — será substituído na Fase 1."""
    with st.sidebar:
        st.markdown(f"### {App.TITLE}")
        st.caption(f"v{App.VERSION}")
        st.divider()

        # Navegação temporária
        page_options = {
            f"{UI.ICONS['dashboard']} Dashboard": Pages.HOME,
            f"{UI.ICONS['extrato']} Extrato": Pages.EXTRATO,
            f"{UI.ICONS['rendimentos']} Rendimentos": Pages.RENDIMENTOS,
            f"{UI.ICONS['contribuicoes']} Contribuições": Pages.CONTRIBUICOES,
            f"{UI.ICONS['contas']} Contas Mensais": Pages.CONTAS,
        }

        # Páginas admin
        if st.session_state.get(SessionKeys.ROLE) == "admin":
            page_options[f"{UI.ICONS['admin_usuarios']} Usuários"] = Pages.ADMIN_USUARIOS
            page_options[f"{UI.ICONS['admin_sync']} Sincronização"] = Pages.ADMIN_SYNC

        selected = st.radio(
            "Navegação",
            options=list(page_options.keys()),
            label_visibility="collapsed",
        )

        if selected:
            st.session_state[SessionKeys.CURRENT_PAGE] = page_options[selected]

        st.divider()

        # Logout
        if st.button("🚪 Sair", use_container_width=True):
            for key in SessionKeys.__dict__:
                if not key.startswith("_"):
                    attr = getattr(SessionKeys, key)
                    if attr in st.session_state:
                        del st.session_state[attr]
            st.rerun()


# =============================================
# Main
# =============================================
def main() -> None:
    """Função principal — orquestra a inicialização e roteamento."""
    _init_session_state()

    current_page = _get_current_page()
    _render_page(current_page)


if __name__ == "__main__":
    main()
