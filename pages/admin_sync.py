"""
🐺 Wolf Wallet — Admin Sync Panel

Painel de sincronização (somente admin):
    - Status da última sync
    - Histórico de syncs
    - Botão "Sincronizar agora"
    - Configuração atual do relatório na API

Usage:
    from pages.admin_sync import render_admin_sync
"""

from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from auth.session import require_admin
from components.sync_status import render_sync_banner
from config.settings import Colors, to_brasilia


def render_admin_sync() -> None:
    """Renderiza o painel de sincronização."""
    if not require_admin():
        return

    render_sync_banner()

    st.title("🔄 Painel de Sincronização")
    st.caption("Gerencie a sincronização de dados com a API do Mercado Pago.")

    # Tabs
    tab_status, tab_manual, tab_history, tab_config = st.tabs([
        "📊 Status", "▶️ Sync Manual", "📋 Histórico", "⚙️ Configuração"
    ])

    with tab_status:
        _render_status()

    with tab_manual:
        _render_manual_sync()

    with tab_history:
        _render_history()

    with tab_config:
        _render_config()


def _render_status() -> None:
    """Exibe o status da última sincronização."""
    try:
        from models.sync_log import get_last_log, get_sync_stats

        last_log = get_last_log()
        stats = get_sync_stats()

        # Cards de stats
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Syncs", stats.get("total_syncs", 0))
        with col2:
            st.metric("✅ Sucesso", stats.get("successful", 0))
        with col3:
            st.metric("❌ Erros", stats.get("failed", 0))
        with col4:
            st.metric("📦 Registros Importados", stats.get("total_records", 0))

        st.divider()

        # Última sync
        if last_log:
            status = last_log.get("status", "unknown")
            sync_date = last_log.get("sync_date")
            records = last_log.get("records_added", 0)

            if status == "success":
                st.success(
                    f"✅ **Última sincronização:** {_format_datetime(sync_date)} — "
                    f"{records} registros adicionados"
                )
            else:
                st.error(
                    f"❌ **Última sincronização falhou:** {_format_datetime(sync_date)}\n\n"
                    f"Erro: {last_log.get('error_message', 'Desconhecido')}"
                )

            # Período sincronizado
            begin = last_log.get("begin_date")
            end = last_log.get("end_date")
            if begin and end:
                st.caption(f"Período: {_format_datetime(begin)} → {_format_datetime(end)}")
        else:
            st.warning("⚠️ Nenhuma sincronização realizada ainda.")
            st.info("Use a aba **Sync Manual** para executar a primeira sincronização.")

    except Exception as e:
        st.error(f"⚠️ Erro ao carregar status: {e}")
        st.info("Verifique a conexão com o banco de dados.")


def _render_manual_sync() -> None:
    """Interface para disparar sync manual."""
    st.markdown("##### ▶️ Sincronizar Agora")
    st.markdown(
        "Execute uma sincronização sob demanda. "
        "O sistema irá consultar a API do Mercado Pago e importar novas transações."
    )

    # Mostra período que será sincronizado no modo automático
    try:
        from services.sync_service import get_last_sync_date
        last_sync = get_last_sync_date()
        if last_sync:
            inclusive_date = last_sync.replace(hour=0, minute=0, second=0)
            st.info(
                f"ℹ️ **Modo automático:** sincronizará desde "
                f"**{inclusive_date.strftime('%d/%m/%Y')}** (início do dia da última sync, "
                f"para recapturar transações tardias) até **agora**."
            )
    except Exception:
        pass

    # Opções de período
    sync_type = st.radio(
        "Tipo de sincronização",
        options=["Automático (desde última sync)", "Período personalizado"],
        key="sync_type",
    )

    begin_date = None
    end_date = None

    if sync_type == "Período personalizado":
        st.info(
            "⚠️ **Limite da API do Mercado Pago:** máximo de **60 dias** por sincronização. "
            "Para importar históricos longos, execute múltiplas syncs de até 60 dias."
        )

        col1, col2 = st.columns(2)
        with col1:
            begin_date_input = st.date_input(
                "Data início",
                value=datetime.now() - timedelta(days=30),
                key="sync_begin",
            )
        with col2:
            end_date_input = st.date_input(
                "Data fim",
                value=datetime.now() - timedelta(days=1),
                key="sync_end",
            )

        begin_date = datetime.combine(begin_date_input, datetime.min.time())
        end_date = datetime.combine(end_date_input, datetime.max.time().replace(microsecond=0))

        # Mostra dias selecionados
        days_selected = (end_date - begin_date).days
        if days_selected > 60:
            st.error(
                f"❌ Período selecionado: **{days_selected} dias**. "
                f"Reduza para no máximo 60 dias."
            )

    st.divider()

    # Botão de sync
    if st.button("🔄 Iniciar Sincronização", type="primary", width="stretch"):
        _execute_sync(begin_date, end_date)


