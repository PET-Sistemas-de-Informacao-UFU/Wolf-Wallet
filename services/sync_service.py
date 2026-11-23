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
from config.settings import utcnow_naive
from models.sync_log import create_log, get_last_successful_log
from models.transaction import insert_transactions_batch
from services.mercadopago import MercadoPagoAPIError, get_client

logger = logging.getLogger(__name__)

# Limite da API do Mercado Pago (dias máximos por relatório)
MAX_DAYS_PER_REPORT: int = 60


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
        7. Enriquece com descrição apenas as transações inseridas agora
           (etapa opcional: falhas aqui não invalidam a sincronização)

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

    # Valida limite de 60 dias da API
    total_days = (end_date - begin_date).days
    if total_days > MAX_DAYS_PER_REPORT:
        error_msg = (
            f"Período de {total_days} dias excede o limite de {MAX_DAYS_PER_REPORT} dias "
            f"da API do Mercado Pago. Selecione um período menor (máx. 60 dias por sync)."
        )
        _progress(f"❌ {error_msg}")
        return {
            "status": "error",
            "records_added": 0,
            "message": error_msg,
        }

    try:
        # 1. Conecta à API
        _progress("🔗 Conectando à API do Mercado Pago...")
        client = get_client()

        # 2. Reaproveita relatório existente do período, se houver.
        #    Evita gerar relatórios duplicados a cada retry e permite coletar
        #    um relatório que ficou preso em "pending" numa execução anterior
        #    (self-healing quando a fila do Mercado Pago está lenta).
        existing = client.find_report_by_period(begin_date, end_date)

        if existing and existing.get("file_name"):
            report_id = existing.get("id")
            _progress(f"♻️ Reaproveitando relatório já processado (id={report_id}).")
            file_name = existing["file_name"]

        elif existing:
            report_id = existing.get("id")
            _progress(
                f"⏳ Relatório do período já em processamento (id={report_id}) — "
                f"aguardando ficar pronto..."
            )
            file_name = client.wait_for_report_ready(report_id)

        else:
            # Gera um novo relatório
            _progress(
                f"📊 Gerando relatório: {begin_date.strftime('%d/%m/%Y')} → "
                f"{end_date.strftime('%d/%m/%Y')}..."
            )
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
                f"Relatório id={report_id} não ficou pronto em {MPConfig.POLL_MAX_WAIT_SECONDS}s. "
                f"Ele continua sendo processado no Mercado Pago e será coletado "
                f"automaticamente na próxima sincronização."
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

        # 6. Insere no banco (guardando o maior id anterior para saber
        #    quais transações foram inseridas nesta execução)
        last_id_before = _get_max_transaction_id()
        _progress(f"💾 Inserindo {len(df)} transações no banco...")
        records_added = insert_transactions_batch(df)

        # 7. Registra no log ANTES do enriquecimento. Os dados já estão no
        #    banco; se o enriquecimento demorar ou o processo for encerrado
        #    (hibernação/reinício do Streamlit Cloud), a sincronização não se
        #    perde e o critério de desatualização continua correto.
        create_log(
            records_added=records_added,
            status="success",
            begin_date=begin_date,
            end_date=end_date,
        )

        # 8. Enriquece somente as transações novas (opcional, best-effort)
        if records_added:
            try:
                _enrich_new_transactions(client, _progress, min_id=last_id_before)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Enriquecimento ignorado após erro: {e}")

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




def _get_max_transaction_id() -> int:
    """Retorna o maior id atual da tabela transactions (0 se vazia)."""
    from config.database import execute_query

    rows = execute_query("SELECT COALESCE(MAX(id), 0) AS max_id FROM transactions")
    return int(rows[0]["max_id"]) if rows else 0


