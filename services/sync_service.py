"""
🐺 Wolf Wallet — Sync Service

Job de sincronização com a API do Mercado Pago.
Orquestra: geração de relatório → polling → download CSV → parse → insert no banco.

Usage:
    from services.sync_service import run_daily_sync, sync_transactions
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from config.settings import MercadoPago as MPConfig
from models.sync_log import create_log, get_last_successful_log
from models.transaction import insert_transactions_batch
from services.mercadopago import MercadoPagoAPIError, get_client

logger = logging.getLogger(__name__)

# Máximo de dias por relatório na API do Mercado Pago
_MAX_DAYS_PER_REPORT: int = 60


def get_last_sync_date() -> datetime | None:
    """
    Retorna a data final da última sincronização bem-sucedida.

    Returns:
        datetime ou None se nunca sincronizou.
    """
    log = get_last_successful_log()
    if log and log.get("end_date"):
        return log["end_date"]
    return None


def sync_transactions(
    begin_date: datetime,
    end_date: datetime,
    progress_callback: callable | None = None,
) -> dict:
    """
    Executa o fluxo completo de sincronização para um período.

    Fluxo:
        1. Gera relatório via POST /settlement_report
        2. Aguarda processamento (polling)
        3. Baixa o CSV
        4. Parseia com pandas
        5. Insere novos registros no banco (ignora duplicatas)
        6. Registra no sync_log

    Args:
        begin_date: Início do período.
        end_date: Fim do período.
        progress_callback: Função opcional para atualizar progresso (recebe str).

    Returns:
        Dict com: status, records_added, message.
    """
    def _progress(msg: str) -> None:
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    try:
        # 1. Conecta à API
        _progress("🔗 Conectando à API do Mercado Pago...")
        client = get_client()

        # 2. Gera relatório
        _progress(f"📊 Gerando relatório: {begin_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}...")
        result = client.generate_report(begin_date, end_date)

        report_id = result.get("id")
        if not report_id:
            logger.warning(f"Resposta do POST sem 'id': {result}")
            raise RuntimeError(
                "API não retornou o ID do relatório. "
                "Verifique se o token tem permissão para gerar relatórios."
            )

        # 3. Aguarda processamento (polling por ID até file_name aparecer)
        _progress(f"⏳ Aguardando processamento (id={report_id})...")
        file_name = client.wait_for_report_ready(report_id)

        if not file_name:
            raise RuntimeError(
                f"Relatório id={report_id} não ficou pronto em {MPConfig.POLL_MAX_WAIT_SECONDS}s."
            )

        # 4. Baixa o CSV
        _progress("⬇️ Baixando relatório CSV...")
        csv_content = client.download_report(file_name)

        if not csv_content or len(csv_content) < 10:
            raise RuntimeError("CSV vazio ou inválido.")

        # 5. Parseia o CSV
        _progress("🔄 Processando dados...")
        df = client.parse_settlement_csv(csv_content)

        if df.empty:
            # Sem transações novas — não é erro
            _progress("ℹ️ Nenhuma transação nova no período.")
            create_log(
                records_added=0,
                status="success",
                begin_date=begin_date,
                end_date=end_date,
            )
            return {
                "status": "success",
                "records_added": 0,
                "message": "Nenhuma transação nova no período.",
            }

        # 6. Insere no banco
        _progress(f"💾 Inserindo {len(df)} transações no banco...")
        records_added = insert_transactions_batch(df)

        # 7. Enriquece transações não-rendimento com descrição do pagamento
        _enrich_new_transactions(client, _progress)

        # 8. Registra no log
        create_log(
            records_added=records_added,
            status="success",
            begin_date=begin_date,
            end_date=end_date,
        )

        message = f"Sincronização concluída: {records_added} novas transações inseridas."
        _progress(f"✅ {message}")

        return {
            "status": "success",
            "records_added": records_added,
            "message": message,
        }

    except MercadoPagoAPIError as e:
        error_msg = f"Erro na API do Mercado Pago: {e}"
        logger.error(error_msg)
        create_log(
            records_added=0,
            status="error",
            error_message=error_msg,
            begin_date=begin_date,
            end_date=end_date,
        )
        return {
            "status": "error",
            "records_added": 0,
            "message": error_msg,
        }

    except Exception as e:
        error_msg = f"Erro durante sincronização: {e}"
        logger.error(error_msg, exc_info=True)
        create_log(
            records_added=0,
            status="error",
            error_message=error_msg,
            begin_date=begin_date,
            end_date=end_date,
        )
        return {
            "status": "error",
            "records_added": 0,
            "message": error_msg,
        }


def sync_transactions_chunked(
    begin_date: datetime,
    end_date: datetime,
    progress_callback: callable | None = None,
) -> dict:
    """
    Sincroniza um período longo dividindo em chunks de até 60 dias.

    A API do Mercado Pago retorna HTTP 400 para períodos maiores que ~60 dias.
    Esta função divide automaticamente e acumula os resultados.

    Args:
        begin_date: Início do período total.
        end_date: Fim do período total.
        progress_callback: Função opcional para atualizar progresso.

    Returns:
        Dict com: status, records_added, message.
    """
    total_days = (end_date - begin_date).days

    # Se cabe em um chunk, chama direto
    if total_days <= _MAX_DAYS_PER_REPORT:
        return sync_transactions(begin_date, end_date, progress_callback)

    def _progress(msg: str) -> None:
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    # Divide em chunks
    chunks: list[tuple[datetime, datetime]] = []
    chunk_start = begin_date
    while chunk_start < end_date:
        chunk_end = min(chunk_start + timedelta(days=_MAX_DAYS_PER_REPORT), end_date)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(seconds=1)

    total_records = 0
    errors: list[str] = []

    _progress(
        f"📦 Período longo detectado ({total_days} dias). "
        f"Dividindo em {len(chunks)} partes de até {_MAX_DAYS_PER_REPORT} dias..."
    )

    for i, (c_start, c_end) in enumerate(chunks, 1):
        _progress(
            f"📄 Parte {i}/{len(chunks)}: "
            f"{c_start.strftime('%d/%m/%Y')} → {c_end.strftime('%d/%m/%Y')}"
        )

        result = sync_transactions(c_start, c_end, progress_callback)

        if result["status"] == "success":
            total_records += result["records_added"]
        else:
            errors.append(f"Parte {i}: {result['message']}")

    if errors:
        msg = (
            f"Sincronização parcial: {total_records} registros importados, "
            f"{len(errors)} erro(s):\n" + "\n".join(errors)
        )
        return {"status": "error", "records_added": total_records, "message": msg}

    msg = f"Sincronização completa: {total_records} registros importados em {len(chunks)} partes."
    _progress(f"✅ {msg}")
    return {"status": "success", "records_added": total_records, "message": msg}


def _enrich_new_transactions(
    client: "MercadoPagoClient",
    progress_callback: callable | None = None,
) -> int:
    """
    Enriquece transações que ainda não têm payment_description.

    Somente busca para transações que NÃO são rendimento/imposto CDI:
    - Tem payment_method preenchido (pix, available_money, etc.)
    - OU valor absoluto >= threshold

    Isso evita chamadas desnecessárias para os ~90% de rendimentos.
    """
    from config.database import execute_query, execute_update
    from config.settings import Finance

    threshold = float(Finance.YIELD_THRESHOLD)

    # Busca transações sem descrição que não são rendimento
    rows = execute_query(
        "SELECT DISTINCT source_id FROM transactions "
        "WHERE payment_description IS NULL "
        "AND ("
        "  (payment_method IS NOT NULL AND payment_method != '') "
        "  OR ABS(transaction_amount) >= :threshold"
        ")",
        {"threshold": threshold},
    )

    if not rows:
        return 0

    source_ids = [r["source_id"] for r in rows if r.get("source_id")]

    if not source_ids:
        return 0

    def _progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    _progress(f"🏷️ Buscando descrições para {len(source_ids)} transações...")

    enrichments = client.enrich_transactions(source_ids)

    # Atualiza no banco
    updated = 0
    for sid, description in enrichments.items():
        rows_affected = execute_update(
            "UPDATE transactions SET payment_description = :desc "
            "WHERE source_id = :sid AND payment_description IS NULL",
            {"desc": description, "sid": sid},
        )
        updated += rows_affected or 0

    if updated:
        _progress(f"🏷️ {updated} transações enriquecidas com descrição.")

    return updated


def run_daily_sync(progress_callback: callable | None = None) -> dict:
    """
    Executa a sincronização diária automática.

    Determina o período automaticamente:
        - begin_date: data da última sync bem-sucedida (ou 6 meses atrás)
        - end_date: ontem 23:59:59

    Args:
        progress_callback: Função opcional para atualizar progresso.

    Returns:
        Dict com: status, records_added, message.
    """
    # Determina begin_date
    last_sync = get_last_sync_date()
    if last_sync:
        begin_date = last_sync
    else:
        # Primeira sync: 6 meses atrás
        begin_date = datetime.now() - timedelta(days=180)
        begin_date = begin_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # end_date: ontem 23:59:59
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)

    if begin_date >= end_date:
        return {
            "status": "success",
            "records_added": 0,
            "message": "Dados já estão atualizados (última sync é de hoje).",
        }

    return sync_transactions(begin_date, end_date, progress_callback)
