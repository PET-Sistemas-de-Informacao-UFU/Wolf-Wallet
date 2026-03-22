-- =============================================
-- 🐺 Wolf Wallet — Database Schema
-- PostgreSQL (Supabase)
--
-- Execute este script no SQL Editor do Supabase
-- ou via psql para criar todas as tabelas.
-- =============================================

-- =============================================
-- EXTENSÕES
-- =============================================
-- Necessária para uuid_generate_v4() nos tokens
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- =============================================
-- 1. USERS — Usuários do sistema
-- =============================================
-- Armazena todos os membros do PET-SI com acesso ao Wolf Wallet.
-- Roles: 'admin' (2 pessoas) ou 'user' (12 pessoas).
-- Soft delete via is_active = false.

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    email           VARCHAR(150)    UNIQUE NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    role            VARCHAR(10)     NOT NULL CHECK (role IN ('admin', 'user')),
    is_active       BOOLEAN         DEFAULT true,
    created_at      TIMESTAMP       DEFAULT NOW(),
    updated_at      TIMESTAMP       DEFAULT NOW()
);

-- Index para buscas por email (login)
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- Index para filtrar usuários ativos
CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active) WHERE is_active = true;

COMMENT ON TABLE  users IS 'Membros do PET-SI com acesso ao Wolf Wallet';
COMMENT ON COLUMN users.role IS 'Papel do usuário: admin (gerencia tudo) ou user (somente visualização)';
COMMENT ON COLUMN users.is_active IS 'Soft delete — false significa conta desativada';


-- =============================================
-- 2. PASSWORD_RESET_TOKENS — Tokens de redefinição de senha
-- =============================================
-- Gerados quando o usuário solicita "Esqueci minha senha".
-- Expiram após 30 minutos. Marcados como used após utilização.

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(255)    UNIQUE NOT NULL,
    expires_at      TIMESTAMP       NOT NULL,
    used            BOOLEAN         DEFAULT false,
    created_at      TIMESTAMP       DEFAULT NOW()
);

-- Index para busca rápida por token (validação do link)
CREATE INDEX IF NOT EXISTS idx_reset_tokens_token ON password_reset_tokens (token);

-- Index para limpeza de tokens expirados
CREATE INDEX IF NOT EXISTS idx_reset_tokens_expires ON password_reset_tokens (expires_at)
    WHERE used = false;

COMMENT ON TABLE  password_reset_tokens IS 'Tokens temporários para redefinição de senha via email';
COMMENT ON COLUMN password_reset_tokens.expires_at IS 'Token expira 30 minutos após criação';


-- =============================================
-- 3. TRANSACTIONS — Transações do Mercado Pago
-- =============================================
-- Dados sincronizados da API Settlement Report do Mercado Pago.
-- Fonte única de verdade financeira do sistema.
-- A constraint UNIQUE evita inserção de duplicatas durante re-syncs.

CREATE TABLE IF NOT EXISTS transactions (
    id                      SERIAL PRIMARY KEY,
    source_id               VARCHAR(50),
    external_reference      VARCHAR(100),
    payment_method          VARCHAR(50),
    transaction_type        VARCHAR(30)     NOT NULL,
    transaction_amount      DECIMAL(12,2)   NOT NULL,
    transaction_currency    VARCHAR(5)      DEFAULT 'BRL',
    transaction_date        TIMESTAMP       NOT NULL,
    fee_amount              DECIMAL(12,2)   DEFAULT 0,
    settlement_net_amount   DECIMAL(12,2)   NOT NULL,
    synced_at               TIMESTAMP       DEFAULT NOW(),

    -- Evita duplicatas: mesma transação não é inserida duas vezes
    UNIQUE(source_id, transaction_type, transaction_amount, transaction_date)
);

-- Index principal: consultas por período (dashboard, extrato, gráficos)
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions (transaction_date DESC);

