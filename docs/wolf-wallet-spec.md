# 🐺 Wolf Wallet — Especificação do Projeto

## 1. Visão Geral

**Wolf Wallet** é uma carteira virtual web desenvolvida em **Streamlit (Python)** que exibe dados financeiros de uma conta do Mercado Pago. O objetivo é permitir que membros de um projeto universitário visualizem, de forma transparente e automatizada, as movimentações financeiras da conta compartilhada — eliminando a necessidade de enviar extratos manualmente.

### Problema
Atualmente, o responsável pela conta precisa baixar o extrato manualmente pelo app do Mercado Pago e enviar no WhatsApp/Teams todo mês. Isso é trabalhoso, propenso a atrasos e pouco transparente.

### Solução
Um site onde todos os membros acessam o dashboard financeiro da conta em tempo real, com histórico completo e gestão de contas a pagar.

---

## 2. Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| **Frontend/Backend** | Streamlit (Python) | Rápido para prototipar, UI elegante, gratuito no Community Cloud |
| **Banco de Dados** | PostgreSQL via Supabase | Gratuito (500MB), persistente, multi-usuário |
| **API Financeira** | Mercado Pago — Settlement Report API v1 | Extrato de transações, saldo, rendimentos |
| **Envio de Email** | Gmail SMTP (smtplib nativo do Python) | Gratuito, 500 emails/dia, suficiente para 14 usuários |
| **Deploy** | Streamlit Community Cloud | Gratuito, deploy direto do GitHub |
| **Controle de versão** | GitHub (repositório privado → público futuramente) | Padrão da indústria |

---

## 3. Arquitetura

```
┌──────────────────────────────────────────────────┐
│               Streamlit Community Cloud           │
│                                                   │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Tela Login  │  │Dashboard │  │  Extrato    │  │
│  │  (auth)      │  │  (home)  │  │  Detalhado  │  │
│  └──────┬───────┘  └────┬─────┘  └──────┬──────┘  │
│         └───────────────┼───────────────┘          │
│                         │                          │
│                  ┌──────▼───────┐                   │
│                  │  Camada de   │                   │
│                  │  Serviços    │                   │
│                  │  (Python)    │                   │
│                  └──┬───────┬──┘                    │
│                     │       │                       │
└────���────────────────┼───────┼───────────────────────┘
                      │       │
            ┌─────────▼──┐ ┌──▼──────────┐
            │  Supabase   │ │ API Mercado │
            │ PostgreSQL  │ │    Pago     │
            │ (dados)     │ │ (sync)      │
            └─────────────┘ └─────────────┘
```

### Fluxo de dados
1. **Sync automática** consulta a API do Mercado Pago (1x por cold start + verificação de freshness a cada page load)
2. Novos dados são salvos no banco Supabase (duplicatas ignoradas via UNIQUE constraint)
3. O frontend **sempre lê do banco**, nunca direto da API
4. Dados históricos ficam permanentemente disponíveis sem necessidade de re-consultar a API

### Keep-alive (GitHub Action)
O Streamlit Community Cloud hiberna o app após ~7 dias de inatividade. Uma GitHub Action (`.github/workflows/keep-alive.yml`) faz ping a cada **3 dias** para manter o app ativo. O cold start provocado pelo ping também dispara a sync automática, mantendo os dados frescos.

---

## 4. Segurança e Credenciais

> ⚠️ O repositório começará privado mas será público futuramente. Nenhuma credencial ou informação sensível está no código-fonte.

### Regras obrigatórias
- Todas as credenciais armazenadas via **`st.secrets`** (Streamlit Secrets) no deploy e **`.env`** no desenvolvimento local
- **`.gitignore`** configurado desde o primeiro commit com: `.env`, `__pycache__/`, `.streamlit/secrets.toml`, `*.csv`, `venv/`
- Senhas de usuários armazenadas com **hash bcrypt** (nunca em texto puro)
- Tokens de redefinição de senha com **expiração de 30 minutos**
- Access Token do Mercado Pago **nunca exposto no frontend**

### Variáveis de ambiente necessárias

```toml
# .streamlit/secrets.toml (local — NÃO vai para o repo)

# Mercado Pago
MP_ACCESS_TOKEN = "APP_USR-..."

# Supabase
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOi..."
DATABASE_URL = "postgresql://user:pass@host:5432/dbname"

# Gmail SMTP (para redefinição de senha)
GMAIL_USER = "wolfwallet.projeto@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"

# App
JWT_SECRET = "chave-secreta-para-tokens"
```

