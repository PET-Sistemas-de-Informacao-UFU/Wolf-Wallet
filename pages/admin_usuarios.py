"""
🐺 Wolf Wallet — Admin Usuários

Página de gerenciamento de usuários (somente admin):
    - Tabela de membros com status
    - Criar novo usuário (com senha temporária + email)
    - Editar nome, email, role
    - Desativar / reativar usuário
    - Resetar senha (gera nova temporária + envia email)

Usage:
    from pages.admin_usuarios import render_admin_usuarios
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from auth.session import require_admin
from config.settings import Colors


def render_admin_usuarios() -> None:
    """Renderiza a página de gerenciamento de usuários."""
    if not require_admin():
        return

    st.title("👤 Gerenciamento de Usuários")
    st.caption("Criar, editar e gerenciar membros do PET-SI.")

    # Tabs para organizar as ações
    tab_list, tab_create = st.tabs(["📋 Membros", "➕ Novo Usuário"])

    with tab_list:
        _render_user_table()

    with tab_create:
        _render_create_form()


# =============================================
# Tabela de Usuários
# =============================================

def _render_user_table() -> None:
    """Tabela de usuários com ações de gerenciamento."""
    from models.user import get_all_users

    users = get_all_users(include_inactive=True)

    if not users:
        st.info("Nenhum usuário cadastrado.")
        return

    # Cards resumo
    active = [u for u in users if u.get("is_active")]
    inactive = [u for u in users if not u.get("is_active")]
    admins = [u for u in active if u.get("role") == "admin"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Membros Ativos", len(active))
    with col2:
        st.metric("Administradores", len(admins))
    with col3:
        st.metric("Inativos", len(inactive))

    st.divider()

    # Lista de usuários
    for user in users:
        _render_user_row(user)


def _render_user_row(user: dict) -> None:
    """Renderiza uma linha de usuário com ações."""
    user_id = user["id"]
    name = user["name"]
    email = user["email"]
    role = user["role"]
    is_active = user.get("is_active", True)
    created_at = user.get("created_at")

    # Visual
    status_badge = "🟢 Ativo" if is_active else "🔴 Inativo"
    role_badge = "🛡️ Admin" if role == "admin" else "👤 Membro"

    if created_at and isinstance(created_at, datetime):
        created_str = created_at.strftime("%d/%m/%Y")
    else:
        created_str = "—"

    # Container do usuário
    with st.container():
        # Info card (largura total — funciona bem no mobile)
        st.markdown(
            f"""
            <div style="
                padding: 0.6rem 1rem;
                border-radius: 8px;
                background: rgba(255,255,255,0.03);
                border-left: 3px solid {Colors.POSITIVE if is_active else Colors.NEGATIVE};
                margin-bottom: 0.3rem;
            ">
                <span style="font-size: 1rem; font-weight: 600;">{name}</span>
                <span style="color: #888; font-size: 0.8rem; margin-left: 0.5rem;">{role_badge}</span>
                <br>
                <span style="color: #aaa; font-size: 0.85rem;">📧 {email}</span>
                <span style="color: #666; font-size: 0.8rem; margin-left: 1rem;">📅 {created_str}</span>
                <span style="color: #888; font-size: 0.8rem; margin-left: 1rem;">{status_badge}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Botões de ação em linha horizontal
        st.markdown('<div class="wolf-action-btns">', unsafe_allow_html=True)
        btn_c1, btn_c2, btn_c3, btn_c4 = st.columns([1, 1, 1, 3])

        with btn_c1:
            if st.button("✏️ Editar", key=f"edit_{user_id}", width="stretch"):
                st.session_state[f"editing_user_{user_id}"] = True
                st.rerun()

        with btn_c2:
            if is_active:
                if st.button("🚫 Desativar", key=f"deact_{user_id}", width="stretch"):
                    st.session_state[f"confirm_deact_{user_id}"] = True
                    st.rerun()
            else:
                if st.button("✅ Reativar", key=f"react_{user_id}", width="stretch"):
                    _reactivate_user(user_id, name)

        with btn_c3:
            if is_active:
                if st.button("🔑 Senha", key=f"reset_{user_id}", width="stretch"):
                    st.session_state[f"confirm_reset_{user_id}"] = True
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Confirmações fora do layout de colunas
    if st.session_state.get(f"confirm_deact_{user_id}"):
        st.warning(f"⚠️ Desativar **{name}**? O usuário não poderá mais acessar o sistema.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirmar", key=f"yes_deact_{user_id}", type="primary"):
                st.session_state.pop(f"confirm_deact_{user_id}", None)
                _deactivate_user(user_id, name)
        with c2:
            if st.button("❌ Cancelar", key=f"no_deact_{user_id}"):
                st.session_state.pop(f"confirm_deact_{user_id}", None)
                st.rerun()

    if st.session_state.get(f"confirm_reset_{user_id}"):
        st.warning(f"⚠️ Resetar a senha de **{name}**? Uma nova senha temporária será gerada.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirmar", key=f"yes_reset_{user_id}", type="primary"):
                st.session_state.pop(f"confirm_reset_{user_id}", None)
                _reset_password(user_id, name, email)
        with c2:
            if st.button("❌ Cancelar", key=f"no_reset_{user_id}"):
                st.session_state.pop(f"confirm_reset_{user_id}", None)
                st.rerun()

    # Formulário de edição (expandido se clicou em editar)
    if st.session_state.get(f"editing_user_{user_id}"):
        _render_edit_form(user)


# =============================================
# Criar Usuário
# =============================================

