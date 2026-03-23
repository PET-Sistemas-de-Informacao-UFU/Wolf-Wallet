"""
🐺 Wolf Wallet — Auto Sync

Sincronização automática diária em background.
Usa @st.cache_resource para disparar UMA vez por ciclo de vida da app.

O thread roda em daemon mode — quando Streamlit Cloud hiberna a app,
ao acordar um novo ciclo inicia e o sync é reavaliado.

Usage:
    from services.auto_sync import start_auto_sync
    start_auto_sync()       # Chamar no app.py (idempotente)
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

import streamlit as st

logger = logging.getLogger(__name__)

# Intervalo entre verificações (24 h)
_SYNC_INTERVAL_HOURS: int = 24


def _is_sync_stale() -> bool:
    """Retorna True se a última sync foi há mais de _SYNC_INTERVAL_HOURS."""
    from services.sync_service import get_last_sync_date

    last = get_last_sync_date()
    if last is None:
        return True

    cutoff = datetime.now() - timedelta(hours=_SYNC_INTERVAL_HOURS)
    return last < cutoff


def _background_sync() -> None:
    """Executa run_daily_sync em background (thread daemon)."""
    try:
        if not _is_sync_stale():
            logger.info("Auto-sync: dados atualizados, nada a fazer.")
            return

        logger.info("Auto-sync: iniciando sincronização D-1...")
        from services.sync_service import run_daily_sync

        result = run_daily_sync()
        logger.info("Auto-sync concluído: %s", result.get("message", result))
    except Exception:
        logger.exception("Auto-sync: erro durante sincronização automática.")


@st.cache_resource(show_spinner=False)
def start_auto_sync() -> str:
    """
    Dispara a sync automática em uma daemon thread.

    Usa @st.cache_resource para executar apenas UMA vez por ciclo
    de vida da app (Streamlit Cloud reinicia ≈ a cada cold start).

    Returns:
        Timestamp de quando o auto-sync foi agendado.
    """
    thread = threading.Thread(
        target=_background_sync,
        name="wolf-auto-sync",
        daemon=True,
    )
    thread.start()
    ts = datetime.now().isoformat()
    logger.info("Auto-sync thread iniciada em %s", ts)
    return ts