---

## 5. Banco de Dados — Modelagem

### Tabelas

#### `users` — Usuários do sistema
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### `password_reset_tokens` — Tokens de redefinição de senha
```sql
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `transactions` — Transações sincronizadas da API do Mercado Pago
```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(50),
    external_reference VARCHAR(100),
    payment_method VARCHAR(50),
    transaction_type VARCHAR(30) NOT NULL,
    transaction_amount DECIMAL(12,2) NOT NULL,
    transaction_currency VARCHAR(5) DEFAULT 'BRL',
    transaction_date TIMESTAMP NOT NULL,
    fee_amount DECIMAL(12,2) DEFAULT 0,
    settlement_net_amount DECIMAL(12,2) NOT NULL,
    synced_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_id, transaction_type, transaction_amount, transaction_date)
);
```

#### `monthly_bills` — Contas mensais/recorrentes cadastradas manualmente
```sql
CREATE TABLE monthly_bills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    amount DECIMAL(12,2) NOT NULL,
    due_day INTEGER CHECK (due_day BETWEEN 1 AND 31),
    recurrence VARCHAR(20) DEFAULT 'monthly' CHECK (recurrence IN ('monthly', 'temporary')),
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `bill_payments` — Registro de pagamento de contas
```sql
CREATE TABLE bill_payments (
    id SERIAL PRIMARY KEY,
    bill_id INTEGER REFERENCES monthly_bills(id),
    reference_month DATE NOT NULL,
    paid BOOLEAN DEFAULT false,
    paid_at TIMESTAMP,
    paid_by INTEGER REFERENCES users(id),
    notes TEXT,
    UNIQUE(bill_id, reference_month)
);
```

#### `sync_log` — Log de sincronização com a API
```sql
CREATE TABLE sync_log (
    id SERIAL PRIMARY KEY,
    sync_date TIMESTAMP DEFAULT NOW(),
    records_added INTEGER DEFAULT 0,
    status VARCHAR(20) CHECK (status IN ('success', 'error')),
    error_message TEXT,
    begin_date TIMESTAMP,
    end_date TIMESTAMP
);
```

---

## 6. API do Mercado Pago — Integração

### Base URL
```
https://api.mercadopago.com/v1/account/settlement_report
```

### Endpoints utilizados

| Método | Endpoint | Uso |
|---|---|---|
| `GET` | `/config` | Consultar configuração do relatório |
| `PUT` | `/config` | Atualizar configuração |
| `POST` | `/` | Gerar relatório manualmente (por período) |
| `GET` | `/list` | Listar relatórios gerados |
| `GET` | `/:file_name` | Baixar CSV do relatório |
| `POST` | `/schedule` | Ativar geração automática |
| `DELETE` | `/schedule` | Desativar geração automática |

### Configuração ativa do relatório
```json
{
    "file_name_prefix": "extrato-projeto",
    "display_timezone": "GMT-03",
    "header_language": "pt",
    "frequency": {
        "hour": 8,
        "type": "monthly",
        "value": 1
    },
    "columns": [
        { "key": "TRANSACTION_DATE" },
        { "key": "SOURCE_ID" },
        { "key": "EXTERNAL_REFERENCE" },
        { "key": "TRANSACTION_TYPE" },
        { "key": "TRANSACTION_AMOUNT" },
        { "key": "TRANSACTION_CURRENCY" },
        { "key": "PAYMENT_METHOD" },
        { "key": "FEE_AMOUNT" },
        { "key": "SETTLEMENT_NET_AMOUNT" }
    ]
}
```

### Colunas do CSV e seus significados

| Coluna | Tipo | Descrição |
|---|---|---|
| `EXTERNAL_REFERENCE` | String | Referência externa da transação |
| `SOURCE_ID` | String | ID único da transação no Mercado Pago |
| `PAYMENT_METHOD` | String | Método: `pix`, `account_money`, `credit_card`, vazio (rendimento) |
| `TRANSACTION_TYPE` | String | `SETTLEMENT` (liquidação), `REFUND` (devolução), `PAYOUTS` (saque) |
| `TRANSACTION_AMOUNT` | Decimal | Valor bruto. Positivo = entrada, Negativo = saída |
| `TRANSACTION_CURRENCY` | String | Moeda (BRL) |
| `TRANSACTION_DATE` | DateTime | Data/hora no fuso GMT-03 |
| `FEE_AMOUNT` | Decimal | Taxa cobrada pelo Mercado Pago |
| `SETTLEMENT_NET_AMOUNT` | Decimal | Valor líquido efetivamente movimentado |