-- Index para filtros por tipo de transação
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions (transaction_type);

-- Index para filtros por método de pagamento
CREATE INDEX IF NOT EXISTS idx_transactions_method ON transactions (payment_method);

-- Index composto para relatórios mensais (entradas vs saídas)
CREATE INDEX IF NOT EXISTS idx_transactions_date_type ON transactions (transaction_date, transaction_type);

COMMENT ON TABLE  transactions IS 'Transações sincronizadas da API Settlement Report do Mercado Pago';
COMMENT ON COLUMN transactions.source_id IS 'ID único da transação no Mercado Pago';
COMMENT ON COLUMN transactions.transaction_type IS 'SETTLEMENT (liquidação), REFUND (devolução), PAYOUTS (saque)';
COMMENT ON COLUMN transactions.transaction_amount IS 'Valor bruto — positivo = entrada, negativo = saída';
COMMENT ON COLUMN transactions.settlement_net_amount IS 'Valor líquido após taxas';
COMMENT ON COLUMN transactions.fee_amount IS 'Taxa cobrada pelo Mercado Pago';


-- =============================================
-- 4. MONTHLY_BILLS — Contas mensais/recorrentes
-- =============================================
-- Cadastradas manualmente pelo admin.
-- Podem ser mensais (monthly) ou temporárias (temporary) com data de fim.

CREATE TABLE IF NOT EXISTS monthly_bills (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    description     TEXT,
    amount          DECIMAL(12,2)   NOT NULL CHECK (amount > 0),
    due_day         INTEGER         CHECK (due_day BETWEEN 1 AND 31),
    recurrence      VARCHAR(20)     DEFAULT 'monthly'
                                    CHECK (recurrence IN ('monthly', 'temporary')),
    start_date      DATE            NOT NULL,
    end_date        DATE,
    is_active       BOOLEAN         DEFAULT true,
    created_by      INTEGER         REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMP       DEFAULT NOW(),

    -- Se recurrence = 'temporary', end_date é obrigatória
    CONSTRAINT chk_temporary_end_date CHECK (
        recurrence != 'temporary' OR end_date IS NOT NULL
    ),
    -- end_date deve ser posterior a start_date
    CONSTRAINT chk_date_range CHECK (
        end_date IS NULL OR end_date >= start_date
    )
);

-- Index para buscar contas ativas (dashboard, alertas)
CREATE INDEX IF NOT EXISTS idx_bills_active ON monthly_bills (is_active)
    WHERE is_active = true;

-- Index para alertas de vencimento
CREATE INDEX IF NOT EXISTS idx_bills_due_day ON monthly_bills (due_day)
    WHERE is_active = true;

COMMENT ON TABLE  monthly_bills IS 'Contas mensais/recorrentes cadastradas manualmente pelo admin';
COMMENT ON COLUMN monthly_bills.due_day IS 'Dia do mês em que a conta vence (1-31)';
COMMENT ON COLUMN monthly_bills.recurrence IS 'monthly = permanente, temporary = período determinado';


-- =============================================
-- 5. BILL_PAYMENTS — Registro de pagamento de contas
-- =============================================
-- Um registro por conta por mês.
-- O admin marca como pago quando o pagamento é efetuado.

CREATE TABLE IF NOT EXISTS bill_payments (
    id              SERIAL PRIMARY KEY,
    bill_id         INTEGER         NOT NULL REFERENCES monthly_bills(id) ON DELETE CASCADE,
    reference_month DATE            NOT NULL,
    paid            BOOLEAN         DEFAULT false,
    paid_at         TIMESTAMP,
    paid_by         INTEGER         REFERENCES users(id) ON DELETE SET NULL,
    notes           TEXT,

    -- Apenas um registro por conta por mês
    UNIQUE(bill_id, reference_month)
);

-- Index para consultas mensais
CREATE INDEX IF NOT EXISTS idx_bill_payments_month ON bill_payments (reference_month);

