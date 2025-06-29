
import os
from dotenv import load_dotenv
load_dotenv()

from crewai_tools import tools
from crewai_tools.tools.serper_dev_tool import SerperDevTool
from langchain.document_loaders import PDFLoader


search_tool = SerperDevTool()


class BloodTestReportTool:
    def read_data_tool(self, path='data/sample.pdf'):
        """Tool to read data from a pdf file from a path

        Args:
            path (str, optional): Path of the pdf file. Defaults to 'data/sample.pdf'.

        Returns:
            str: Full Blood Test report file
        """
        
        docs = PDFLoader(file_path=path).load()

        full_report = ""
        for data in docs:
            
            content = data.page_content
            
            
            while "\n\n" in content:
                content = content.replace("\n\n", "\n")
                
            full_report += content + "\n"
            
        return full_report

class NutritionTool:
    async def analyze_nutrition_tool(blood_report_data):
        
        processed_data = blood_report_data
        
        
        i = 0
        while i < len(processed_data):
            if processed_data[i:i+2] == "  ":  # Remove double spaces
                processed_data = processed_data[:i] + processed_data[i+1:]
            else:
                i += 1
                
       
        return "Nutrition analysis functionality to be implemented"

class ExerciseTool:
    async def create_exercise_plan_tool(blood_report_data):        
       
        return "Exercise planning functionality to be implemented"