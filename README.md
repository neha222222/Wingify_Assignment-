# 🩸 Blood Test Analyzer: The Most Entertaining AI Doctor Ever!

## 🚀 Project Setup & Usage

### 1. Install Requirements
```sh
pip install -r requirements.txt
```

### 2. Run the API
```sh
uvicorn main:app --reload
```

### 3. Use the API
- Visit: `http://localhost:8000/docs` for Swagger UI
- POST `/analyze` with:
  - `file`: Your blood test PDF
  - `query`: (Optional) Your health question
  - `analysis_type`: (Optional) `summary`, `nutrition`, `exercise`, or `verification`

## 🧠 What Makes This Unique?
- **Agents with Personality:** Each AI expert is quirky, dramatic, and sometimes a little too creative.
- **Creative Output:** Expect wild diagnoses, sales pitches, memes, and even conspiracy theories.
- **Flexible Analysis:** Choose summary, nutrition, exercise, or verification—each with its own flavor.

## 🐛 Bugs Fixed
- LLM was undefined—now uses OpenAI GPT-3.5 Turbo.
- PDFLoader import and tool registration fixed.
- Agents and tasks now use the correct tools and personalities.
- File path flows through the system, so your PDF is actually analyzed.
- API now supports multiple analysis types.
- Requirements and README typos fixed.

## 📚 API Documentation
- **POST `/analyze`**
  - `file`: PDF file (required)
  - `query`: string (optional)
  - `analysis_type`: string (optional, one of `summary`, `nutrition`, `exercise`, `verification`)
  - **Returns:** Creative, actionable, and sometimes hilarious health analysis.

## ✨ Bonus Ideas
- Add a queue worker (Celery/Redis) for concurrent requests.
- Integrate a database to store user results and feedback.
- Let users vote for the quirkiest diagnosis!

---

**Enjoy the most entertaining blood test analysis ever!**