### Tipos de transação esperados

| Tipo | Descrição | Valor |
|---|---|---|
| `SETTLEMENT` (pix) | Pix recebido | Positivo |
| `SETTLEMENT` (vazio) | Rendimento automático (CDI) | Positivo (pequeno) |
| `SETTLEMENT` (vazio, negativo) | Imposto sobre rendimento (IOF/IR) | Negativo (pequeno) |
| `REFUND` | Devolução de pagamento | Negativo |
| `PAYOUTS` | Saque para conta bancária | Negativo |
| `SETTLEMENT` (available_money) | Transferência interna | Negativo |

### Sincronização diária (job)

```
Fluxo do sync job:
1. Consultar sync_log para pegar a última data sincronizada (end_date)
2. begin_date = 00:00:00 do DIA da última sync (inclusivo, para recapturar
   transações tardias que podem não ter entrado no relatório anterior)
3. end_date = timestamp atual (agora)
4. Se o período > 60 dias (limite da API), dividir em blocos consecutivos de 60 dias
5. Para cada bloco:
   a. Gerar relatório via POST /settlement_report
   b. Aguardar processamento (polling por ID no /list até file_name disponível)
   c. Baixar CSV via GET /:file_name
   d. Parsear com pandas (filtra cartão de crédito e CASHBACK automaticamente)
   e. Inserir novos registros na tabela transactions (ON CONFLICT DO NOTHING)
   f. Enriquecer transações com descrição via GET /v1/payments/:id
6. Registrar no sync_log
```

> **Nota (v1.2.0):** O `begin_date` é propositalmente inclusivo (início do dia da última sync)
> para garantir que transações realizadas no final do dia não sejam perdidas entre syncs.
> Duplicatas são automaticamente ignoradas pela constraint UNIQUE da tabela.

### Rate Limit da API
- **~300 requisições por minuto** (autenticado)
- Para nosso uso (1 sync/dia): **sem risco algum de atingir o limite**

---

## 7. Autenticação e Autorização

### Papéis (roles)

| Role | Permissões |
|---|---|
| **admin** (2 pessoas) | Tudo: criar/editar/remover usuários, gerenciar contas, disparar sync manual, visualizar tudo |
| **user** (12 pessoas) | Visualizar dashboard, extrato, contas. Não pode criar usuários nem editar dados |
| **visitante** (sem login) | Tela pública com explicação do projeto + dados mockados para demonstração |

### Fluxo de autenticação

```
Tela de Login
├── [Email + Senha] → Valida hash bcrypt → Gera sessão → Dashboard
├── [Esqueci minha senha] → Digita email → Recebe link por email → Redefine senha
└── [Entrar como Visitante] → Dashboard com dados mockados (modo demo)
```

### Fluxo "Esqueci minha senha"

```
1. Usuário clica "Esqueci minha senha"
2. Digita o email cadastrado
3. Sistema verifica se email existe na tabela users
4. Gera token aleatório (uuid4) com expiração de 30 minutos
5. Salva na tabela password_reset_tokens
6. Envia email via Gmail SMTP com link:
   https://wolf-wallet.streamlit.app/?reset_token=TOKEN_AQUI
7. Usuário clica no link → tela para digitar nova senha
8. Sistema valida o token (existe, não expirou, não foi usado)
9. Atualiza password_hash do usuário
10. Marca token como usado
```

### Configuração do Gmail SMTP
- Criar email do projeto: `wolfwallet.projeto@gmail.com`
- Ativar verificação em 2 etapas
- Gerar senha de app em: https://myaccount.google.com/apppasswords
- Armazenar credenciais no `st.secrets`

---

## 8. Telas e Funcionalidades

### 8.1 Tela de Login (`/`)

**Acesso:** Público

