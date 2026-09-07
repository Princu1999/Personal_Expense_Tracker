<p align="center">
  <h1 align="center">💰 Personal Expense Tracker</h1>
  <p align="center">
    <strong>An AI-powered conversational expense tracker built with LangGraph, FastAPI & Streamlit</strong>
  </p>
  <p align="center">
    <a href="#features">Features</a> •
    <a href="#tech-stack">Tech Stack</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#getting-started">Getting Started</a> •
    <a href="#api-reference">API Reference</a> •
    <a href="#testing">Testing</a>
  </p>
</p>

---

## 📖 Overview

**Personal Expense Tracker** is a multi-user, AI-powered application that lets you track your expenses through natural language conversation. Instead of filling out forms or spreadsheets, just chat:

> *"I spent ₹450 on groceries today"*  
> *"Show me my expenses this week"*  
> *"How much did I spend on food last month?"*

The AI agent automatically **extracts amounts, categories, and dates** from your messages, stores them in a PostgreSQL database, and answers queries about your spending — all through a beautiful chat interface.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🗣️ **Natural Language Input** | Record expenses by simply describing them in plain English |
| 🔍 **Smart Querying** | Ask questions about your spending and get instant summaries |
| 🔐 **Multi-User Auth** | JWT-based authentication with registration and login |
| 💬 **Persistent Conversations** | Chat history survives server restarts via PostgreSQL-backed checkpointing |
| 🧵 **Multiple Chat Threads** | Create, switch between, and delete separate conversation threads |
| 🏷️ **Auto Title Generation** | Conversations get auto-generated titles using LLM |
| ⚡ **Real-Time Streaming** | Token-by-token Server-Sent Events (SSE) for responsive UI |
| 🛡️ **Comprehensive Guardrails** | Rate limiting, prompt injection detection, toxicity filtering, PII redaction, hallucination checking, and more |
| 📂 **38 Default Categories** | Pre-seeded expense categories on user registration |
| 🔒 **Data Isolation** | Strict per-user data scoping — users can never access each other's data |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **AI Agent** | [LangGraph](https://github.com/langchain-ai/langgraph) + [LangChain](https://github.com/langchain-ai/langchain) |
| **LLM Provider** | [Groq](https://groq.com/) (ultra-fast inference) |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| **Frontend** | [Streamlit](https://streamlit.io/) |
| **Database** | [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy](https://www.sqlalchemy.org/) (async) |
| **Auth** | JWT (PyJWT) + bcrypt password hashing |
| **Checkpointing** | LangGraph PostgreSQL Checkpointer (persistent conversation state) |
| **Observability** | [LangSmith](https://smith.langchain.com/) (optional tracing) |

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────┐     HTTP/SSE      ┌──────────────────────────────────────┐
│                 │ ◄───────────────► │            FastAPI Backend           │
│   Streamlit UI  │                   │                                      │
│   (Frontend)    │                   │  ┌──────────┐    ┌───────────────┐  │
│                 │                   │  │ Auth API │    │  Chat API     │  │
└─────────────────┘                   │  └──────────┘    └───────┬───────┘  │
                                      │                          │          │
                                      │               ┌─────────▼────────┐ │
                                      │               │   Guardrails     │ │
                                      │               │  (Input/Output)  │ │
                                      │               └─────────┬────────┘ │
                                      │                         │          │
                                      │              ┌──────────▼────────┐ │
                                      │              │  LangGraph Agent  │ │
                                      │              │  ┌──────────────┐ │ │
                                      │              │  │   LLM Node   │ │ │
                                      │              │  │  (Groq API)  │ │ │
                                      │              │  └──────┬───────┘ │ │
                                      │              │         │         │ │
                                      │              │  ┌──────▼───────┐ │ │
                                      │              │  │  Tool Node   │ │ │
                                      │              │  │ • record     │ │ │
                                      │              │  │ • query      │ │ │
                                      │              │  └──────────────┘ │ │
                                      │              └───────────────────┘ │
                                      └──────────────────────┬─────────────┘
                                                             │
                                                    ┌────────▼────────┐
                                                    │   PostgreSQL    │
                                                    │  • Users        │
                                                    │  • Expenses     │
                                                    │  • Categories   │
                                                    │  • Conversations│
                                                    │  • Checkpoints  │
                                                    └─────────────────┘
```

### LangGraph Agent Flow

The AI agent is built as a **LangGraph state machine** with a simple but powerful loop:

```
START ──► LLM Node ──► Has tool calls? ──YES──► Tool Node ──► (back to LLM)
                            │
                            NO
                            │
                           END
```

- **LLM Node**: Sends conversation history + system prompt to the Groq-hosted LLM with tools bound
- **Tool Node**: Executes `record_expense` or `query_expenses` against the database
- The loop cycles until the LLM produces a final text response

### Database Schema

```
users ──┬──► categories ──► expenses
        ├──► expenses
        └──► conversations
```

| Table | Key Fields |
|-------|-----------|
| `users` | `id`, `email`, `username`, `hashed_password`, `default_currency` |
| `categories` | `id`, `name`, `user_id` (unique per user) |
| `expenses` | `id`, `amount`, `currency`, `category_id`, `description`, `transaction_date` |
| `conversations` | `id` (UUID), `user_id`, `title`, `created_at`, `updated_at` |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **PostgreSQL** running on `localhost:5432`
- **Groq API Key** — Get one free at [console.groq.com](https://console.groq.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/Princu1999/Personal_Expense_Tracker.git
cd Personal_Expense_Tracker
```

### 2. Create Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your actual values:

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Your Groq API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | A secure random string for JWT signing |

### 5. Set Up the Database

```bash
# Create the 'expense_tracker' database in PostgreSQL first, then:
python migrate_db.py
```

### 6. Start the Backend

```bash
uvicorn app.api.chat:app --reload --host 0.0.0.0 --port 8000
```

### 7. Start the Frontend

```bash
streamlit run frontend/streamlit_app.py
```

Open your browser and start chatting! 🎉

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login and receive JWT token |
| `GET` | `/auth/me` | Get current user profile |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send a message and receive a response |
| `POST` | `/chat/stream` | Send a message with SSE streaming response |

### Conversations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/conversations` | List all conversations |
| `GET` | `/conversations/{id}/messages` | Get messages for a conversation |
| `DELETE` | `/conversations/{id}` | Delete a conversation |

> **Auth**: All chat and conversation endpoints require a `Bearer` token in the `Authorization` header.

---

## 🛡️ Guardrails System

The application includes a comprehensive **input/output guardrail pipeline**:

### Input Guardrails (Pre-LLM)

| Guardrail | What It Does |
|-----------|-------------|
| **Rate Limiter** | Sliding window (30 req/min) per user — prevents abuse |
| **Prompt Injection** | Detects override commands, system prompt extraction, jailbreak patterns |
| **Toxicity Filter** | Blocks profanity, hate speech, threats (with leetspeak normalization) |
| **PII Redaction** | Redacts credit cards (Luhn-validated), SSNs, Aadhaar numbers, emails, phone numbers, API keys |

### Output Guardrails (Post-LLM)

| Guardrail | What It Does |
|-----------|-------------|
| **Format Validation** | Fixes unclosed markdown fences, strips leaked XML |
| **Policy Compliance** | Adds financial disclaimers, redacts accidentally leaked secrets |
| **Hallucination Check** | Catches fabricated expenses when query returned none |

All guardrails are individually toggleable via environment variables.

---

## 🧪 Testing

The project includes a comprehensive test suite covering database operations, authentication, guardrails, streaming, and more.

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_guardrails.py      # Guardrails unit tests
pytest tests/test_auth_isolation.py  # Multi-user data isolation
pytest tests/test_streaming.py       # SSE streaming tests
pytest tests/test_crud.py            # Expense CRUD operations
```

> **Note**: Tests run against a real PostgreSQL database configured in your `.env` file.

---

## 📁 Project Structure

```
Personal_Expense_Tracker/
├── app/                          # Main application package
│   ├── api/                      # FastAPI HTTP layer
│   │   ├── auth.py               #   Auth endpoints (register, login, /me)
│   │   ├── chat.py               #   Chat endpoints (chat, stream, conversations)
│   │   └── deps.py               #   Dependency injection (auth, database)
│   │
│   ├── database/                 # Data access layer
│   │   ├── base.py               #   SQLAlchemy declarative base
│   │   ├── connection.py         #   Async engine creation
│   │   ├── session.py            #   Async session factory
│   │   ├── crud.py               #   Expense CRUD operations
│   │   ├── category_crud.py      #   Category CRUD + get_or_create
│   │   └── conversation_crud.py  #   Conversation CRUD
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── user.py               #   User model
│   │   ├── category.py           #   Category model
│   │   ├── expense.py            #   Expense model
│   │   └── conversation.py       #   Conversation model
│   │
│   ├── schemas/                  # Pydantic validation schemas
│   │   ├── auth.py               #   Auth request/response models
│   │   └── conversation.py       #   Chat request/response models
│   │
│   ├── services/                 # Business logic layer
│   │   ├── auth_service.py       #   JWT, password hashing, user management
│   │   ├── expense_service.py    #   Expense business operations
│   │   ├── category_service.py   #   Category operations
│   │   └── conversation_service.py  # Conversation lifecycle + title gen
│   │
│   ├── graph/                    # LangGraph AI agent
│   │   ├── state.py              #   Agent state definition
│   │   ├── nodes.py              #   LLM node (system prompt + Groq)
│   │   └── graph.py              #   State graph construction
│   │
│   ├── tools/                    # LangChain tools for the agent
│   │   ├── expense_tools.py      #   record_expense tool
│   │   └── query_tools.py        #   query_expenses tool
│   │
│   ├── guardrails/               # Input/output safety system
│   │   ├── input/                #   Rate limiter, prompt injection, toxicity, PII
│   │   ├── output/               #   Format repair, hallucination, policy
│   │   ├── manager.py            #   Guardrail orchestrator
│   │   └── config.py             #   Guardrail configuration
│   │
│   └── config.py                 # Centralized app settings
│
├── frontend/
│   └── streamlit_app.py          # Streamlit chat interface
│
├── tests/                        # Test suite (10 test files)
├── migrate_db.py                 # Database migration script
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
├── .env.example                  # Environment variable template
└── README.md                     # This file
```

---

## ⚙️ Configuration

All configuration is managed through environment variables. See [`.env.example`](.env.example) for the complete list.

| Category | Variables |
|----------|----------|
| **Database** | `DATABASE_URL` |
| **LLM** | `GROQ_API_KEY`, `GROQ_MODEL` |
| **Auth** | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| **Guardrails** | `ENABLE_GUARDRAILS`, `ENABLE_PII_REDACTION`, `ENABLE_PROMPT_INJECTION`, `ENABLE_TOXICITY`, `ENABLE_HALLUCINATION_CHECK`, `ENABLE_POLICY_COMPLIANCE`, `ENABLE_FORMAT_VALIDATION`, `RATE_LIMIT_PER_MINUTE` |
| **Observability** | `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ using LangGraph, FastAPI & Streamlit
</p>
