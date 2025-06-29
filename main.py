from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import os
import uuid
import asyncio

from crewai import Crew, Process
from agents import doctor, nutritionist, exercise_specialist, verifier
from task import help_patients, nutrition_analysis, exercise_planning, verification
from tools import BloodTestReportTool

app = FastAPI(title="Blood Test Report Analyser")

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
    return {"message": "Blood Test Report Analyser API is running"}

@app.post("/analyze")
async def analyze_blood_report(
    file: UploadFile = File(...),
    query: str = Form(default="Summarise my Blood Test Report"),
    analysis_type: str = Form(default="summary")
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
        response = run_crew(query=query.strip(), file_path=file_path, analysis_type=analysis_type)
        return {
            "status": "success",
            "query": query,
            "analysis_type": analysis_type,
            "creative_analysis": str(response),
            "file_processed": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing blood report: {str(e)}")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)