def _enrich_new_transactions(
    client: "MercadoPagoClient",
    progress_callback: callable | None = None,
    min_id: int = 0,
) -> int:
    """
    Enriquece com descrição as transações inseridas nesta sincronização.

    Somente busca para transações que NÃO são rendimento/imposto CDI:
    - Tem payment_method preenchido (pix, available_money, etc.)
    - OU valor absoluto >= threshold

    Considera apenas transações com id > min_id (as recém-inseridas).
    Antes, toda sincronização reconsultava TODAS as transações sem
    descrição — inclusive centenas para as quais a API nunca retorna
    descrição —, acrescentando minutos e centenas de chamadas à API a
    cada execução.
    """
    from config.database import execute_query, execute_update
    from config.settings import Finance

    threshold = float(Finance.YIELD_THRESHOLD)

    # Busca transações sem descrição que não são rendimento
    rows = execute_query(
        "SELECT DISTINCT source_id FROM transactions "
        "WHERE payment_description IS NULL "
        "AND id > :min_id "
        "AND ("
        "  (payment_method IS NOT NULL AND payment_method != '') "
        "  OR ABS(transaction_amount) >= :threshold"
        ")",
        {"threshold": threshold, "min_id": min_id},
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
        - begin_date: início do DIA da última sync (inclusive — captura
          transações tardias daquele dia que podem ter ficado de fora)
        - end_date: agora (timestamp atual)

    Se a diferença ultrapassar 60 dias (limite da API), executa em
    blocos consecutivos de até 60 dias.

    Args:
        progress_callback: Função opcional para atualizar progresso.

    Returns:
        Dict com: status, records_added, message.
    """
    def _progress(msg: str) -> None:
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    # Determina begin_date (início do dia da última sync, para ser inclusivo)
    last_sync = get_last_sync_date()
    if last_sync:
        # Volta ao 00:00:00 (UTC) do dia da última sync para recapturar
        # transações tardias que podem não ter entrado no relatório anterior.
        # Em BRT isso corresponde às 21h do dia anterior: a sobreposição com
        # a janela anterior é de pelo menos 3 h, sem risco de duplicatas
        # (carga idempotente).
        begin_date = last_sync.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Primeira sync: 6 meses atrás
        begin_date = utcnow_naive() - timedelta(days=180)
        begin_date = begin_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # end_date: momento atual em UTC (convenção do projeto para datetimes
    # naive; a conversão para BRT ocorre ao montar a requisição à API)
    end_date = utcnow_naive().replace(second=0, microsecond=0)

    if begin_date >= end_date:
        return {
            "status": "success",
            "records_added": 0,
            "message": "Dados já estão atualizados (última sync é de hoje).",
        }

    # Se o período excede 60 dias, executa em blocos
    total_days = (end_date - begin_date).days
    if total_days > MAX_DAYS_PER_REPORT:
        return _sync_in_chunks(begin_date, end_date, progress_callback)

    return sync_transactions(begin_date, end_date, progress_callback)


def sync_custom_period(
    begin_date: datetime,
    end_date: datetime,
    progress_callback: callable | None = None,
) -> dict:
    """
    Sincroniza um período personalizado, quebrando automaticamente em blocos
    de até 60 dias quando necessário (limite da API do Mercado Pago).

    Usado pelo Sync Manual com período personalizado. Evita o erro
    "período excede 60 dias" e impede que ranges grandes gerem relatórios
    presos no Mercado Pago.

    Args:
        begin_date: Início do período.
        end_date: Fim do período.
        progress_callback: Função opcional para atualizar progresso.

    Returns:
        Dict com: status, records_added, message.
    """
    if begin_date >= end_date:
        return {
            "status": "error",
            "records_added": 0,
            "message": "A data de início deve ser anterior à data de fim.",
        }

    total_days = (end_date - begin_date).days
    if total_days > MAX_DAYS_PER_REPORT:
        return _sync_in_chunks(begin_date, end_date, progress_callback)

    return sync_transactions(begin_date, end_date, progress_callback)


def _sync_in_chunks(
    begin_date: datetime,
    end_date: datetime,
    progress_callback: callable | None = None,
) -> dict:
    """
    Executa sync em blocos de até 60 dias quando o período total é maior.

    Args:
        begin_date: Início do período total.
        end_date: Fim do período total.
        progress_callback: Função opcional para atualizar progresso.

    Returns:
        Dict com: status, records_added, message.
    """
    def _progress(msg: str) -> None:
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    total_records = 0
    chunk_start = begin_date
    chunk_num = 0

    while chunk_start < end_date:
        chunk_num += 1
        chunk_end = min(chunk_start + timedelta(days=MAX_DAYS_PER_REPORT), end_date)

        _progress(
            f"📦 Bloco {chunk_num}: "
            f"{chunk_start.strftime('%d/%m/%Y')} → {chunk_end.strftime('%d/%m/%Y')}"
        )

        result = sync_transactions(chunk_start, chunk_end, progress_callback)

        if result["status"] == "error":
            result["records_added"] += total_records
            return result

        total_records += result.get("records_added", 0)
        chunk_start = chunk_end

    message = f"Sincronização concluída em {chunk_num} bloco(s): {total_records} novas transações."
    _progress(f"✅ {message}")

    return {
        "status": "success",
        "records_added": total_records,
        "message": message,
    }
