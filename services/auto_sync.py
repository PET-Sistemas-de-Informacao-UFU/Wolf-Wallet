"""
🐺 Wolf Wallet — Auto Sync

Sincronização automática diária em background.

Dois mecanismos complementares:
    1. @st.cache_resource — dispara UMA vez por cold start
    2. ensure_sync_freshness() — verifica staleness em CADA page load,
       redispara se necessário (cobre o caso do app ficar warm por dias)

O thread roda em daemon mode — quando Streamlit Cloud hiberna a app,
ao acordar um novo ciclo inicia e o sync é reavaliado.

O progresso da sync é armazenado em uma variável global thread-safe
e pode ser consultado em tempo real pelas páginas via get_sync_progress().

Usage:
    from services.auto_sync import start_auto_sync, ensure_sync_freshness
    start_auto_sync()           # Chamar no app.py (idempotente — 1x por cold start)
    ensure_sync_freshness()     # Chamar no app.py (cada page load)
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

import streamlit as st

logger = logging.getLogger(__name__)

# Intervalo entre verificações (24 h)
_SYNC_INTERVAL_HOURS: int = 24

# =============================================
# Progresso da sync (thread-safe, global)
# =============================================
_sync_lock = threading.Lock()
_sync_progress: dict = {
    "running": False,
    "steps": [],         # Lista de mensagens de progresso
    "started_at": None,
    "finished_at": None,
    "result": None,      # Dict com status/records_added/message quando concluído
}


def get_sync_progress() -> dict:
    """Retorna cópia do estado atual do progresso da sync."""
    with _sync_lock:
        return {**_sync_progress, "steps": list(_sync_progress["steps"])}


def _update_progress(**kwargs) -> None:
    """Atualiza o estado do progresso de forma thread-safe."""
    with _sync_lock:
        _sync_progress.update(kwargs)


def _progress_callback(msg: str) -> None:
    """Callback usado pelo sync_service para registrar cada etapa."""
    with _sync_lock:
        _sync_progress["steps"].append(msg)


def _is_sync_stale() -> bool:
    """Retorna True se a última sync foi há mais de _SYNC_INTERVAL_HOURS."""
    try:
        from services.sync_service import get_last_sync_date

        last = get_last_sync_date()
        if last is None:
            return True

        cutoff = datetime.now() - timedelta(hours=_SYNC_INTERVAL_HOURS)
        return last < cutoff
    except Exception:
        # Se não conseguir consultar o banco, não trava a app
        return False


def _is_running() -> bool:
    """Retorna True se já existe uma sync em andamento."""
    with _sync_lock:
        return _sync_progress["running"]


def _background_sync() -> None:
    """Executa run_daily_sync em background (thread daemon)."""
    # Double-check thread-safe para evitar duas threads simultâneas
    with _sync_lock:
        if _sync_progress["running"]:
            logger.info("Auto-sync: já existe uma sync em andamento, ignorando.")
            return
        _sync_progress["running"] = True
        _sync_progress["steps"] = ["🚀 Iniciando sincronização automática..."]
        _sync_progress["started_at"] = datetime.now()
        _sync_progress["finished_at"] = None
        _sync_progress["result"] = None

    try:
        if not _is_sync_stale():
            logger.info("Auto-sync: dados atualizados, nada a fazer.")
            _update_progress(running=False)
            return

        logger.info("Auto-sync: iniciando sincronização...")
        from services.sync_service import run_daily_sync

        result = run_daily_sync(progress_callback=_progress_callback)
        logger.info("Auto-sync concluído: %s", result.get("message", result))

        _update_progress(
            running=False,
            finished_at=datetime.now(),
            result=result,
        )

    except Exception:
        logger.exception("Auto-sync: erro durante sincronização automática.")
        _update_progress(
            running=False,
            finished_at=datetime.now(),
            result={"status": "error", "records_added": 0, "message": "Erro inesperado na sync automática."},
        )


def _launch_sync_thread(name: str = "wolf-auto-sync") -> None:
    """Cria e inicia uma daemon thread para sync."""
    thread = threading.Thread(
        target=_background_sync,
        name=name,
        daemon=True,
    )
    thread.start()


@st.cache_resource(show_spinner=False)
def start_auto_sync() -> str:
    """
    Dispara a sync automática em uma daemon thread.

    Usa @st.cache_resource para executar apenas UMA vez por ciclo
    de vida da app (Streamlit Cloud reinicia ≈ a cada cold start).

    Returns:
        Timestamp de quando o auto-sync foi agendado.
    """
    _launch_sync_thread("wolf-cold-start-sync")
    ts = datetime.now().isoformat()
    logger.info("Auto-sync thread iniciada em %s (cold start)", ts)
    return ts


def ensure_sync_freshness() -> None:
    """
    Verifica se os dados estão desatualizados e redispara sync se necessário.

    Chamada em CADA page load (app.py → main()). Cobre o cenário onde:
    - O app ficou warm por vários dias sem hibernar
    - O @st.cache_resource já rodou no cold start e não re-dispara
    - Nenhum usuário disparou sync manual

    É seguro chamar muitas vezes — não faz nada se a sync está em dia
    ou se já existe uma sync em andamento.
    """
    if _is_running():
        return

    if not _is_sync_stale():
        return

    logger.info("ensure_sync_freshness: dados desatualizados, disparando sync...")
    _launch_sync_thread("wolf-freshness-sync")
