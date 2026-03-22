# 🐺 Wolf Wallet

> Carteira virtual do **PET-SI — Universidade Federal de Uberlândia (UFU)**.
> Visualize as movimentações financeiras da conta compartilhada de forma transparente e automatizada.

---

## 📖 Sobre

Atualmente, o responsável pela conta do Mercado Pago do PET-SI precisa baixar o extrato manualmente e enviar no WhatsApp/Teams todo mês. O **Wolf Wallet** resolve isso com um dashboard financeiro acessível a todos os membros, com:

- 📊 **Dashboard** com saldo, entradas, saídas e rendimentos em tempo real
- 📋 **Extrato detalhado** com filtros avançados e exportação
- 📈 **Rendimentos** CDI acompanhados dia a dia
- 👥 **Contribuições** dos membros com controle mensal
- 💳 **Contas mensais** com alertas de vencimento
- 🔄 **Sincronização automática** com a API do Mercado Pago

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Frontend / Backend | [Streamlit](https://streamlit.io/) (Python) |
| Banco de Dados | PostgreSQL via [Supabase](https://supabase.com/) |
| API Financeira | [Mercado Pago — Settlement Report API](https://www.mercadopago.com.br/developers/) |
| Envio de Email | Gmail SMTP (smtplib) |
| Deploy | [Streamlit Community Cloud](https://share.streamlit.io/) |

---

## 🚀 Setup Local

### Pré-requisitos

- Python 3.11+
- Git
- Conta no [Supabase](https://supabase.com/) (banco configurado)
- Access Token do [Mercado Pago](https://www.mercadopago.com.br/developers/)

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/pet-si-ufu/wolf-wallet.git
cd wolf-wallet

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as credenciais
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
# Edite .streamlit/secrets.toml com suas credenciais

# 5. Execute a aplicação
streamlit run app.py
```

### Configuração de Credenciais

Crie o arquivo `.streamlit/secrets.toml` (NÃO vai para o repositório):

```toml
# Mercado Pago
MP_ACCESS_TOKEN = "APP_USR-..."

# Supabase
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOi..."
DATABASE_URL = "postgresql://user:pass@host:5432/dbname"

# Gmail SMTP
GMAIL_USER = "wolfwallet.projeto@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"

# App
JWT_SECRET = "chave-secreta-aleatoria"
```

---

## 📁 Estrutura do Projeto

```
wolf-wallet/
├── app.py                     # Entry point — roteamento de páginas
├── config/
│   ├── settings.py            # Constantes e configurações
│   └── database.py            # Conexão com Supabase/PostgreSQL
├── auth/
│   ├── login.py               # Tela de login
│   ├── session.py             # Gerenciamento de sessão
│   ├── password.py            # Hash, validação, reset de senha
│   └── email_service.py       # Envio de email via Gmail SMTP
├── pages/
│   ├── home.py                # Dashboard principal
│   ├── extrato.py             # Extrato detalhado
│   ├── rendimentos.py         # Tela de rendimentos
│   ├── contribuicoes.py       # Contribuições dos membros
│   ├── contas.py              # Contas mensais
│   ├── admin_usuarios.py      # Gerenciamento de usuários (admin)
│   └── admin_sync.py          # Painel de sincronização (admin)
├── services/
│   ├── mercadopago.py         # Integração com API do Mercado Pago
│   ├── sync_service.py        # Job de sincronização diária
│   ├── transaction_service.py # Lógica de negócio das transações
│   └── report_service.py      # Geração de relatórios e cálculos
├── models/
│   ├── user.py                # CRUD de usuários
│   ├── transaction.py         # CRUD de transações
│   ├── bill.py                # CRUD de contas mensais
│   ├── contribution.py        # CRUD de contribuições
│   └── sync_log.py            # CRUD de logs de sync
├── components/
│   ├── sidebar.py             # Sidebar de navegação
│   ├── cards.py               # Componentes de cards
│   ├── charts.py              # Gráficos reutilizáveis
│   ├── tables.py              # Tabelas reutilizáveis
│   └── hide_balance.py        # Componente de ocultar saldo
├── mock/
│   └── mock_data.py           # Dados fictícios (modo visitante)
├── sql/
│   └── schema.sql             # Script de criação das tabelas
└── docs/
    └── wolf-wallet-spec.md    # Especificação completa do projeto
```

---

## 👥 Papéis

| Role | Permissões |
|---|---|
| **Admin** | Tudo: gerenciar usuários, contas, confirmar contribuições, sync |
| **User** | Visualizar dashboard, extrato, contribuições, contas |
| **Visitante** | Dashboard com dados fictícios (demonstração) |

---

## 📅 Roadmap

- [x] **Fase 0** — Fundação (estrutura, banco, config)
- [ ] **Fase 1** — Autenticação e navegação
- [ ] **Fase 2** — Dashboard e transações
- [ ] **Fase 3** — Integração Mercado Pago
- [ ] **Fase 4** — Extrato detalhado
- [ ] **Fase 5** — Rendimentos
- [ ] **Fase 6** — Contribuições
- [ ] **Fase 7** — Contas mensais
- [ ] **Fase 8** — Gestão de usuários e email
- [ ] **Fase 9** — Modo visitante (dados mockados)
- [ ] **Fase 10** — Polimento UX
- [ ] **Fase 11** — Deploy

---

## 📝 Licença

Projeto interno do PET-SI — UFU. Repositório inicialmente privado, será tornado público futuramente.

---

*Desenvolvido com ❤️ pelo PET-SI — Universidade Federal de Uberlândia*
