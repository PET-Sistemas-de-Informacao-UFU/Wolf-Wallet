-- =============================================
-- 🐺 Wolf Wallet — Seed Data
-- PostgreSQL (Supabase)
--
-- Dados iniciais para desenvolvimento e teste.
-- Senhas hash bcrypt (rounds=12):
--   "Admin@123" → hash abaixo
--   "Membro@123" → hash abaixo
--
-- IMPORTANTE: Alterar senhas em produção!
-- =============================================

-- =============================================
-- ADMINS (2)
-- =============================================
-- Senha padrão: Admin@123
INSERT INTO users (name, email, password_hash, role)
VALUES
    (
        'Administrador 1',
        'admin1@wolfwallet.com',
        '$2b$12$iNEx9RVRWK0zOVSWC034auOedB.JlnN4j1A6nqNdkLOjO8MV1LBpe',
        'admin'
    ),
    (
        'Administrador 2',
        'admin2@wolfwallet.com',
        '$2b$12$iNEx9RVRWK0zOVSWC034auOedB.JlnN4j1A6nqNdkLOjO8MV1LBpe',
        'admin'
    )
ON CONFLICT (email) DO NOTHING;

-- =============================================
-- MEMBROS (12) — Nomes fictícios para dev
-- =============================================
-- Senha padrão: Membro@123
INSERT INTO users (name, email, password_hash, role)
VALUES
    ('Ana Silva', 'ana.silva@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Bruno Costa', 'bruno.costa@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Carla Oliveira', 'carla.oliveira@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Daniel Santos', 'daniel.santos@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Elena Pereira', 'elena.pereira@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Felipe Lima', 'felipe.lima@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Gabriela Souza', 'gabriela.souza@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Henrique Martins', 'henrique.martins@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Isabela Rocha', 'isabela.rocha@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('João Ferreira', 'joao.ferreira@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Karen Almeida', 'karen.almeida@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user'),
    ('Lucas Ribeiro', 'lucas.ribeiro@wolfwallet.com', '$2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.', 'user')
ON CONFLICT (email) DO NOTHING;