def _execute_sync(begin_date: datetime | None, end_date: datetime | None) -> None:
    """Executa a sincronização com feedback visual e atualiza banner global."""
    progress_container = st.empty()
    status_container = st.empty()

    progress_messages: list[str] = []

    def progress_callback(msg: str) -> None:
        """Atualiza tanto o feedback local quanto o banner global."""
        progress_messages.append(msg)
        progress_container.markdown(
            "\n\n".join(f"- {m}" for m in progress_messages)
        )
        # Também alimenta o progresso global (banner)
        try:
            from services.auto_sync import _progress_callback as global_cb
            global_cb(msg)
        except Exception:
            pass

    try:
        from services.sync_service import run_daily_sync, sync_transactions
        from services.auto_sync import _update_progress

        # Marca início no progresso global
        _update_progress(
            running=True,
            steps=["🚀 Sincronização manual iniciada..."],
            started_at=datetime.now(),
            finished_at=None,
            result=None,
        )

        with st.spinner("Sincronizando..."):
            if begin_date and end_date:
                result = sync_transactions(begin_date, end_date, progress_callback)
            else:
                result = run_daily_sync(progress_callback)

        # Marca fim no progresso global
        _update_progress(
            running=False,
            finished_at=datetime.now(),
            result=result,
        )

        if result["status"] == "success":
            status_container.success(f"✅ {result['message']}")
        else:
            status_container.error(f"❌ {result['message']}")

    except Exception as e:
        try:
            from services.auto_sync import _update_progress
            _update_progress(
                running=False,
                finished_at=datetime.now(),
                result={"status": "error", "records_added": 0, "message": str(e)},
            )
        except Exception:
            pass
        status_container.error(f"❌ Erro inesperado: {e}")


def _render_history() -> None:
    """Exibe o histórico de sincronizações."""
    st.markdown("##### 📋 Histórico de Sincronizações")

    try:
        from models.sync_log import get_all_logs

        logs = get_all_logs(limit=50)

        if not logs:
            st.info("Nenhuma sincronização registrada.")
            return

        for log in logs:
            status = log.get("status", "unknown")
            sync_date = log.get("sync_date")
            records = log.get("records_added", 0)
            begin = log.get("begin_date")
            end = log.get("end_date")
            error = log.get("error_message")

            icon = "✅" if status == "success" else "❌"
            color = Colors.POSITIVE if status == "success" else Colors.NEGATIVE

            with st.container():
                cols = st.columns([0.5, 2, 1, 1])
                with cols[0]:
                    st.markdown(f"### {icon}")
                with cols[1]:
                    st.markdown(f"**{_format_datetime(sync_date)}**")
                    if begin and end:
                        st.caption(f"Período: {_format_datetime(begin)} → {_format_datetime(end)}")
                with cols[2]:
                    st.metric("Registros", records, label_visibility="collapsed")
                with cols[3]:
                    if error:
                        with st.expander("Ver erro"):
                            st.code(error, language=None)

            st.divider()

    except Exception as e:
        st.error(f"⚠️ Erro ao carregar histórico: {e}")
        st.info("Verifique a conexão com o banco de dados.")


def _render_config() -> None:
    """Exibe a configuração atual do relatório na API do MP."""
    st.markdown("##### ⚙️ Configuração do Relatório")
    st.markdown(
        "Configuração atual do Settlement Report na API do Mercado Pago. "
        "Alterações aqui afetam os próximos relatórios gerados."
    )

    if st.button("🔍 Consultar Configuração", key="fetch_config"):
        try:
            from services.mercadopago import get_client

            with st.spinner("Consultando API..."):
                client = get_client()
                config = client.get_config()

            st.json(config)

        except Exception as e:
            st.error(f"❌ Erro ao consultar configuração: {e}")
            st.info(
                "Verifique se o MP_ACCESS_TOKEN está configurado "
                "em .streamlit/secrets.toml ou .env."
            )

    st.divider()
    st.markdown("##### 📅 Geração Automática")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Ativar Schedule", key="enable_schedule"):
            try:
                from services.mercadopago import get_client
                client = get_client()
                result = client.enable_schedule()
                st.success("Schedule ativado com sucesso!")
                st.json(result)
            except Exception as e:
                st.error(f"Erro: {e}")

    with col2:
        if st.button("⏹️ Desativar Schedule", key="disable_schedule"):
            try:
                from services.mercadopago import get_client
                client = get_client()
                result = client.disable_schedule()
                st.success("Schedule desativado.")
                st.json(result)
            except Exception as e:
                st.error(f"Erro: {e}")


def _format_datetime(dt: datetime | str | None) -> str:
    """Formata datetime para exibição (horário de Brasília)."""
    if dt is None:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    # Converte para horário de Brasília
    dt = to_brasilia(dt)
    return dt.strftime("%d/%m/%Y %H:%M")
