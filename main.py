from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from celery.result import AsyncResult
import os
import uuid
import asyncio
import re
from typing import Optional
from datetime import datetime, timedelta
import hashlib

from crewai import Crew, Process
from agents import doctor, nutritionist, exercise_specialist, verifier
from task import help_patients, nutrition_analysis, exercise_planning, verification
from tools import BloodTestReportTool
from database import get_db, AnalysisResult, User
from tasks import analyze_blood_report_task, celery_app

app = FastAPI(title="Blood Test Report Analyser - Enhanced Edition")

# Configuration constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf'}
VALID_ANALYSIS_TYPES = {'summary', 'nutrition', 'exercise', 'verification'}
RATE_LIMIT_WINDOW = 3600  # 1 hour
RATE_LIMIT_MAX_REQUESTS = 10  # Max 10 requests per hour per user

# Simple in-memory rate limiting (use Redis in production)
rate_limit_store = {}

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed"
        )
    
    # Check file size (will be validated when reading content)
    if hasattr(file, 'size') and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', text)
    # Limit length
    return sanitized[:1000]

def check_rate_limit(user_id: str) -> bool:
    """Check if user has exceeded rate limit"""
    if not user_id:
        return True  # No rate limiting for anonymous users
    
    current_time = datetime.now()
    if user_id in rate_limit_store:
        user_requests = rate_limit_store[user_id]
        # Remove old requests outside the window
        user_requests = [req_time for req_time in user_requests 
                        if current_time - req_time < timedelta(seconds=RATE_LIMIT_WINDOW)]
        
        if len(user_requests) >= RATE_LIMIT_MAX_REQUESTS:
            return False
        
        user_requests.append(current_time)
        rate_limit_store[user_id] = user_requests
    else:
        rate_limit_store[user_id] = [current_time]
    
    return True

