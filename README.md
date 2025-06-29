# 🩸 Blood Test Analyzer: The Most Entertaining AI Doctor Ever!

## 🚀 Project Setup & Usage

### 1. Install Requirements
```sh
pip install -r requirements.txt
```

### 2. Setup Redis (for Queue Worker)
```sh
# Install Redis (Windows: use WSL or Docker)
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server

# Start Redis
redis-server
```

### 3. Setup Database
```sh
# SQLite database will be created automatically
# For production, consider PostgreSQL or MySQL
```

### 4. Start Celery Worker
```sh
# Start Celery worker for background processing
celery -A celery_app worker --loglevel=info
```

### 5. Start Celery Beat (Optional - for scheduled tasks)
```sh
# Start Celery beat for scheduled cleanup tasks
celery -A celery_app beat --loglevel=info
```

### 6. Run the API
```sh
uvicorn main:app --reload
```

### 7. Monitor with Flower (Optional)
```sh
# Start Flower for task monitoring
celery -A celery_app flower
# Visit: http://localhost:5555
```

## 🧠 What Makes This Unique?
- **Agents with Personality:** Each AI expert is quirky, dramatic, and sometimes a little too creative.
- **Creative Output:** Expect wild diagnoses, sales pitches, memes, and even conspiracy theories.
- **Flexible Analysis:** Choose summary, nutrition, exercise, or verification—each with its own flavor.
- **Queue Worker Model:** Handles concurrent requests with Redis and Celery.
- **Database Integration:** Stores all analysis results and user data for history and analytics.

## 🐛 Bugs Fixed
- LLM was undefined—now uses OpenAI GPT-3.5 Turbo.
- PDFLoader import and tool registration fixed.
- Agents and tasks now use the correct tools and personalities.
- File path flows through the system, so your PDF is actually analyzed.
- API now supports multiple analysis types.
- Requirements and README typos fixed.

## 📚 API Documentation

### Core Endpoints
- **POST `/analyze`** - Asynchronous analysis (uses queue)
  - `file`: PDF file (required)
  - `query`: string (optional)
  - `analysis_type`: string (optional, one of `summary`, `nutrition`, `exercise`, `verification`)
  - `user_id`: string (optional)
  - **Returns:** Task ID for status tracking

- **POST `/analyze/sync`** - Synchronous analysis (immediate results)
  - Same parameters as above
  - **Returns:** Immediate analysis results

- **GET `/status/{task_id}`** - Check background task status
  - **Returns:** Task state and progress/result

### Analytics & History
- **GET `/history/{user_id}`** - Get user's analysis history
- **GET `/analytics`** - Get system-wide analytics and statistics

### Health Check
- **GET `/`** - API health check

## 🎯 Bonus Features Implemented

### ✅ Queue Worker Model (Celery + Redis)
- **Background Processing:** Handle multiple concurrent requests
- **Task Monitoring:** Track progress and status of long-running analyses
- **Scalability:** Easy to scale workers across multiple machines
- **Error Handling:** Robust error handling and retry mechanisms
- **File Cleanup:** Automated cleanup of old uploaded files

### ✅ Database Integration (SQLAlchemy + SQLite)
- **Analysis Storage:** Store all analysis results with metadata
- **User Tracking:** Track user analysis history and preferences
- **Analytics:** System-wide statistics and performance metrics
- **Audit Trail:** Complete history of all analyses performed
- **Performance Metrics:** Processing time and success rate tracking

## 🔧 Environment Variables
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 📊 System Architecture
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   FastAPI   │───▶│    Redis    │───▶│   Celery    │
│   Server    │    │   Queue     │    │   Workers   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   SQLite    │    │   Flower    │    │  CrewAI     │
│  Database   │    │  Monitor    │    │  Analysis   │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 🚀 Production Deployment
- Use PostgreSQL instead of SQLite
- Deploy Redis on a separate server
- Use multiple Celery workers
- Add authentication and rate limiting
- Implement proper logging and monitoring

---

**Enjoy the most entertaining blood test analysis ever!** 🩸✨
