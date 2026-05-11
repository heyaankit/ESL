# ESL - English Learning Backend API

[![GitHub stars](https://img.shields.io/github/stars/heyaankit/ESL)](https://github.com/heyaankit/ESL/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/heyaankit/ESL)](https://github.com/heyaankit/ESL/network)
[![GitHub issues](https://img.shields.io/github/issues/heyaankit/ESL)](https://github.com/heyaankit/ESL/issues)
[![License](https://img.shields.io/github/license/heyaankit/ESL)](https://github.com/heyaankit/ESL/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-white)](https://fastapi.tiangolo.com/)

A FastAPI backend for an English Learning application with AI-powered chat, text-to-speech, and interactive lessons.

## Features

- **AI-Powered Chat** - Conversational English tutor with local AI models (Ollama)
- **Adaptive Teaching** - Detects learner level, gently corrects mistakes, introduces grammar naturally
- **Text-to-Speech** - Local TTS using Kokoro ONNX model with multiple voices
- **Interactive Lessons** - Dynamic lesson flow with progress tracking
- **Voice Answers** - Submit voice answers with transcription
- **Quiz System** - AI-generated quiz questions
- **Authentication** - Phone/OTP-based authentication with JWT
- **SQLite Database** - Simple, file-based database for easy setup

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **SQLite** - File-based database
- **Pydantic** - Data validation
- **Kokoro TTS** - Local text-to-speech model (ONNX)
- **Ollama** - Local AI models for chat
- **Python** - Core language

## Project Structure

```
ESL/
├── app/                    # FastAPI backend application
│   ├── main.py            # App entry point & lifespan
│   ├── config.py          # Settings & environment config
│   ├── auth.py            # JWT authentication
│   ├── database.py        # Database config
│   ├── logger.py          # Logging config
│   ├── routers/           # API route handlers
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── chat.py        # AI chat endpoints
│   │   ├── lesson.py      # Dynamic lesson endpoints
│   │   ├── tts.py         # Text-to-speech endpoints
│   │   └── ...            # Other routers
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   └── services/          # Business logic
│       ├── ai_service.py  # AI chat service (OpenAI/Ollama)
│       ├── tts.py         # Text-to-speech service
│       ├── audio_service.py # Audio processing
│       └── models/        # TTS model files
│           ├── model.onnx # Kokoro TTS model
│           └── voices/    # Voice preset files
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
├── esl.db                 # SQLite database
└── alembic/               # Database migrations
```

## Prerequisites

- Python 3.14+
- Ollama (optional, for local AI chat)

## How to Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/heyaankit/ESL.git
cd ESL
```

### 2. Set up Python environment

```bash
# Create virtual environment (recommended)
python -m venv .venv

# Activate - Linux/Mac
source .venv/bin/activate

# Activate - Windows (PowerShell)
.venv\Scripts\activate

# Activate - Windows (CMD)
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Set up local AI model

For AI chat features, install and run Ollama:

```bash
# Install Ollama from https://ollama.com

# Pull a model (llama3.2:3b recommended)
ollama pull llama3.2:3b
```

Update `.env` if using local model:
```env
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3.2:3b
```

### 5. Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API runs at: **http://localhost:8000**

API documentation: **http://localhost:8000/docs**

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login with credentials |
| POST | `/api/v1/auth/request-otp` | Request OTP |
| POST | `/api/v1/auth/verify-otp` | Verify OTP |
| GET | `/api/v1/auth/get_profile` | Get user profile |

### Chat (AI Tutor)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/chat/themes` | List available themes |
| GET | `/api/v1/chat/dialogs/{theme}` | Get dialog scenarios |
| POST | `/api/v1/chat/start-dialog` | Start dialog practice |
| POST | `/api/v1/chat/send-message` | Send message to AI |
| GET | `/api/v1/chat/history/{user_id}` | Get chat history |
| GET | `/api/v1/chat/corrections/{user_id}` | Get sentence corrections |
| GET | `/api/v1/chat/assessment/{user_id}` | Get level assessment |

### Lessons

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/lesson/list` | List all lessons |
| POST | `/api/v1/lesson/start` | Start a lesson |
| POST | `/api/v1/lesson/next` | Get next question |
| POST | `/api/v1/lesson/submit-answer` | Submit answer |
| POST | `/api/v1/lesson/submit-voice-answer` | Submit voice answer |
| GET | `/api/v1/lesson/progress/{user_id}` | Get user progress |

### Text-to-Speech

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tts/voices` | List available voices |
| POST | `/api/v1/tts/speak` | Generate speech from text |

### Quiz

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/quiz/generate` | Generate quiz question |
| POST | `/api/v1/quiz/evaluate` | Evaluate answer |

## Example Usage (cURL)

### Register a user

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"phone": "97688123456", "password": "test123", "name": "Test User"}'
```

### Send a chat message

```bash
curl -X POST http://localhost:8000/api/v1/chat/send-message \
  -F "user_id=user123" \
  -F "message=Hello, I want to practice English" \
  -F "mode=chat"
```

### Generate TTS audio

```bash
curl -X POST http://localhost:8000/api/v1/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, welcome to English learning!", "voice": "af_sarah"}'
```

### Start a lesson

```bash
curl -X POST http://localhost:8000/api/v1/lesson/start \
  -F "user_id=user123" \
  -F "lesson_id=1"
```

## Database

The database file is `esl.db`. You can inspect it:

```bash
sqlite3 esl.db ".tables"
sqlite3 esl.db "SELECT * FROM users LIMIT 5;"
```

## Environment Variables

Create a `.env` file (already included in repo):

```env
# Server
APP_ENV=development
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///esl.db

# JWT
SECRET_KEY=dev-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Chat (optional - for local models)
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3.2:3b
```

## License

MIT License