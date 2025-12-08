# AI Interview System API

A production-ready FastAPI backend for conducting AI-powered technical interviews with JWT authentication.

## Features

- 🔐 **JWT Authentication** - Secure user authentication with FastAPI Users
- 🤖 **AI-Powered Questions** - Dynamic question generation using GPT-4o-mini
- 📊 **Adaptive Difficulty** - Questions adjust based on candidate performance
- 📝 **Real-time Evaluation** - Immediate feedback on answers with detailed scoring
- 📈 **Comprehensive Reports** - Detailed assessment with hiring recommendations
- 🗃️ **SQLite Async** - Lightweight async database with aiosqlite

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py                    # Application entry point
│   ├── api/                       # Additional API routes
│   │   └── __init__.py
│   ├── auth/                      # Authentication module
│   │   ├── __init__.py
│   │   ├── models.py              # User database model
│   │   ├── schemas.py             # Auth Pydantic schemas
│   │   ├── users.py               # User manager & JWT config
│   │   └── router.py              # Auth routes
│   ├── core/                      # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py              # Settings management
│   │   └── database.py            # Database configuration
│   └── interview/                 # Interview module
│       ├── __init__.py
│       ├── models.py              # Interview Pydantic models
│       ├── router.py              # Interview API routes
│       ├── storage.py             # In-memory session storage
│       └── services/
│           ├── __init__.py
│           ├── interview_service.py  # Business logic
│           └── openai_service.py     # OpenAI API integration
├── .env.example                   # Environment template
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
cd /home/ldt/Interview
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# Get your key from: https://platform.openai.com/api-keys
```

**Required Environment Variables:**
```env
OPENAI_API_KEY="sk-your-openai-api-key-here"
SECRET_KEY="generate-a-secure-key"
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication (`/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/jwt/login` | Login and get JWT token |
| POST | `/auth/jwt/logout` | Logout |
| GET | `/auth/users/me` | Get current user |
| PATCH | `/auth/users/me` | Update current user |

### Interview (`/api/interview`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/interview/start` | Start a new interview |
| POST | `/api/interview/answer` | Submit an answer |
| GET | `/api/interview/report/{id}` | Get final report |
| GET | `/api/interview/status/{id}` | Get interview status |
| GET | `/api/interview/question/{id}` | Get current question |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Basic health check |
| GET | `/health` | Detailed health check |

## Interview Flow

### 1. Start Interview

```bash
curl -X POST "http://localhost:8000/api/interview/start" \
  -H "Content-Type: application/json" \
  -d '{
    "experience_level": "mid",
    "subject": "Python",
    "difficulty": "medium",
    "num_questions": 5
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "interview_id": "550e8400-e29b-41d4-a716-446655440000",
    "first_question": {
      "question_number": 1,
      "question": "Explain the difference between a list and a tuple in Python...",
      "difficulty": "medium",
      "topic": "Data Structures"
    },
    "total_questions": 5,
    "config": {...}
  }
}
```

### 2. Submit Answer

```bash
curl -X POST "http://localhost:8000/api/interview/answer" \
  -H "Content-Type: application/json" \
  -d '{
    "interview_id": "550e8400-e29b-41d4-a716-446655440000",
    "answer": "Lists are mutable while tuples are immutable...",
    "question_number": 1
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "evaluation": {
      "score": 8,
      "correctness": "The answer is technically accurate...",
      "strengths": ["Clear explanation", "Good examples"],
      "areas_for_improvement": ["Could mention memory efficiency"],
      "feedback": "Good answer demonstrating solid understanding..."
    },
    "next_question": {
      "question_number": 2,
      "question": "How would you implement a singleton pattern in Python?",
      "difficulty": "medium",
      "topic": "Design Patterns"
    },
    "is_complete": false,
    "questions_remaining": 4
  }
}
```

### 3. Get Final Report

After answering all questions:

```bash
curl -X GET "http://localhost:8000/api/interview/report/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "interview_id": "550e8400-e29b-41d4-a716-446655440000",
    "overall_score": 7.6,
    "total_questions": 5,
    "questions_answered": 5,
    "detailed_feedback": "The candidate demonstrated solid Python knowledge...",
    "strong_areas": ["Core Python concepts", "Problem-solving"],
    "weak_areas": ["Advanced topics like metaclasses"],
    "recommendations": [
      "Study advanced Python features",
      "Practice system design problems"
    ],
    "hire_recommendation": "Hire - Strong mid-level candidate",
    "question_wise_breakdown": [...]
  }
}
```

## Interview Configuration Options

### Experience Levels
- `junior` - Entry-level, focus on fundamentals
- `mid` - Intermediate, includes design decisions
- `senior` - Advanced, architecture and leadership

### Difficulty Levels
- `easy` - Basic concepts and simple problems
- `medium` - Moderate complexity with trade-offs
- `hard` - Complex scenarios and edge cases

### Adaptive Difficulty
The system automatically adjusts difficulty based on performance:
- Score ≥ 8: Difficulty increases
- Score ≤ 4: Difficulty decreases

## Response Format

All API responses follow this structure:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

Error responses:

```json
{
  "success": false,
  "data": null,
  "error": "Error message"
}
```

## Production Deployment

1. **Set secure environment variables:**
   ```bash
   SECRET_KEY="strong-random-key"
   OPENAI_API_KEY="sk-..."
   DEBUG=false
   ```

2. **Use production database** (migrate from SQLite):
   ```bash
   DATABASE_URL="postgresql+asyncpg://user:pass@host/db"
   ```

3. **Run with Gunicorn:**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

4. **For multiple instances**, migrate interview storage to Redis:
   - Install `redis` and `aioredis`
   - Update `app/interview/storage.py` to use Redis

5. **Configure CORS** for your frontend domain

## Cost Optimization

- Uses **gpt-4o-mini** for cost efficiency (~$0.15 per 1M input tokens)
- Estimated cost per interview (5 questions): ~$0.01-0.02
- Consider caching common questions for further savings

## License

MIT License
