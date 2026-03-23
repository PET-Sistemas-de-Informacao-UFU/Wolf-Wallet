-- =============================================
-- 🐺 Wolf Wallet — Seed Data (Exemplo)
-- PostgreSQL (Supabase)
--
-- Dados de exemplo para quem quiser rodar o projeto localmente.
-- Em produção, os usuários são criados pelo painel admin.
--
-- ⚠️  NÃO commitar senhas ou dados reais aqui!
-- =============================================

-- =============================================
-- EXEMPLO: Criando um admin
-- =============================================
-- Para gerar o hash bcrypt da senha, use Python:
--
--   import bcrypt
--   senha = "SuaSenha@123"
--   hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=12)).decode()
--   print(hash)
--
-- Resultado exemplo para "Admin@123":
--   $2b$12$iNEx9RVRWK0zOVSWC034auOedB.JlnN4j1A6nqNdkLOjO8MV1LBpe

-- INSERT INTO users (name, email, password_hash, role)
-- VALUES (
--     'Nome do Admin',
--     'admin@exemplo.com',
--     '$2b$12$COLE_O_HASH_BCRYPT_AQUI',
--     'admin'
-- );

-- =============================================
-- EXEMPLO: Criando membros (role = 'user')
-- =============================================
-- Hash exemplo para "Membro@123":
--   $2b$12$IaHpVo6.tmNs/1QhkfPcaeXFQPgH6fMIXMj1V9B9KfsbjeYXmofB.

-- INSERT INTO users (name, email, password_hash, role)
-- VALUES
--     ('Ana Silva',    'ana@exemplo.com',    '$2b$12$HASH...', 'user'),
--     ('Bruno Costa',  'bruno@exemplo.com',  '$2b$12$HASH...', 'user'),
--     ('Carla Santos', 'carla@exemplo.com',  '$2b$12$HASH...', 'user')
-- ON CONFLICT (email) DO NOTHING;

-- =============================================
-- EXEMPLO: Forçando troca de senha no primeiro login
-- =============================================
-- UPDATE users SET must_change_password = true
-- WHERE email IN ('ana@exemplo.com', 'bruno@exemplo.com');