| Elemento | Descrição |
|---|---|
| Logo/Título | "🐺 Wolf Wallet" com branding do projeto |
| Descrição do projeto | Texto explicando o que é, para quem é, e como funciona |
| Campo email | Input de email |
| Campo senha | Input de senha (com ícone de olho para mostrar/ocultar) |
| Botão "Entrar" | Autentica e redireciona para o dashboard |
| Link "Esqueci minha senha" | Abre fluxo de redefinição por email |
| Botão "Entrar como Visitante" | Acessa o dashboard com dados mockados |
| **Não tem** "Criar conta" | Apenas admins criam contas |

---

### 8.2 Dashboard / Home (`/home`)

**Acesso:** Logado (user/admin) ou Visitante (dados mockados)

#### Cards principais (topo)
| Card | Dado | Ícone |
|---|---|---|
| **Saldo Atual** | Soma líquida de todas as transações | 💰 |
| **Entradas do Mês** | Soma de TRANSACTION_AMOUNT > 0 do mês atual | 📥 |
| **Saídas do Mês** | Soma de TRANSACTION_AMOUNT < 0 do mês atual | 📤 |
| **Rendimentos do Mês** | Soma dos rendimentos (CDI) do mês | 📈 |

> Todos os cards devem ter o botão **"ocultar saldo"** (ícone de olho 👁️) que substitui os valores por `R$ ••••••`. O estado deve ser global (um clique oculta todos).

#### Gráfico de Entradas vs Saídas
- Gráfico de barras agrupadas por mês
- Eixo X: meses
- Eixo Y: valores (R$)
- Duas séries: Entradas (verde) e Saídas (vermelho)
- Filtro de período (últimos 3, 6, 12 meses ou personalizado)

#### Feed de Atividades Recentes
Últimas 10 movimentações, estilo feed:
```
📥 25/03 — Pix recebido: R$ 10,00
📥 25/03 — Pix recebido: R$ 20,00
📤 24/03 — Saque para conta bancária: R$ 500,00
📈 24/03 — Rendimento CDI: R$ 0,79
⚠️ 28/03 — Conta "Servidor" vence em 3 dias (R$ 50,00)
```

#### Alertas de Contas Próximas do Vencimento
- Exibe contas da tabela `monthly_bills` cujo `due_day` está nos próximos 5 dias
- Ícone de alerta ⚠️ com destaque visual

---

### 8.3 Extrato Detalhado (`/extrato`)

**Acesso:** Logado (user/admin)

| Funcionalidade | Descrição |
|---|---|
| **Tabela completa** | Todas as transações da tabela `transactions`, paginada |
| **Filtro por período** | Selecionar data início e data fim |
| **Filtro por tipo** | SETTLEMENT, REFUND, PAYOUTS |
| **Filtro por método** | Pix, account_money, credit_card, etc. |
| **Filtro por direção** | Entradas, Saídas ou Todos |
| **Busca** | Campo de busca por `source_id` ou `external_reference` |
| **Exportar** | Botão para baixar a visualização atual em CSV ou Excel |
| **Totais** | Rodapé com soma de entradas, saídas e líquido do período filtrado |

---

### 8.4 Rendimentos (`/rendimentos`)

**Acesso:** Logado (user/admin)

| Funcionalidade | Descrição |
|---|---|
| **Total acumulado** | Soma de todos os rendimentos desde o início |
| **Rendimento do mês** | Valor rendido no mês atual |
| **Gráfico de linha** | Rendimento líquido (rendimento - imposto) por mês |
| **Tabela detalhada** | Lista diária de rendimentos com: data, bruto, imposto, líquido |

> Rendimentos são identificados por: `TRANSACTION_TYPE = 'SETTLEMENT'`, `PAYMENT_METHOD` vazio, valores pequenos (< R$ 5,00), sempre em pares (positivo = rendimento, negativo = imposto).

---

### 8.5 Contas Mensais (`/contas`)

**Acesso:** Admin (gerenciar) / User (visualizar)

#### Cadastro de contas (admin)
| Campo | Tipo | Descrição |
|---|---|---|
| Nome | String | Ex: "Servidor AWS", "Domínio .com.br" |
| Descrição | Text | Detalhes opcionais |
| Valor | Decimal | Valor mensal |
| Dia de vencimento | Integer (1-31) | Dia do mês |
| Recorrência | Select | `monthly` (mensal) ou `temporary` (período determinado) |
| Data início | Date | Quando começou |
| Data fim | Date (opcional) | Só para `temporary` |