def _render_create_form() -> None:
    """Formulário para criar novo usuário."""
    from services.email_service import is_email_configured

    if not is_email_configured():
        st.warning(
            "⚠️ Email não configurado. A senha temporária será exibida na tela "
            "(não será enviada por email). Configure `GMAIL_USER` e `GMAIL_APP_PASSWORD` "
            "em `.streamlit/secrets.toml`."
        )

    with st.form("create_user_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Nome completo *", placeholder="Ex: João Silva")
            email = st.text_input("Email *", placeholder="Ex: joao@gmail.com")

        with col2:
            role = st.selectbox("Papel", ["user", "admin"])
            st.markdown("<br>", unsafe_allow_html=True)
            send_email = st.checkbox("Enviar email com senha", value=True)

        submitted = st.form_submit_button("👤 Criar Usuário", type="primary")

        if submitted:
            if not name or not email:
                st.error("Nome e email são obrigatórios.")
                return

            _create_user(name.strip(), email.strip(), role, send_email)


def _create_user(name: str, email: str, role: str, send_email: bool) -> None:
    """Cria o usuário no banco e opcionalmente envia email."""
    from auth.password import generate_temp_password, hash_password
    from models.user import create_user
    from services.email_service import send_welcome_email

    temp_password = generate_temp_password()

    try:
        user = create_user(
            name=name,
            email=email,
            password_hash=hash_password(temp_password),
            role=role,
        )

        if not user:
            st.error("Erro ao criar usuário.")
            return

        # Marca para trocar senha no próximo login
        from models.user import update_user
        update_user(user["id"], must_change_password=True)

        st.success(f"✅ Usuário **{name}** criado com sucesso!")

        # Tenta enviar email
        email_sent = False
        if send_email:
            email_sent = send_welcome_email(name, email, temp_password)
            if email_sent:
                st.info("📧 Email de boas-vindas enviado!")

        # Mostra senha na tela se email não foi enviado
        if not email_sent:
            st.warning("⚠️ Anote a senha temporária (ela não será exibida novamente):")
            st.code(temp_password, language=None)

        st.rerun()

    except ValueError as e:
        st.error(f"❌ {e}")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")


# =============================================
# Editar Usuário
# =============================================

def _render_edit_form(user: dict) -> None:
    """Formulário inline para editar um usuário."""
    user_id = user["id"]

    with st.form(f"edit_form_{user_id}"):
        st.markdown(f"**Editando: {user['name']}**")

        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Nome", value=user["name"], key=f"ename_{user_id}")
            new_email = st.text_input("Email", value=user["email"], key=f"eemail_{user_id}")
        with col2:
            role_options = ["user", "admin"]
            current_idx = role_options.index(user["role"]) if user["role"] in role_options else 0
            new_role = st.selectbox("Papel", role_options, index=current_idx, key=f"erole_{user_id}")

        col_save, col_cancel = st.columns(2)
        with col_save:
            save = st.form_submit_button("💾 Salvar", type="primary")
        with col_cancel:
            cancel = st.form_submit_button("❌ Cancelar")

    if cancel:
        st.session_state.pop(f"editing_user_{user_id}", None)
        st.rerun()

    if save:
        _update_user(user_id, user, new_name, new_email, new_role)


def _update_user(user_id: int, old: dict, name: str, email: str, role: str) -> None:
    """Aplica as alterações no usuário."""
    from models.user import update_user

    changes = {}
    if name.strip() != old["name"]:
        changes["name"] = name.strip()
    if email.strip().lower() != old["email"]:
        changes["email"] = email.strip()
    if role != old["role"]:
        changes["role"] = role

    if not changes:
        st.info("Nenhuma alteração detectada.")
        st.session_state.pop(f"editing_user_{user_id}", None)
        st.rerun()
        return

    try:
        if update_user(user_id, **changes):
            st.success(f"✅ Usuário atualizado: {', '.join(changes.keys())}")
            st.session_state.pop(f"editing_user_{user_id}", None)
            st.rerun()
        else:
            st.error("Nenhum registro atualizado.")
    except Exception as e:
        st.error(f"Erro: {e}")


# =============================================
# Ações rápidas
# =============================================

def _deactivate_user(user_id: int, name: str) -> None:
    """Desativa um usuário."""
    from models.user import deactivate_user

    try:
        if deactivate_user(user_id):
            st.success(f"✅ {name} desativado.")
            st.rerun()
        else:
            st.warning("Usuário já estava inativo.")
    except Exception as e:
        st.error(f"Erro: {e}")


def _reactivate_user(user_id: int, name: str) -> None:
    """Reativa um usuário."""
    from models.user import reactivate_user

    try:
        if reactivate_user(user_id):
            st.success(f"✅ {name} reativado.")
            st.rerun()
        else:
            st.warning("Usuário já estava ativo.")
    except Exception as e:
        st.error(f"Erro: {e}")


def _reset_password(user_id: int, name: str, email: str) -> None:
    """Gera nova senha temporária e envia por email."""
    from auth.password import generate_temp_password, hash_password
    from models.user import update_user
    from services.email_service import send_password_reset_email

    temp_password = generate_temp_password()

    try:
        if update_user(user_id, password_hash=hash_password(temp_password), must_change_password=True):
            email_sent = send_password_reset_email(name, email, temp_password)

            if email_sent:
                st.success(f"✅ Senha resetada e email enviado para {email}.")
            else:
                st.warning(f"⚠️ Senha resetada mas email não enviado. Nova senha:")
                st.code(temp_password, language=None)

            st.rerun()
        else:
            st.error("Erro ao resetar senha.")
    except Exception as e:
        st.error(f"Erro: {e}")
