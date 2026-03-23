"""
🐺 Wolf Wallet — Application Settings & Constants

Centraliza todas as constantes, cores e configurações do sistema.
Nenhum valor "mágico" deve existir fora deste arquivo.

Usage:
    from config.settings import Settings, Colors, Messages
"""

from decimal import Decimal


# =============================================
# Application Metadata
# =============================================
class App:
    """Metadados gerais da aplicação."""

    NAME: str = "Wolf Wallet"
    EMOJI: str = "🐺"
    TITLE: str = f"{NAME}"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "Carteira virtual do PET-SI — UFU. "
        "Visualize as movimentações financeiras da conta compartilhada "
        "de forma transparente e automatizada."
    )
    AUTHOR: str = "PET-SI — Universidade Federal de Uberlândia"
    REPO_URL: str = "https://github.com/pet-si-ufu/wolf-wallet"


# =============================================
# Financial Settings
# =============================================
class Finance:
    """Constantes financeiras do projeto."""

    # Moeda padrão
    CURRENCY: str = "BRL"
    CURRENCY_SYMBOL: str = "R$"
    CURRENCY_LOCALE: str = "pt_BR"

    # Limiar para identificar rendimentos CDI (valores < este threshold)
    YIELD_THRESHOLD: Decimal = Decimal("5.00")

    # Máscara para valores ocultos
    HIDDEN_VALUE: str = "R$ ••••••"


# =============================================
# UI / UX Settings
# =============================================
class UI:
    """Constantes de interface e experiência do usuário."""

    # Paginação
    ITEMS_PER_PAGE: int = 20

    # Alertas de contas — dias antes do vencimento
    BILL_ALERT_DAYS: int = 5

    # Feed de atividades recentes — quantidade de itens
    RECENT_ACTIVITIES_LIMIT: int = 10

    # Períodos padrão para gráficos
    CHART_PERIODS: dict[str, int] = {
        "3 meses": 3,
        "6 meses": 6,
        "12 meses": 12,
    }

    # Layout padrão
    LAYOUT: str = "wide"

    # Ícones das seções
    ICONS: dict[str, str] = {
        "dashboard": "🏠",
        "extrato": "📋",
        "rendimentos": "📈",
        "contas": "💳",
        "admin_usuarios": "👤",
        "admin_sync": "🔄",
        "saldo": "💰",
        "entradas": "📥",
        "saidas": "📤",
        "rendimento": "📈",
        "alerta": "⚠️",
        "sucesso": "✅",
        "pendente": "⏳",
        "atrasado": "🔴",
    }


# =============================================
# Theme Colors
# =============================================
class Colors:
    """Paleta de cores do projeto (conforme spec seção 10)."""

    # Semânticas
    POSITIVE: str = "#00C853"       # Entradas / Verde
    NEGATIVE: str = "#FF1744"       # Saídas / Vermelho
    NEUTRAL: str = "#2979FF"        # Saldo / Azul
    YIELD: str = "#FFD600"          # Rendimentos / Dourado
    ALERT: str = "#FF9100"          # Alertas / Laranja

    # Backgrounds (tema escuro)
    BG_DARK: str = "#0E1117"
    BG_CARD_DARK: str = "#1E1E2E"

    # Backgrounds (tema claro)
    BG_LIGHT: str = "#FFFFFF"
    BG_CARD_LIGHT: str = "#F8F9FA"

    # Texto
    TEXT_PRIMARY: str = "#FAFAFA"
    TEXT_SECONDARY: str = "#B0B0B0"
    TEXT_DARK: str = "#1A1A2E"


# =============================================
# Authentication & Security
# =============================================
class Auth:
    """Constantes de autenticação e segurança."""

    # Expiração do token de redefinição de senha (minutos)
    TOKEN_EXPIRATION_MINUTES: int = 30

    # Tamanho da senha temporária gerada
    TEMP_PASSWORD_LENGTH: int = 12

    # Requisitos de senha
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_DIGIT: bool = True

    # bcrypt rounds (custo do hashing)
    BCRYPT_ROUNDS: int = 12

    # Delay após tentativa de login falha (segundos) — anti brute-force
    FAILED_LOGIN_DELAY: float = 1.0

    # Roles válidos
    ROLES: list[str] = ["admin", "user"]