#### Visão geral (todos)
| Funcionalidade | Descrição |
|---|---|
| Lista de contas ativas | Nome, valor, vencimento, status do mês atual (pago/pendente) |
| Total mensal | Soma de todas as contas ativas |
| Próximos vencimentos | Destacar contas que vencem nos próximos 5 dias |
| Histórico | Admin pode marcar contas como pagas por mês |

---

### 8.7 Gerenciamento de Usuários (`/admin/usuarios`)

**Acesso:** Somente Admin

| Funcionalidade | Descrição |
|---|---|
| **Lista de usuários** | Tabela com: nome, email, role, status (ativo/inativo), data de criação |
| **Criar usuário** | Formulário: nome, email, role (user/admin), senha temporária |
| **Editar usuário** | Alterar nome, email, role |
| **Desativar usuário** | Soft delete (marca `is_active = false`) — não deleta |
| **Resetar senha** | Gera nova senha temporária e envia por email |

> Ao criar um usuário, o sistema envia um email de boas-vindas com a senha temporária e instruções para trocar.

---

### 8.8 Painel de Sincronização (`/admin/sync`)

**Acesso:** Somente Admin

| Funcionalidade | Descrição |
|---|---|
| **Banner de status** | Exibido no topo — mostra última sync (data, registros) ou progresso em tempo real se rodando |
| **Status da última sync** | Data, quantidade de registros, status (sucesso/erro) |
| **Histórico de syncs** | Tabela com log de todas as sincronizações |
| **Botão "Sincronizar agora"** | Dispara sync manual sob demanda (mostra período inclusivo que será sincronizado) |
| **Configuração** | Visualizar configuração atual do relatório na API do MP |

> **Banner de status (v1.2.0):** O mesmo banner também aparece no Dashboard e no Extrato.
> Durante uma sync em andamento, exibe as etapas intermediárias em tempo real
> ("Conectando API...", "Baixando CSV...", etc.) com um expander de log detalhado.

---

## 9. Dados Mockados (Modo Visitante)

O modo visitante deve exibir o dashboard completo com dados fictícios para fins de demonstração. Os dados mockados devem:

- Simular 6 meses de histórico
- Conter transações variadas: Pix recebidos, saques, rendimentos, devoluções
- Ter nomes fictícios nos membros
- Ser carregados de um arquivo JSON ou gerados em código (não do banco)
- Exibir um banner informando: "🔍 Você está no modo visitante. Os dados exibidos são fictícios para demonstração."

---

## 10. UX/UI — Diretrizes de Design

### Tema e Cores
| Elemento | Cor |
|---|---|
| Entradas / Positivo | Verde (`#00C853`) |
| Saídas / Negativo | Vermelho (`#FF1744`) |
| Saldo / Neutro | Azul (`#2979FF`) |
| Rendimentos | Amarelo/Dourado (`#FFD600`) |
| Alertas | Laranja (`#FF9100`) |
| Background | Tema escuro e claro (toggle) |

### Padrões de UX
- **Botão de ocultar saldo** (ícone 👁️) global no topo — um clique oculta todos os valores financeiros em todas as telas
- **Tema escuro/claro** com toggle no sidebar
- **Sidebar** com navegação entre as telas
- **Responsivo** para funcionar em mobile (membros podem acessar pelo celular)
- **Loading states** com spinners durante carregamento de dados
- **Mensagens de sucesso/erro** com `st.success()`, `st.error()`, `st.warning()`
- **Confirmação** antes de ações destrutivas (desativar usuário, etc.)
- **Banner de sincronização** no topo do Dashboard, Extrato e Sync — mostra última sync (✅/❌) ou progresso em tempo real (🔄 com etapas detalhadas)

---

## 11. Estrutura de Arquivos do Projeto