-- Index para buscar pagamentos por conta
CREATE INDEX IF NOT EXISTS idx_bill_payments_bill ON bill_payments (bill_id);

COMMENT ON TABLE  bill_payments IS 'Registro mensal de pagamento das contas cadastradas';
COMMENT ON COLUMN bill_payments.reference_month IS 'Primeiro dia do mês de referência (ex: 2026-03-01)';


-- =============================================
-- 6. MEMBER_CONTRIBUTIONS — Contribuições mensais
-- =============================================
-- Controle de quem pagou a contribuição mensal de R$ 10,00.
-- Status: pending (aguardando), paid (confirmado pelo admin), late (atrasado).

CREATE TABLE IF NOT EXISTS member_contributions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reference_month DATE            NOT NULL,
    expected_amount DECIMAL(12,2)   NOT NULL CHECK (expected_amount > 0),
    status          VARCHAR(15)     DEFAULT 'pending'
                                    CHECK (status IN ('pending', 'paid', 'late')),
    confirmed_by    INTEGER         REFERENCES users(id) ON DELETE SET NULL,
    confirmed_at    TIMESTAMP,
    notes           TEXT,

    -- Apenas uma contribuição por membro por mês
    UNIQUE(user_id, reference_month)
);

-- Index para consultas mensais (quadro de contribuições)
CREATE INDEX IF NOT EXISTS idx_contributions_month ON member_contributions (reference_month);

-- Index para filtrar por status (dashboard: pendentes/atrasados)
CREATE INDEX IF NOT EXISTS idx_contributions_status ON member_contributions (status)
    WHERE status != 'paid';

-- Index para consultas por membro
CREATE INDEX IF NOT EXISTS idx_contributions_user ON member_contributions (user_id);

COMMENT ON TABLE  member_contributions IS 'Controle mensal de contribuições dos membros do PET-SI';
COMMENT ON COLUMN member_contributions.status IS 'pending = aguardando, paid = confirmado, late = atrasado';
COMMENT ON COLUMN member_contributions.confirmed_by IS 'ID do admin que confirmou o pagamento';


-- =============================================
-- 7. SYNC_LOG — Log de sincronização com a API
-- =============================================
-- Registra cada execução do job de sincronização com o Mercado Pago.
-- Usado para: determinar a última data sincronizada, debug de erros.

CREATE TABLE IF NOT EXISTS sync_log (
    id              SERIAL PRIMARY KEY,
    sync_date       TIMESTAMP       DEFAULT NOW(),
    records_added   INTEGER         DEFAULT 0,
    status          VARCHAR(20)     NOT NULL CHECK (status IN ('success', 'error')),
    error_message   TEXT,
    begin_date      TIMESTAMP,
    end_date        TIMESTAMP,

    -- begin_date não pode ser posterior a end_date
    CONSTRAINT chk_sync_date_range CHECK (
        begin_date IS NULL OR end_date IS NULL OR begin_date <= end_date
    )
);

-- Index para buscar a última sync (ORDER BY sync_date DESC LIMIT 1)
CREATE INDEX IF NOT EXISTS idx_sync_log_date ON sync_log (sync_date DESC);

COMMENT ON TABLE  sync_log IS 'Log de cada execução do job de sincronização com o Mercado Pago';
COMMENT ON COLUMN sync_log.records_added IS 'Quantidade de novas transações inseridas nesta sync';
COMMENT ON COLUMN sync_log.begin_date IS 'Início do período consultado na API';
COMMENT ON COLUMN sync_log.end_date IS 'Fim do período consultado na API';


-- =============================================
-- TRIGGER: Atualizar updated_at automaticamente
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- =============================================
-- FIM DO SCHEMA
-- =============================================
-- Após executar este script, todas as tabelas estarão prontas.
-- Próximo passo: executar sql/seed.sql para inserir dados iniciais.
