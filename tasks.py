from celery_app import celery_app
from database import SessionLocal, AnalysisResult, User
from main import run_crew
import time
import uuid

@celery_app.task(bind=True)
def analyze_blood_report_task(self, file_path: str, query: str, analysis_type: str, user_id: str = None):
    
    start_time = time.time()
    
    try:
       
        self.update_state(state='PROGRESS', meta={'status': 'Analyzing blood report...'})
        
        result = run_crew(query=query, file_path=file_path, analysis_type=analysis_type)
        
       
        processing_time = time.time() - start_time
        
       
        db = SessionLocal()
        try:
            analysis_result = AnalysisResult(
                user_id=user_id or str(uuid.uuid4()),
                file_name=file_path.split('/')[-1],
                query=query,
                analysis_type=analysis_type,
                result=str(result),
                processing_time=processing_time,
                status="completed"
            )
            db.add(analysis_result)
            db.commit()
            
           
            if user_id:
                user = db.query(User).filter(User.user_id == user_id).first()
                if user:
                    user.total_analyses += 1
                    db.commit()
                    
        finally:
            db.close()
        
        return {
            'status': 'success',
            'result': str(result),
            'processing_time': processing_time,
            'analysis_id': analysis_result.id if 'analysis_result' in locals() else None
        }
        
    except Exception as e:
       
        db = SessionLocal()
        try:
            analysis_result = AnalysisResult(
                user_id=user_id or str(uuid.uuid4()),
                file_name=file_path.split('/')[-1] if file_path else "unknown",
                query=query,
                analysis_type=analysis_type,
                result=f"Error: {str(e)}",
                processing_time=time.time() - start_time,
                status="failed"
            )
            db.add(analysis_result)
            db.commit()
        finally:
            db.close()
        
        raise e

@celery_app.task
def cleanup_old_files():
   
    import os
    import glob
    from datetime import datetime, timedelta
    

    cutoff_time = datetime.now() - timedelta(hours=1)
    data_dir = "data"
    
    if os.path.exists(data_dir):
        for file_path in glob.glob(os.path.join(data_dir, "blood_test_report_*.pdf")):
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if file_time < cutoff_time:
                try:
                    os.remove(file_path)
                except:
                    pass 