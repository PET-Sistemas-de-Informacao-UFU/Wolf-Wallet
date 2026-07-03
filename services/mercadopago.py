"""
🐺 Wolf Wallet — Mercado Pago API Client

Integração com a Settlement Report API v1 do Mercado Pago.
Gerencia geração, listagem, download e parsing de relatórios.

Docs: https://www.mercadopago.com.br/developers/pt/reference/settlement_report

Usage:
    from services.mercadopago import MercadoPagoClient

    client = MercadoPagoClient(access_token="APP_USR-...")
    reports = client.list_reports()
"""

from __future__ import annotations

import io
import logging
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from config.settings import MercadoPago as MPConfig

logger = logging.getLogger(__name__)


class MercadoPagoAPIError(Exception):
    """Erro específico da API do Mercado Pago."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[HTTP {status_code}] {message}")


class MercadoPagoClient:
    """
    Cliente para a Settlement Report API do Mercado Pago.

    Attributes:
        base_url: URL base da API.
        headers: Headers com autenticação Bearer.
        timeout: Timeout para requests em segundos.
    """

    def __init__(self, access_token: str):
        """
        Inicializa o cliente com o access token.

        Args:
            access_token: Token de acesso da conta MP (APP_USR-...).
        """
        self.base_url = MPConfig.BASE_URL
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        self.timeout = MPConfig.REQUEST_TIMEOUT

    # =============================================
    # Internal: HTTP com retry
    # =============================================

    def _request(
        self,
        method: str,
        endpoint: str = "",
        json: dict | None = None,
        params: dict | None = None,
        accept_text: bool = False,
    ) -> dict | str:
        """
        Faz uma requisição HTTP com retry e backoff exponencial.

        Args:
            method: GET, POST, PUT, DELETE.
            endpoint: Path relativo (ex: "/config", "/list").
            json: Body JSON para POST/PUT.
            params: Query params.
            accept_text: Se True, retorna resposta como texto (CSV).

        Returns:
            Dict (JSON) ou str (texto).

        Raises:
            MercadoPagoAPIError: Em caso de erro HTTP.
        """
        url = f"{self.base_url}{endpoint}"
        headers = {**self.headers}
        if accept_text:
            headers["Accept"] = "text/csv"

        last_error = None

        for attempt in range(1, MPConfig.MAX_RETRIES + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    params=params,
                    timeout=self.timeout,
                )

                # Sucesso
                if response.status_code in (200, 201, 202):
                    if accept_text:
                        return response.text
                    return response.json()

                # Erros que não fazem sentido retry
                if response.status_code in (400, 401, 403, 404):
                    error_msg = self._extract_error(response)
                    raise MercadoPagoAPIError(response.status_code, error_msg)

                # Rate limit — espera e retenta
                if response.status_code == 429:
                    wait = MPConfig.RETRY_BACKOFF_FACTOR ** attempt
                    logger.warning(f"Rate limit (429). Tentativa {attempt}/{MPConfig.MAX_RETRIES}. Aguardando {wait}s...")
                    time.sleep(wait)
                    last_error = MercadoPagoAPIError(429, "Rate limit exceeded")
                    continue

                # Erro servidor — retenta
                if response.status_code >= 500:
                    wait = MPConfig.RETRY_BACKOFF_FACTOR ** attempt
                    logger.warning(f"Erro servidor ({response.status_code}). Tentativa {attempt}/{MPConfig.MAX_RETRIES}. Aguardando {wait}s...")
                    time.sleep(wait)
                    last_error = MercadoPagoAPIError(response.status_code, self._extract_error(response))
                    continue

                # Outro erro
                raise MercadoPagoAPIError(response.status_code, self._extract_error(response))

            except requests.exceptions.Timeout:
                wait = MPConfig.RETRY_BACKOFF_FACTOR ** attempt
                logger.warning(f"Timeout. Tentativa {attempt}/{MPConfig.MAX_RETRIES}. Aguardando {wait}s...")
                time.sleep(wait)
                last_error = MercadoPagoAPIError(0, "Request timeout")

            except requests.exceptions.ConnectionError as e:
                wait = MPConfig.RETRY_BACKOFF_FACTOR ** attempt
                logger.warning(f"Erro de conexão. Tentativa {attempt}/{MPConfig.MAX_RETRIES}. Aguardando {wait}s...")
                time.sleep(wait)
                last_error = MercadoPagoAPIError(0, f"Connection error: {e}")

            except MercadoPagoAPIError:
                raise

        # Todas as tentativas falharam
        raise last_error or MercadoPagoAPIError(0, "Todas as tentativas falharam")

    @staticmethod
    def _extract_error(response: requests.Response) -> str:
        """Extrai mensagem de erro da resposta."""
        try:
            data = response.json()
            return data.get("message", data.get("error", str(data)))
        except Exception:
            return response.text[:500] if response.text else f"HTTP {response.status_code}"

    # =============================================
    # Config
    # =============================================

    def get_config(self) -> dict:
        """
        Consulta a configuração atual do relatório.

        Returns:
            Dict com a configuração (colunas, frequência, timezone, etc.).
        """
        logger.info("Consultando configuração do relatório...")
        return self._request("GET", "/config")

    def update_config(self, config: dict) -> dict:
        """
        Atualiza a configuração do relatório.

        Args:
            config: Nova configuração (partial update).

        Returns:
            Dict com a configuração atualizada.
        """
        logger.info("Atualizando configuração do relatório...")
        return self._request("PUT", "/config", json=config)

    # =============================================
    # Report Generation & Download
    # =============================================

    def generate_report(self, begin_date: datetime, end_date: datetime) -> dict:
        """
        Solicita a geração de um relatório por período.

        Args:
            begin_date: Início do período.
            end_date: Fim do período.

        Returns:
            Dict com dados do relatório solicitado (file_name, etc.).
        """
        payload = {
            "begin_date": begin_date.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "end_date": end_date.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
        }
        logger.info(f"Gerando relatório: {payload['begin_date']} → {payload['end_date']}")
        return self._request("POST", "", json=payload)

    def list_reports(self) -> list[dict]:
        """
        Lista todos os relatórios gerados.

        Returns:
            Lista de dicts com: id, file_name, date_created, status, etc.
        """
        logger.info("Listando relatórios...")
        result = self._request("GET", "/list")
        # A API retorna uma lista diretamente
        return result if isinstance(result, list) else []

    def find_report_by_id(self, report_id: int | str) -> dict | None:
        """
        Busca um relatório pelo ID na lista.

        Args:
            report_id: ID do relatório retornado pelo POST.

        Returns:
            Dict do relatório, ou None se não encontrado.
        """
        report_id = int(report_id)
        reports = self.list_reports()
        for report in reports:
            if report.get("id") == report_id:
                return report
        return None

    @staticmethod
    def _report_brt_date(iso_str: str | None):
        """Converte um timestamp ISO (UTC) do relatório para a data em BRT (UTC-3)."""
        if not iso_str:
            return None
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return (dt - timedelta(hours=3)).date()
        except Exception:
            return None

    def find_report_by_period(
        self,
        begin_date: datetime,
        end_date: datetime,
        max_age_hours: int = 6,
    ) -> dict | None:
        """
        Procura um relatório existente que cubra o mesmo período (dia a dia).

        Serve para dois objetivos:
            1. Evitar gerar relatórios duplicados a cada retry (o MP acumula
               relatórios "pending" quando está lento).
            2. Self-healing: coletar um relatório gerado numa execução anterior
               que ficou preso em "pending" e só ficou pronto depois.

        O MP normaliza begin/end para dias inteiros (BRT), então o casamento
        é feito por data (ignora hora). Relatórios em erro são descartados.

        Args:
            begin_date: Início do período solicitado.
            end_date: Fim do período solicitado.
            max_age_hours: Só considera relatórios criados nas últimas N horas
                (limita a "idade" do snapshot reaproveitado).

        Returns:
            O relatório mais recente que casa com o período, ou None.
        """
        target_begin = begin_date.date()
        target_end = end_date.date()
        now_utc = datetime.now(timezone.utc)

        candidates: list[tuple[datetime, dict]] = []
        for report in self.list_reports():
            status = (report.get("status") or "").lower()
            if status in ("error", "failed"):
                continue

            if self._report_brt_date(report.get("begin_date")) != target_begin:
                continue
            if self._report_brt_date(report.get("end_date")) != target_end:
                continue

            created_raw = report.get("date_created")
            try:
                created_dt = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
            except Exception:
                continue

            if now_utc - created_dt > timedelta(hours=max_age_hours):
                continue

            candidates.append((created_dt, report))

        if not candidates:
            return None

        # Mais recente primeiro
        candidates.sort(key=lambda c: c[0], reverse=True)
        return candidates[0][1]

    def download_report(self, file_name: str) -> str:
        """
        Baixa o conteúdo CSV de um relatório.

        Args:
            file_name: Nome do arquivo retornado pela API.

        Returns:
            Conteúdo CSV como string.
        """
        logger.info(f"Baixando relatório: {file_name}")
        return self._request("GET", f"/{file_name}", accept_text=True)

    def wait_for_report_ready(self, report_id: int | str) -> str | None:
        """
        Aguarda até o relatório estar pronto (polling por ID).

        O POST /settlement_report retorna status 'pending' e file_name null.
        Precisamos esperar o processamento terminar para obter o file_name.

        Args:
            report_id: ID do relatório retornado pelo POST.

        Returns:
            file_name quando pronto, ou None se timeout/error.
        """
        elapsed = 0
        interval = MPConfig.POLL_INTERVAL_SECONDS
        max_wait = MPConfig.POLL_MAX_WAIT_SECONDS

        logger.info(f"Aguardando relatório id={report_id} (max {max_wait}s)...")

        while elapsed < max_wait:
            report = self.find_report_by_id(report_id)

            if report:
                status = report.get("status", "unknown")
                file_name = report.get("file_name")

                logger.info(f"  [{elapsed}s] status={status}, file_name={file_name}")

                # Readiness robusto: file_name preenchido = relatório pronto,
                # independentemente do rótulo de status (o MP usa variações como
                # "pending", "PENDING-YUL", "processed", "ready", etc.).
                if file_name:
                    logger.info(f"Relatório pronto após {elapsed}s: {file_name} (status={status})")
                    return file_name

                if str(status).lower() in ("error", "failed"):
                    logger.error(f"Relatório com erro de processamento (status={status}).")
                    return None
            else:
                logger.warning(f"  [{elapsed}s] Relatório id={report_id} não encontrado na lista.")

            time.sleep(interval)
            elapsed += interval

        logger.error(f"Timeout: relatório não ficou pronto em {max_wait}s.")
        return None

    # =============================================
    # Schedule (geração automática)
    # =============================================

    # =============================================
    # Payments API (enrichment)
    # =============================================

    def get_payment_detail(self, payment_id: str) -> dict | None:
        """
        Busca detalhes de um pagamento pela Payments API.

        Endpoint: GET /v1/payments/{id}
        Usado para enriquecer transações com descrição do pagamento.

        Args:
            payment_id: ID do pagamento (source_id do settlement).

        Returns:
            Dict com description e payer info, ou None se não encontrado.
        """
        try:
            url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
            headers = {**self.headers}
            response = requests.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                payer = data.get("payer", {})
                fname = payer.get("first_name") or ""
                lname = payer.get("last_name") or ""
                payer_name = f"{fname} {lname}".strip() or None

                return {
                    "description": data.get("description"),
                    "payer_name": payer_name,
                    "payer_email": payer.get("email"),
                }

            if response.status_code == 404:
                return None

            logger.warning(f"Payment detail {payment_id}: HTTP {response.status_code}")
            return None

        except Exception as e:
            logger.warning(f"Erro ao buscar payment {payment_id}: {e}")
            return None

    def enrich_transactions(self, source_ids: list[str]) -> dict[str, str]:
        """
        Busca descrição para múltiplos pagamentos.

        Filtra automaticamente para não fazer chamadas desnecessárias.

        Args:
            source_ids: Lista de source_ids para buscar.

        Returns:
            Dict {source_id: description} para os que retornaram dados.
        """
        enrichments: dict[str, str] = {}

        for sid in source_ids:
            if not sid:
                continue

            detail = self.get_payment_detail(sid)
            if detail and detail.get("description"):
                enrichments[sid] = detail["description"]
                logger.info(f"  Enriched {sid}: {detail['description']}")

        logger.info(f"Enrichment: {len(enrichments)}/{len(source_ids)} transações enriquecidas.")
        return enrichments

    # =============================================
    # Schedule (geração automática)
    # =============================================

    def enable_schedule(self) -> dict:
        """Ativa geração automática de relatórios."""
        logger.info("Ativando schedule de relatórios...")
        return self._request("POST", "/schedule")

    def disable_schedule(self) -> dict:
        """Desativa geração automática de relatórios."""
        logger.info("Desativando schedule de relatórios...")
        return self._request("DELETE", "/schedule")

    # =============================================
    # CSV Parsing
    # =============================================

    @staticmethod
    def parse_settlement_csv(csv_content: str) -> pd.DataFrame:
        """
        Parseia o CSV do Settlement Report do Mercado Pago.

        O CSV do MP pode ter linhas de cabeçalho/rodapé extras que
        precisam ser ignoradas. As colunas relevantes são mapeadas
        para os nomes da tabela `transactions`.

        Args:
            csv_content: Conteúdo CSV como string.

        Returns:
            DataFrame limpo e tipado pronto para insert.
        """
        logger.info("Parseando CSV do Settlement Report...")

        # Lê o CSV ignorando erros
        # O MP usa ";" como separador — detecta automaticamente
        try:
            # Detecta separador: se a primeira linha tem ";" usa ";", senão ","
            first_line = csv_content.split("\n")[0] if csv_content else ""
            sep = ";" if ";" in first_line else ","

            df = pd.read_csv(
                io.StringIO(csv_content),
                sep=sep,
                encoding="utf-8",
                on_bad_lines="skip",
            )
        except Exception as e:
            logger.error(f"Erro ao ler CSV: {e}")
            return pd.DataFrame()

        if df.empty:
            logger.warning("CSV vazio após parsing.")
            return pd.DataFrame()

        # Normaliza nomes de coluna (upper, strip)
        df.columns = [c.strip().upper() for c in df.columns]

        # Verifica se tem as colunas esperadas
        expected = {"TRANSACTION_DATE", "TRANSACTION_TYPE", "TRANSACTION_AMOUNT", "SETTLEMENT_NET_AMOUNT"}
        present = set(df.columns)
        missing = expected - present

        if missing:
            logger.error(f"Colunas ausentes no CSV: {missing}. Presentes: {present}")
            return pd.DataFrame()

        # Filtra apenas linhas com TRANSACTION_TYPE válido
        valid_types = {"SETTLEMENT", "REFUND", "PAYOUTS"}
        df = df[df["TRANSACTION_TYPE"].isin(valid_types)].copy()

        if df.empty:
            logger.warning("Nenhuma transação válida no CSV após filtro de tipo.")
            return pd.DataFrame()

        # Mapeia colunas do CSV para colunas do banco
        column_map = {
            "TRANSACTION_DATE": "transaction_date",
            "SOURCE_ID": "source_id",
            "EXTERNAL_REFERENCE": "external_reference",
            "TRANSACTION_TYPE": "transaction_type",
            "TRANSACTION_AMOUNT": "transaction_amount",
            "TRANSACTION_CURRENCY": "transaction_currency",
            "PAYMENT_METHOD": "payment_method",
            "FEE_AMOUNT": "fee_amount",
            "SETTLEMENT_NET_AMOUNT": "settlement_net_amount",
        }

        # Seleciona apenas colunas presentes
        cols_to_select = [c for c in column_map.keys() if c in df.columns]
        df = df[cols_to_select].rename(columns=column_map)

        # Converte tipos
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        df["transaction_amount"] = pd.to_numeric(df["transaction_amount"], errors="coerce")
        df["settlement_net_amount"] = pd.to_numeric(df["settlement_net_amount"], errors="coerce")

        if "fee_amount" in df.columns:
            df["fee_amount"] = pd.to_numeric(df["fee_amount"], errors="coerce").fillna(0)

        # Preenche colunas faltantes com defaults
        for col in ["source_id", "external_reference", "payment_method"]:
            if col not in df.columns:
                df[col] = ""

        if "transaction_currency" not in df.columns:
            df["transaction_currency"] = "BRL"

        if "fee_amount" not in df.columns:
            df["fee_amount"] = 0

        # Remove linhas com dados essenciais nulos
        df = df.dropna(subset=["transaction_date", "transaction_amount", "settlement_net_amount"])

        # Preenche NaN em strings com vazio
        str_cols = ["source_id", "external_reference", "payment_method", "transaction_currency"]
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)

        logger.info(f"CSV parseado: {len(df)} transações válidas.")
        return df


def get_client() -> MercadoPagoClient:
    """
    Cria um MercadoPagoClient usando o token de st.secrets ou .env.

    Returns:
        MercadoPagoClient configurado.

    Raises:
        RuntimeError: Se o token não for encontrado.
    """
    token = None

    # st.secrets
    try:
        import streamlit as st
        token = st.secrets.get("MP_ACCESS_TOKEN")
    except Exception:
        pass

    # .env
    if not token:
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            token = os.getenv("MP_ACCESS_TOKEN")
        except ImportError:
            pass

    if not token:
        raise RuntimeError(
            "MP_ACCESS_TOKEN não encontrado. "
            "Configure em .streamlit/secrets.toml ou .env."
        )

    return MercadoPagoClient(access_token=token)