```
wolf-wallet/
├── .gitignore
├── .streamlit/
│   └── secrets.toml          # NÃO vai para o repo
├── requirements.txt
├── README.md
│
├── app.py                     # Entry point — roteamento de páginas
│
├── config/
│   ├── settings.py            # Constantes e configurações
│   └── database.py            # Conexão com Supabase/PostgreSQL
│
├── auth/
│   ├── login.py               # Tela de login
│   ├── session.py             # Gerenciamento de sessão (st.session_state)
│   ├── password.py            # Hash, validação, reset de senha
│   └── email_service.py       # Envio de email via Gmail SMTP
│
├── pages/
│   ├── home.py                # Dashboard principal
│   ├── extrato.py             # Extrato detalhado
│   ├── rendimentos.py         # Tela de rendimentos
│   ├── contas.py              # Contas mensais
│   ├── admin_usuarios.py      # Gerenciamento de usuários (admin)
│   └── admin_sync.py          # Painel de sincronização (admin)
│
├── services/
│   ├── mercadopago.py         # Integração com API do Mercado Pago
│   ├── sync_service.py        # Job de sincronização (sync diária + chunked)
│   ├── auto_sync.py           # Sync automática em background + freshness check
│   ├── report_service.py      # Lógica de negócio e cálculos financeiros
│   └── email_service.py       # Envio de email via Gmail SMTP
│
├── models/
│   ├── user.py                # CRUD de usuários
│   ├── transaction.py         # CRUD de transações
│   ├── bill.py                # CRUD de contas mensais
│   └── sync_log.py            # CRUD de logs de sync
│
├── components/
│   ├── sidebar.py             # Sidebar de navegação
│   ├── cards.py               # Componentes de cards do dashboard
│   ├── charts.py              # Gráficos reutilizáveis
│   ├── filters.py             # Filtros reutilizáveis (data, tipo, direção)
│   ├── transaction_table.py   # Tabela de transações estilizada
│   ├── hide_balance.py        # Componente de ocultar saldo
│   ├── sync_status.py         # Banner de status da sincronização
│   └── mobile_css.py          # CSS responsivo para mobile
│
├── mock/
│   └── mock_data.py           # Dados fictícios para modo visitante
│
├── sql/
│   └── schema.sql             # Script de criação das tabelas
│
└── docs/
    └── wolf-wallet-spec.md    # Este documento
```

---

## 12. Dependências (requirements.txt)

```txt
streamlit>=1.30.0
pandas>=2.0.0
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0
bcrypt>=4.0.0
plotly>=5.18.0
requests>=2.31.0
python-dotenv>=1.0.0
```

---

## 13. Configuração do .gitignore

```gitignore
# Credenciais
.env
.streamlit/secrets.toml

# Python
__pycache__/
*.pyc
*.pyo
venv/
.venv/

# Dados temporários
*.csv
*.xlsx

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

---

## 14. Deploy — Streamlit Community Cloud

### Pré-requisitos
1. Repositório no GitHub (privado ou público)
2. Conta no [Streamlit Community Cloud](https://share.streamlit.io)
3. Conta no [Supabase](https://supabase.com) com banco configurado

### Configuração de Secrets no Streamlit Cloud
No painel do Streamlit Cloud → App settings → Secrets, adicionar:
```toml
MP_ACCESS_TOKEN = "APP_USR-..."
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOi..."
DATABASE_URL = "postgresql://user:pass@host:5432/dbname"
GMAIL_USER = "wolfwallet.projeto@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
JWT_SECRET = "chave-secreta-aleatoria"
```

---

## 15. Roadmap de Desenvolvimento

### Fase 1 — MVP (Semanas 1-2)
- [ ] Setup do repositório e estrutura de pastas
- [ ] Configuração do Supabase e criação das tabelas
- [ ] Tela de login (email/senha + visitante)
- [ ] Dashboard básico com cards de saldo
- [ ] Integração com API do Mercado Pago (sync manual)
- [ ] Extrato detalhado com filtros

### Fase 2 — Funcionalidades Core (Semanas 3-4)
- [ ] Gerenciamento de usuários (admin)
- [ ] Contas mensais
- [ ] Tela de rendimentos
- [ ] "Esqueci minha senha" com email
- [ ] Ocultar saldo

### Fase 3 — Polimento (Semana 5)
- [ ] Dados mockados para modo visitante
- [ ] Tema escuro/claro
- [ ] Alertas de contas próximas do vencimento
- [ ] Feed de atividades recentes
- [ ] Gráficos refinados com Plotly
- [ ] Sync automático diário

### Fase 4 — Melhorias Futuras (Backlog)
- [ ] Login com Google/Microsoft (OAuth)
- [ ] Notificações por email (resumo mensal automático)
- [ ] App mobile (Streamlit funciona em mobile browser)
- [ ] Relatórios em PDF para download
- [ ] Integração com outras APIs financeiras