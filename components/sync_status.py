"""
🐺 Wolf Wallet — Sync Status Banner Component

Banner persistente exibido no topo do Dashboard, Extrato e Sync
mostrando o estado atual da sincronização:

    - Última sync bem-sucedida (data, registros)
    - Progresso em tempo real quando uma sync está rodando
    - Indicador visual de sync em andamento

Usage:
    from components.sync_status import render_sync_banner
    render_sync_banner()  # Chamar no topo de cada página relevante
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from auth.session import is_visitor
from config.settings import Colors


def render_sync_banner() -> None:
    """
    Renderiza o banner de status da sincronização.

    - Se visitante: não exibe nada (modo mock).
    - Se sync rodando: mostra progresso em tempo real com steps.
    - Se idle: mostra a última sync com data e registros.
    """
    if is_visitor():
        return

    # Tenta obter progresso live da sync
    try:
        from services.auto_sync import get_sync_progress
        progress = get_sync_progress()
    except Exception:
        progress = {"running": False, "steps": [], "result": None}

    if progress["running"]:
        _render_running_banner(progress)
    else:
        _render_idle_banner(progress)


def _render_running_banner(progress: dict) -> None:
    """Exibe o banner com progresso em tempo real da sync."""
    steps = progress.get("steps", [])
    started_at = progress.get("started_at")

    # Último step como status principal
    current_step = steps[-1] if steps else "Iniciando..."

    # Tempo decorrido
    elapsed = ""
    if started_at:
        delta = datetime.now() - started_at
        elapsed = f" ({delta.seconds}s)"

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            border-radius: 10px;
            padding: 0.7rem 1.2rem;
            margin-bottom: 1rem;
            border-left: 4px solid {Colors.NEUTRAL};
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
        ">
            <div style="display: flex; align-items: center; gap: 0.6rem;">
                <span style="font-size: 1.1rem;" class="sync-spinner">🔄</span>
                <div>
                    <span style="color: #90CAF9; font-weight: 600; font-size: 0.88rem;">
                        Sincronização em andamento{elapsed}
                    </span>
                    <br>
                    <span style="color: #B0BEC5; font-size: 0.8rem;">
                        {current_step}
                    </span>
                </div>
            </div>
            <span style="color: #64B5F6; font-size: 0.75rem;">
                {len(steps)} etapa(s) concluída(s)
            </span>
        </div>
        <style>
            @keyframes wolf-spin {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
            .sync-spinner {{
                display: inline-block;
                animation: wolf-spin 2s linear infinite;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Expander com log detalhado das etapas
    if len(steps) > 1:
        with st.expander("📋 Ver etapas detalhadas", expanded=False):
            for step in steps:
                st.caption(step)


def _render_idle_banner(progress: dict) -> None:
    """Exibe o banner com info da última sync (idle)."""
    # Verifica se acabou de completar uma sync nesta sessão
    result = progress.get("result")
    finished_at = progress.get("finished_at")

    # Busca info do banco (última sync bem-sucedida)
    try:
        from models.sync_log import get_last_log
        last_log = get_last_log()
    except Exception:
        last_log = None

    if not last_log and not result:
        # Nunca sincronizou
        st.markdown(
            f"""
            <div style="
                background: rgba(255, 145, 0, 0.08);
                border-radius: 10px;
                padding: 0.6rem 1.2rem;
                margin-bottom: 1rem;
                border-left: 4px solid {Colors.ALERT};
                display: flex;
                align-items: center;
                gap: 0.6rem;
            ">
                <span style="font-size: 1rem;">⚠️</span>
                <span style="color: {Colors.ALERT}; font-size: 0.85rem;">
                    Nenhuma sincronização realizada ainda.
                    Acesse o painel de Sincronização para importar dados.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Dados da última sync
    if last_log:
        status = last_log.get("status", "unknown")
        sync_date = last_log.get("sync_date")
        records = last_log.get("records_added", 0)
        begin = last_log.get("begin_date")
        end = last_log.get("end_date")
    else:
        status = result.get("status", "unknown") if result else "unknown"
        sync_date = finished_at
        records = result.get("records_added", 0) if result else 0
        begin = None
        end = None

    # Formata data
    date_str = _format_dt(sync_date) if sync_date else "—"
    period_str = ""
    if begin and end:
        period_str = f" • Período: {_format_dt(begin)} → {_format_dt(end)}"

    if status == "success":
        icon = "✅"
        bg = "rgba(0, 200, 83, 0.06)"
        border_color = Colors.POSITIVE
        text_color = Colors.POSITIVE
        status_text = f"Última sincronização: {date_str} — {records} registro(s) adicionado(s){period_str}"
    else:
        icon = "❌"
        bg = "rgba(255, 23, 68, 0.06)"
        border_color = Colors.NEGATIVE
        text_color = Colors.NEGATIVE
        error_msg = ""
        if last_log and last_log.get("error_message"):
            error_msg = f" — {last_log['error_message'][:80]}"
        status_text = f"Última sincronização falhou: {date_str}{error_msg}"

    st.markdown(
        f"""
        <div style="
            background: {bg};
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            margin-bottom: 1rem;
            border-left: 4px solid {border_color};
            display: flex;
            align-items: center;
            gap: 0.6rem;
        ">
            <span style="font-size: 1rem;">{icon}</span>
            <span style="color: {text_color}; font-size: 0.83rem;">
                {status_text}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_dt(dt: datetime | str | None) -> str:
    """Formata datetime para exibição no banner."""
    if dt is None:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    return dt.strftime("%d/%m/%Y %H:%M")
