# 🏥 MedAssist - AI Medical Knowledge Assistant

A full-stack Laravel web application that provides an AI-powered medical chatbot interface for healthcare professionals. The system communicates with a separate RAG (Retrieval-Augmented Generation) backend via REST API to deliver evidence-based medical answers with source references.

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [Login Credentials](#login-credentials)
- [RAG API Integration](#rag-api-integration)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Stage 2 Roadmap (SaaS)](#stage-2-roadmap-saas)

---

## ✨ Features

- **🔐 Authentication** — Secure login/logout system for doctors
- **💬 AI Chat Interface** — Real-time medical Q&A with typing indicators
- **📚 Source References** — Each answer shows source file, page number, section, and relevance score
- **🖼️ Medical Images** — Displays referenced diagrams and images from medical literature
- **📊 Comparison Tables** — Side-by-side medical comparisons (e.g., Type 1 vs Type 2 Diabetes)
- **💡 Follow-up Suggestions** — AI suggests related questions for deeper exploration
- **📜 Chat History** — Browse and manage all past conversations
- **📱 Fully Responsive** — Works perfectly on mobile, tablet, and desktop
- **⚡ AJAX-powered** — Messages sent without page reload for smooth UX

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   FRONTEND                       │
│          (Laravel Blade + Responsive CSS)        │
│   ┌─────────┐  ┌──────────┐  ┌───────────────┐  │
│   │  Login   │  │   Chat   │  │    History     │  │
│   │  Page    │  │   Page   │  │     Page       │  │
│   └─────────┘  └──────────┘  └───────────────┘  │
│                       │                          │
│                  ChatController                  │
│                       │                          │
│               RagApiService.php                  │
└───────────────────────────┬──────────────────────┘
                            │
                    HTTP POST Request
                    (JSON API Call)
                            │
                            ▼
┌──────────────────────────────────────────────────┐
│                  RAG BACKEND                      │
│         (Separate Python/FastAPI Service)         │
│   ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│   │ Document  │  │ Vector   │  │   LLM Query   │  │
│   │  Parser   │  │  Search  │  │    Engine     │  │
│   └──────────┘  └──────────┘  └───────────────┘  │
└──────────────────────────────────────────────────┘
```

**Key Design Principle:** The full-stack system is completely **isolated** from the RAG system. They communicate only via HTTP REST API. This allows independent development, testing, and deployment of each component.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Laravel 12 (PHP 8.2+) |
| Database | SQLite (development) |
| Frontend | Blade Templates + Vanilla CSS/JS |
| Icons | Lucide Icons |
| Fonts | Google Fonts (Inter) |
| RAG Communication | Laravel HTTP Client |

---

## 📦 Prerequisites

- **PHP 8.2+** with extensions: pdo_sqlite, mbstring, openssl, tokenizer
- **Composer** (PHP package manager)
- **Node.js** (optional, only if using Vite for asset compilation)

---

## 🚀 Installation & Setup

### 1. Navigate to the project
```bash
cd fullstack-system
```

### 2. Install PHP dependencies
```bash
composer install
```

### 3. Setup environment
```bash
cp .env.example .env
php artisan key:generate
```

### 4. Configure the RAG API URL
Edit `.env` and add this line:
```env
RAG_API_URL=http://127.0.0.1:8000
```

### 5. Create database and run migrations
```bash
touch database/database.sqlite
php artisan migrate --force
```

### 6. Seed the default user
```bash
php artisan db:seed --force
```

---

## ▶️ Running the Application

### Start the Laravel development server:
```bash
php artisan serve
```

### Open in browser:
```
http://127.0.0.1:8000
```

You will be redirected to the login page.

---

## 🔑 Login Credentials

| Field | Value |
|-------|-------|
| **Email** | `doc@gmail.com` |
| **Password** | `123` |

---

## 📡 RAG API Integration

### How It Works

The full-stack system communicates with the RAG backend through a single REST API endpoint:

```
POST http://127.0.0.1:8000/api/query
```

### Service File
The integration logic is in:
```
app/Services/RagApiService.php
```

### Request Format
When a doctor types a question, the system sends:

```json
POST /api/query
Content-Type: application/json

{
    "question": "What are the diagnostic criteria for Type 2 Diabetes?",
    "conversation_id": 1
}
```

### Expected Response Format
The RAG backend should return:

```json
{
    "answer": "Diabetes mellitus is a chronic metabolic disorder...",

    "sources": [
        {
            "file": "Harrison_Principles_Internal_Medicine.pdf",
            "page": 42,
            "section": "Chapter 3: Diabetes Mellitus",
            "relevance_score": 0.95,
            "excerpt": "Diabetes mellitus encompasses a group of metabolic diseases..."
        }
    ],

    "images": [
        {
            "description": "Glucose metabolism pathway diagram",
            "page": 43,
            "source_file": "Harrison_Principles_Internal_Medicine.pdf"
        }
    ],

    "comparisons": [
        "Type 1 vs Type 2 Diabetes",
        {
            "feature": "Age of onset",
            "type1": "Usually childhood/adolescence",
            "type2": "Usually adulthood (>40 years)"
        }
    ],

    "suggestions": [
        "What are the complications of diabetes?",
        "How is diabetes managed pharmacologically?"
    ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The main answer text (supports markdown: `**bold**`, bullet points) |
| `sources` | array | List of source references from medical literature |
| `sources[].file` | string | PDF/document filename |
| `sources[].page` | integer | Page number in the source document |
| `sources[].section` | string | Chapter or section title |
| `sources[].relevance_score` | float | Relevance score (0.0 - 1.0) |
| `sources[].excerpt` | string | Relevant text excerpt from source |
| `images` | array | Referenced images/diagrams (optional) |
| `comparisons` | array | Comparison data for side-by-side display (optional) |
| `suggestions` | array | Follow-up question suggestions |

### Configuration

The RAG API URL is configured in:

```
config/services.php → services.rag.base_url
```

Or via environment variable:
```env
RAG_API_URL=http://127.0.0.1:8000
```

### Fallback Behavior

If the RAG backend is **offline or unreachable**, the system falls back to built-in mock responses for common medical topics (Diabetes, Hypertension, Heart Failure) to allow demo/testing without the RAG service.

### Health Check

The service includes a health check method:
```php
$ragService = new \App\Services\RagApiService();
$isHealthy = $ragService->healthCheck(); // checks GET /api/health
```

---

## 📁 Project Structure

```
fullstack-system/
├── app/
│   ├── Http/
│   │   └── Controllers/
│   │       ├── AuthController.php      # Login/Logout logic
│   │       └── ChatController.php      # Chat CRUD + RAG integration
│   ├── Models/
│   │   ├── User.php                    # User model
│   │   ├── Conversation.php            # Conversation model
│   │   └── Message.php                 # Message model (user/assistant)
│   └── Services/
│       └── RagApiService.php           # 🔗 RAG API communication layer
│
├── config/
│   └── services.php                    # RAG API URL configuration
│
├── database/
│   ├── migrations/                     # Database schema
│   ├── seeders/
│   │   └── DatabaseSeeder.php          # Default doctor user
│   └── database.sqlite                 # SQLite database file
│
├── resources/
│   └── views/
│       ├── auth/
│       │   └── login.blade.php         # Login page
│       ├── chat/
│       │   ├── home.blade.php          # Chat welcome screen
│       │   ├── show.blade.php          # Conversation with messages
│       │   └── history.blade.php       # Chat history list
│       └── layouts/
│           ├── app.blade.php           # Base layout (CSS + responsive)
│           └── chat.blade.php          # Chat layout (sidebar + main)
│
├── routes/
│   └── web.php                         # All application routes
│
└── .env                                # Environment configuration
```

---

## 🗄️ Database Schema

### Users Table
| Column | Type | Description |
|--------|------|-------------|
| id | integer | Primary key |
| name | string | Doctor's name |
| email | string | Login email (unique) |
| password | string | Hashed password |

### Conversations Table
| Column | Type | Description |
|--------|------|-------------|
| id | integer | Primary key |
| user_id | integer | Foreign key → users |
| title | string | Auto-generated from first message |
| created_at | timestamp | Creation time |
| updated_at | timestamp | Last activity |

### Messages Table
| Column | Type | Description |
|--------|------|-------------|
| id | integer | Primary key |
| conversation_id | integer | Foreign key → conversations |
| role | enum | `user` or `assistant` |
| content | text | Message text |
| sources | json | RAG source references (nullable) |
| suggestions | json | Follow-up suggestions (nullable) |
| created_at | timestamp | Message time |

---

## 🔀 API Endpoints (Web Routes)

| Method | URL | Description | Auth |
|--------|-----|-------------|------|
| GET | `/login` | Show login page | ❌ |
| POST | `/login` | Process login | ❌ |
| POST | `/logout` | Logout | ✅ |
| GET | `/` | Redirect to chat | ✅ |
| GET | `/chat` | Chat home (welcome screen) | ✅ |
| GET/POST | `/chat/new` | Create new conversation | ✅ |
| GET | `/chat/{id}` | View conversation | ✅ |
| POST | `/chat/{id}/send` | Send message (AJAX) | ✅ |
| DELETE | `/chat/{id}` | Delete conversation | ✅ |
| GET | `/chat/history` | Chat history page | ✅ |

---

## ⚙️ Configuration

### Key Environment Variables (`.env`)

```env
APP_NAME=MedAssist
APP_ENV=local
APP_DEBUG=true
APP_URL=http://localhost:8000

DB_CONNECTION=sqlite

RAG_API_URL=http://127.0.0.1:8000
```

---

## 🗺️ Stage 2 Roadmap (SaaS)

Future enhancements planned:

- [ ] **Subscription Plans** — Monthly billing tiers (Free / Pro / Enterprise)
- [ ] **Payment Integration** — Stripe/PayPal payment processing
- [ ] **User Dashboard** — Usage analytics and conversation statistics
- [ ] **Admin Panel** — User management and system monitoring
- [ ] **API Rate Limiting** — Query limits per subscription tier
- [ ] **Multi-language** — Arabic/English interface support
- [ ] **PDF Export** — Export conversations as medical reports
- [ ] **Team Collaboration** — Share conversations between doctors

---

## 👥 Team

This project is built for a medical AI hackathon. The full-stack system is developed separately from the RAG system, with clear API boundaries for independent team workflow.

---

## 📝 License

Medical AI Hackathon Project — 2026
