from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import uuid
import asyncio

from crewai import Crew, Process
from agents import doctor, nutritionist, exercise_specialist, verifier
from task import help_patients, nutrition_analysis, exercise_planning, verification
from tools import BloodTestReportTool
from database import get_db, AnalysisResult, User
from tasks import analyze_blood_report_task

app = FastAPI(title="Blood Test Report Analyser - Enhanced Edition")

def run_crew(query: str, file_path: str = "data/sample.pdf", analysis_type: str = "summary"):
    """To run the whole crew with the selected analysis type"""
    blood_tool = BloodTestReportTool()
    
    # Map analysis type to task and agent
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

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Blood Test Report Analyser API is running - Enhanced with Queue & Database!"}

@app.post("/analyze")
async def analyze_blood_report(
    file: UploadFile = File(...),
    query: str = Form(default="Summarise my Blood Test Report"),
    analysis_type: str = Form(default="summary"),
    user_id: str = Form(default=None),
    db: Session = Depends(get_db)
):
    """Analyze blood test report and provide creative health recommendations"""
    file_id = str(uuid.uuid4())
    file_path = f"data/blood_test_report_{file_id}.pdf"
    
    try:
        os.makedirs("data", exist_ok=True)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
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
            "file_processed": file.filename
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing blood report: {str(e)}")

@app.post("/analyze/sync")
async def analyze_blood_report_sync(
    file: UploadFile = File(...),
    query: str = Form(default="Summarise my Blood Test Report"),
    analysis_type: str = Form(default="summary"),
    user_id: str = Form(default=None),
    db: Session = Depends(get_db)
):
    """Synchronous analysis for immediate results"""
    file_id = str(uuid.uuid4())
    file_path = f"data/blood_test_report_{file_id}.pdf"
    
    try:
        os.makedirs("data", exist_ok=True)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        if not query:
            query = "Summarise my Blood Test Report"
        
        response = run_crew(query=query.strip(), file_path=file_path, analysis_type=analysis_type)
        
        # Store in database
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
        
        return {
            "status": "success",
            "query": query,
            "analysis_type": analysis_type,
            "creative_analysis": str(response),
            "file_processed": file.filename,
            "analysis_id": analysis_result.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing blood report: {str(e)}")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a background task"""
    from celery.result import AsyncResult
    from tasks import celery_app
    
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == 'PENDING':
        response = {
            'state': task_result.state,
            'status': 'Task is pending...'
        }
    elif task_result.state == 'PROGRESS':
        response = {
            'state': task_result.state,
            'status': task_result.info.get('status', ''),
            'progress': task_result.info.get('progress', 0)
        }
    elif task_result.state == 'SUCCESS':
        response = {
            'state': task_result.state,
            'result': task_result.result
        }
    else:
        response = {
            'state': task_result.state,
            'error': str(task_result.info)
        }
    
    return response

@app.get("/history/{user_id}")
async def get_analysis_history(user_id: str, db: Session = Depends(get_db)):
    """Get analysis history for a user"""
    analyses = db.query(AnalysisResult).filter(AnalysisResult.user_id == user_id).order_by(AnalysisResult.created_at.desc()).all()
    
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

@app.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get system analytics"""
    total_analyses = db.query(AnalysisResult).count()
    completed_analyses = db.query(AnalysisResult).filter(AnalysisResult.status == "completed").count()
    failed_analyses = db.query(AnalysisResult).filter(AnalysisResult.status == "failed").count()
    
    # Analysis type distribution
    analysis_types = db.query(AnalysisResult.analysis_type).all()
    type_counts = {}
    for analysis_type in analysis_types:
        type_counts[analysis_type[0]] = type_counts.get(analysis_type[0], 0) + 1
    
    return {
        "total_analyses": total_analyses,
        "completed_analyses": completed_analyses,
        "failed_analyses": failed_analyses,
        "success_rate": (completed_analyses / total_analyses * 100) if total_analyses > 0 else 0,
        "analysis_type_distribution": type_counts
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)