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

import itertools
import logging
import threading
from datetime import datetime, timedelta

import streamlit as st

from config.settings import utcnow_naive

logger = logging.getLogger(__name__)

# Intervalo entre verificações (24 h)
_SYNC_INTERVAL_HOURS: int = 24

# Uma sincronização "em andamento" há mais tempo que isto é considerada
# travada e deixa de bloquear novas execuções. O pior caso legítimo é de
# ~15 min de espera pelo relatório + download + carga por bloco.
_SYNC_STUCK_AFTER: timedelta = timedelta(minutes=45)

# Gerador de identificadores de execução (thread-safe sob o _sync_lock)
_run_counter = itertools.count(1)

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
    "run_id": None,      # Identifica a execução dona do progresso atual
}


def get_sync_progress() -> dict:
    """Retorna cópia do estado atual do progresso da sync."""
    with _sync_lock:
        snapshot = {**_sync_progress, "steps": list(_sync_progress["steps"])}
        if _is_stuck_locked():
            # Execução travada não deve aparecer como "em andamento" para sempre
            snapshot["running"] = False
        return snapshot


def _update_progress(**kwargs) -> None:
    """Atualiza o estado do progresso de forma thread-safe."""
    with _sync_lock:
        _sync_progress.update(kwargs)


def _progress_callback(msg: str) -> None:
    """Callback usado pelo sync_service para registrar cada etapa."""
    with _sync_lock:
        _sync_progress["steps"].append(msg)


def _make_run_callback(run_id: int | str):
    """Callback que só registra etapas enquanto `run_id` for a execução atual."""
    def _cb(msg: str) -> None:
        with _sync_lock:
            if _sync_progress.get("run_id") == run_id:
                _sync_progress["steps"].append(msg)
    return _cb


def _is_stuck_locked() -> bool:
    """(Requer _sync_lock) True se há uma execução marcada como ativa há tempo demais."""
    started = _sync_progress.get("started_at")
    return (
        _sync_progress["running"]
        and started is not None
        and datetime.now() - started > _SYNC_STUCK_AFTER
    )


def mark_sync_started(initial_step: str) -> str:
    """
    Marca o início de uma sincronização (manual) no progresso global.

    Returns:
        Identificador da execução, a ser passado para `mark_sync_finished`.
    """
    with _sync_lock:
        run_id = f"manual-{next(_run_counter)}"
        _sync_progress.update(
            running=True,
            steps=[initial_step],
            started_at=datetime.now(),
            finished_at=None,
            result=None,
            run_id=run_id,
        )
    return run_id


def mark_sync_finished(run_id: str, result: dict) -> None:
    """Marca o fim da execução `run_id` (ignorado se outra execução assumiu)."""
    with _sync_lock:
        if _sync_progress.get("run_id") != run_id:
            return
        _sync_progress.update(running=False, finished_at=datetime.now(), result=result)


def _is_sync_stale() -> bool:
    """Retorna True se a última sync foi há mais de _SYNC_INTERVAL_HOURS."""
    try:
        from services.sync_service import get_last_sync_date

        last = get_last_sync_date()
        if last is None:
            return True

        # end_date do sync_log é UTC naive (convenção do projeto)
        cutoff = utcnow_naive() - timedelta(hours=_SYNC_INTERVAL_HOURS)
        return last < cutoff
    except Exception:
        # Se não conseguir consultar o banco, não trava a app
        return False


def _is_running() -> bool:
    """
    Retorna True se já existe uma sync em andamento.

    Uma execução marcada como ativa há mais de `_SYNC_STUCK_AFTER` é
    considerada travada e NÃO bloqueia novas sincronizações. Antes, uma
    thread presa (ex.: API lenta) mantinha `running=True` indefinidamente
    e todas as visitas seguintes deixavam de disparar a sincronização.
    """
    with _sync_lock:
        return _sync_progress["running"] and not _is_stuck_locked()


def _background_sync() -> None:
    """Executa run_daily_sync em background (thread daemon)."""
    # Double-check thread-safe para evitar duas threads simultâneas
    with _sync_lock:
        if _sync_progress["running"]:
            if not _is_stuck_locked():
                logger.info("Auto-sync: já existe uma sync em andamento, ignorando.")
                return
            logger.warning(
                "Auto-sync: execução anterior (run_id=%s) ativa desde %s parece travada; "
                "liberando a trava e iniciando nova sincronização.",
                _sync_progress.get("run_id"), _sync_progress.get("started_at"),
            )
        run_id = next(_run_counter)
        _sync_progress["running"] = True
        _sync_progress["steps"] = ["🚀 Iniciando sincronização automática..."]
        _sync_progress["started_at"] = datetime.now()
        _sync_progress["finished_at"] = None
        _sync_progress["result"] = None
        _sync_progress["run_id"] = run_id

    def _finish(**kwargs) -> None:
        # Só atualiza se esta thread ainda for a dona do progresso (uma thread
        # travada que termine tarde não sobrescreve a execução mais nova).
        with _sync_lock:
            if _sync_progress.get("run_id") == run_id:
                _sync_progress.update(kwargs)

    try:
        if not _is_sync_stale():
            logger.info("Auto-sync: dados atualizados, nada a fazer.")
            _finish(running=False)
            return

        logger.info("Auto-sync: iniciando sincronização (run_id=%s)...", run_id)
        from services.sync_service import run_daily_sync

        result = run_daily_sync(progress_callback=_make_run_callback(run_id))
        logger.info("Auto-sync concluído: %s", result.get("message", result))

        _finish(
            running=False,
            finished_at=datetime.now(),
            result=result,
        )

    except Exception:
        logger.exception("Auto-sync: erro durante sincronização automática.")
        _finish(
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