# =============================================
# Mercado Pago API
# =============================================
class MercadoPago:
    """Constantes da integração com a API do Mercado Pago."""

    BASE_URL: str = "https://api.mercadopago.com/v1/account/settlement_report"

    # Timeout para requisições HTTP (segundos)
    REQUEST_TIMEOUT: int = 30

    # Retry
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0

    # Polling para aguardar processamento do relatório
    POLL_INTERVAL_SECONDS: int = 10
    POLL_MAX_WAIT_SECONDS: int = 600  # 10 minutos

    # Configuração do relatório
    FILE_NAME_PREFIX: str = "extrato-projeto"
    TIMEZONE: str = "GMT-03"
    HEADER_LANGUAGE: str = "pt"

    # Métodos de pagamento EXCLUÍDOS da importação:
    # master, visa, amex, elo, hipercard, diners, debit_card, credit_card
    # Motivo: a API Settlement inclui compras pessoais com cartão vinculado
    # à conta MP, que não pertencem ao caixa do PET-SI.

    # Colunas esperadas no CSV
    CSV_COLUMNS: list[str] = [
        "TRANSACTION_DATE",
        "SOURCE_ID",
        "EXTERNAL_REFERENCE",
        "TRANSACTION_TYPE",
        "TRANSACTION_AMOUNT",
        "TRANSACTION_CURRENCY",
        "PAYMENT_METHOD",
        "FEE_AMOUNT",
        "SETTLEMENT_NET_AMOUNT",
    ]


# =============================================
# Email (Gmail SMTP)
# =============================================
class Email:
    """Constantes do serviço de email."""

    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    USE_TLS: bool = True

    # Remetente (display name)
    FROM_NAME: str = "Wolf Wallet — PET-SI"

    # Limite diário do Gmail (free tier)
    DAILY_LIMIT: int = 500


# =============================================
# Database
# =============================================
class Database:
    """Constantes de configuração do banco de dados."""

    # Connection pool
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_TIMEOUT: int = 30  # segundos
    POOL_RECYCLE: int = 1800  # 30 minutos — evita conexões stale


# =============================================
# Session State Keys
# =============================================
class SessionKeys:
    """
    Chaves usadas no st.session_state.

    Centralizar aqui evita typos e facilita refatorações.
    """

    AUTHENTICATED: str = "authenticated"
    USER: str = "user"
    ROLE: str = "role"
    IS_VISITOR: str = "is_visitor"
    HIDE_BALANCE: str = "hide_balance"
    CURRENT_PAGE: str = "current_page"
    THEME: str = "theme"
    MUST_CHANGE_PASSWORD: str = "must_change_password"


# =============================================
# Page Routes
# =============================================
class Pages:
    """Identificadores das páginas para roteamento."""

    LOGIN: str = "login"
    HOME: str = "home"
    EXTRATO: str = "extrato"
    RENDIMENTOS: str = "rendimentos"
    CONTAS: str = "contas"
    ADMIN_USUARIOS: str = "admin_usuarios"
    ADMIN_SYNC: str = "admin_sync"

    # Páginas acessíveis por visitantes
    VISITOR_PAGES: list[str] = [HOME]

    # Páginas que requerem admin
    ADMIN_PAGES: list[str] = [ADMIN_USUARIOS, ADMIN_SYNC]

    # Todas as páginas que requerem login
    AUTH_PAGES: list[str] = [
        HOME, EXTRATO, RENDIMENTOS,
        CONTAS,
        ADMIN_USUARIOS, ADMIN_SYNC,
    ]


# =============================================
# Messages (PT-BR)
# =============================================
class Messages:
    """Mensagens padronizadas exibidas na interface."""

    # Login
    LOGIN_SUCCESS: str = "Login realizado com sucesso!"
    LOGIN_FAILED: str = "Email ou senha incorretos."
    LOGIN_INACTIVE: str = "Sua conta foi desativada. Entre em contato com um administrador."
    LOGOUT_SUCCESS: str = "Você saiu da sua conta."

    # Visitante
    VISITOR_BANNER: str = (
        "🔍 Você está no modo visitante. "
        "Os dados exibidos são fictícios para demonstração."
    )

    # Senhas
    PASSWORD_RESET_SENT: str = "Email de redefinição enviado! Verifique sua caixa de entrada."
    PASSWORD_RESET_SUCCESS: str = "Senha alterada com sucesso! Faça login com a nova senha."
    PASSWORD_RESET_EXPIRED: str = "Este link de redefinição expirou. Solicite um novo."
    PASSWORD_RESET_INVALID: str = "Link de redefinição inválido."
    PASSWORD_TOO_SHORT: str = f"A senha deve ter no mínimo {Auth.MIN_PASSWORD_LENGTH} caracteres."
    PASSWORD_NEEDS_UPPERCASE: str = "A senha deve conter pelo menos uma letra maiúscula."
    PASSWORD_NEEDS_DIGIT: str = "A senha deve conter pelo menos um número."

    # Sync
    SYNC_SUCCESS: str = "Sincronização concluída com sucesso!"
    SYNC_ERROR: str = "Erro durante a sincronização. Verifique os logs."
    SYNC_IN_PROGRESS: str = "Sincronização em andamento..."

    # Geral
    NO_DATA: str = "Nenhum dado encontrado para o período selecionado."
    CONFIRM_ACTION: str = "Tem certeza que deseja realizar esta ação?"
    ACTION_SUCCESS: str = "Ação realizada com sucesso!"
    ACTION_ERROR: str = "Ocorreu um erro. Tente novamente."