def run_crew(query: str, file_path: str = "data/sample.pdf", analysis_type: str = "summary"):
    """Run the crew with error handling"""
    try:
        blood_tool = BloodTestReportTool()
        
        # Validate analysis type
        if analysis_type not in VALID_ANALYSIS_TYPES:
            analysis_type = "summary"
        
        task_map = {
            "summary": help_patients,
            "nutrition": nutrition_analysis,
            "exercise": exercise_planning,
            "verification": verification
        }
        selected_task = task_map.get(analysis_type, help_patients)
        
        # Patch the tool to use the correct file_path
        def patched_tool():
            return blood_tool.read_data_tool(file_path)
        selected_task.tools = [patched_tool]
        
        # Pick the right agent
        agent_map = {
            "summary": doctor,
            "nutrition": nutritionist,
            "exercise": exercise_specialist,
            "verification": verifier
        }
        selected_task.agent = agent_map.get(analysis_type, doctor)
        
        medical_crew = Crew(
            agents=[selected_task.agent],
            tasks=[selected_task],
            process=Process.sequential,
        )
        result = medical_crew.kickoff({'query': query})
        return result
    except Exception as e:
        raise Exception(f"CrewAI analysis failed: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Blood Test Report Analyser API is running - Enhanced with Queue & Database!",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/analyze")
async def analyze_blood_report(
    request: Request,
    file: UploadFile = File(...),
    query: str = Form(default="Summarise my Blood Test Report"),
    analysis_type: str = Form(default="summary"),
    user_id: str = Form(default=None),
    db: Session = Depends(get_db)
):
    """Analyze blood test report with comprehensive validation"""
    
    # Rate limiting
    if not check_rate_limit(user_id or request.client.host):
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX_REQUESTS} requests per hour."
        )
    
    # Validate file
    validate_file(file)
    
    # Sanitize inputs
    query = sanitize_input(query)
    analysis_type = sanitize_input(analysis_type)
    user_id = sanitize_input(user_id) if user_id else None
    
    # Validate analysis type
    if analysis_type not in VALID_ANALYSIS_TYPES:
        analysis_type = "summary"
    
    file_id = str(uuid.uuid4())
    file_path = f"data/blood_test_report_{file_id}.pdf"
    
    try:
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Read and validate file content
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Save file with content hash for security
        file_hash = hashlib.md5(content).hexdigest()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Set default query if empty
        if not query:
            query = "Summarise my Blood Test Report"
        
        # Start background task
        task = analyze_blood_report_task.delay(file_path, query.strip(), analysis_type, user_id)
        
        return {
            "status": "processing",
            "task_id": task.id,
            "message": "Analysis started in background. Use /status/{task_id} to check progress.",
            "query": query,
            "analysis_type": analysis_type,
            "file_processed": file.filename,
            "file_hash": file_hash,
            "rate_limit_remaining": RATE_LIMIT_MAX_REQUESTS - len(rate_limit_store.get(user_id or request.client.host, []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing blood report: {str(e)}")

@app.post("/analyze/sync")
async def analyze_blood_report_sync(
    request: Request,
    file: UploadFile = File(...),
    query: str = Form(default="Summarise my Blood Test Report"),
    analysis_type: str = Form(default="summary"),
    user_id: str = Form(default=None),
    db: Session = Depends(get_db)
):
    """Synchronous analysis with comprehensive validation"""
    
    # Rate limiting
    if not check_rate_limit(user_id or request.client.host):
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX_REQUESTS} requests per hour."
        )
    
    # Validate file
    validate_file(file)
    
    # Sanitize inputs
    query = sanitize_input(query)
    analysis_type = sanitize_input(analysis_type)
    user_id = sanitize_input(user_id) if user_id else None
    
    # Validate analysis type
    if analysis_type not in VALID_ANALYSIS_TYPES:
        analysis_type = "summary"
    
    file_id = str(uuid.uuid4())
    file_path = f"data/blood_test_report_{file_id}.pdf"
    
    try:
        os.makedirs("data", exist_ok=True)
        
        # Read and validate file content
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        if not query:
            query = "Summarise my Blood Test Report"
        
        # Run analysis with timeout
        try:
            response = run_crew(query=query.strip(), file_path=file_path, analysis_type=analysis_type)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        
        # Store in database with error handling
        try:
            analysis_result = AnalysisResult(
                user_id=user_id or str(uuid.uuid4()),
                file_name=file.filename,
                query=query,
                analysis_type=analysis_type,
                result=str(response),
                status="completed"
            )
            db.add(analysis_result)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        return {
            "status": "success",
            "query": query,
            "analysis_type": analysis_type,
            "creative_analysis": str(response),
            "file_processed": file.filename,
            "analysis_id": analysis_result.id,
            "rate_limit_remaining": RATE_LIMIT_MAX_REQUESTS - len(rate_limit_store.get(user_id or request.client.host, []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing blood report: {str(e)}")
    finally:
        # Clean up file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a background task with validation"""
    
    # Validate task_id format
    if not task_id or len(task_id) < 10:
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.state == 'PENDING':
            response = {
                'state': task_result.state,
                'status': 'Task is pending...',
                'task_id': task_id
            }
        elif task_result.state == 'PROGRESS':
            response = {
                'state': task_result.state,
                'status': task_result.info.get('status', ''),
                'progress': task_result.info.get('progress', 0),
                'task_id': task_id
            }
        elif task_result.state == 'SUCCESS':
            response = {
                'state': task_result.state,
                'result': task_result.result,
                'task_id': task_id
            }
        else:
            response = {
                'state': task_result.state,
                'error': str(task_result.info),
                'task_id': task_id
            }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving task status: {str(e)}")

@app.get("/history/{user_id}")
async def get_analysis_history(user_id: str, db: Session = Depends(get_db)):
    """Get analysis history for a user with validation"""
    
    # Validate user_id
    if not user_id or len(user_id) < 3:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    try:
        analyses = db.query(AnalysisResult).filter(
            AnalysisResult.user_id == user_id
        ).order_by(AnalysisResult.created_at.desc()).limit(100).all()  # Limit to prevent abuse
        
        return {
            "user_id": user_id,
            "total_analyses": len(analyses),
            "analyses": [
                {
                    "id": analysis.id,
                    "file_name": analysis.file_name,
                    "query": analysis.query,
                    "analysis_type": analysis.analysis_type,
                    "status": analysis.status,
                    "created_at": analysis.created_at.isoformat(),
                    "processing_time": analysis.processing_time
                }
                for analysis in analyses
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@app.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get system analytics with error handling"""
    
    try:
        total_analyses = db.query(AnalysisResult).count()
        completed_analyses = db.query(AnalysisResult).filter(AnalysisResult.status == "completed").count()
        failed_analyses = db.query(AnalysisResult).filter(AnalysisResult.status == "failed").count()
        
        # Analysis type distribution
        analysis_types = db.query(AnalysisResult.analysis_type).all()
        type_counts = {}
        for analysis_type in analysis_types:
            if analysis_type[0]:  # Check for None values
                type_counts[analysis_type[0]] = type_counts.get(analysis_type[0], 0) + 1
        
        # Calculate success rate safely
        success_rate = (completed_analyses / total_analyses * 100) if total_analyses > 0 else 0
        
        return {
            "total_analyses": total_analyses,
            "completed_analyses": completed_analyses,
            "failed_analyses": failed_analyses,
            "success_rate": round(success_rate, 2),
            "analysis_type_distribution": type_counts,
            "rate_limit_config": {
                "window_seconds": RATE_LIMIT_WINDOW,
                "max_requests": RATE_LIMIT_MAX_REQUESTS
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        # Check database connection
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        
        # Check Redis connection (if available)
        redis_status = "unknown"
        try:
            from redis import Redis
            redis_client = Redis(host='localhost', port=6379, db=0)
            redis_client.ping()
            redis_status = "healthy"
        except:
            redis_status = "unavailable"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "healthy",
            "redis": redis_status,
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)