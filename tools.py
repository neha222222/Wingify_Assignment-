import os
from dotenv import load_dotenv
load_dotenv()

from crewai_tools import tools
from crewai_tools.tools.serper_dev_tool import SerperDevTool
from langchain.document_loaders import PDFLoader
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

search_tool = SerperDevTool()

class BloodTestReportTool:
    def read_data_tool(self, path='data/sample.pdf'):
        """Tool to read data from a pdf file from a path with comprehensive error handling

        Args:
            path (str, optional): Path of the pdf file. Defaults to 'data/sample.pdf'.

        Returns:
            str: Full Blood Test report file or error message
        """
        try:
            # Validate file exists
            if not os.path.exists(path):
                logger.error(f"File not found: {path}")
                return f"Error: File not found at {path}"
            
            # Validate file is readable
            if not os.access(path, os.R_OK):
                logger.error(f"File not readable: {path}")
                return f"Error: File not readable at {path}"
            
            # Check file size
            file_size = os.path.getsize(path)
            if file_size == 0:
                logger.error(f"File is empty: {path}")
                return "Error: File is empty"
            
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                logger.error(f"File too large: {path} ({file_size} bytes)")
                return "Error: File too large (max 50MB)"
            
            # Load PDF with error handling
            try:
                docs = PDFLoader(file_path=path).load()
            except Exception as e:
                logger.error(f"PDF loading failed: {str(e)}")
                return f"Error: Failed to load PDF - {str(e)}"
            
            if not docs:
                logger.warning(f"No content extracted from PDF: {path}")
                return "Warning: No content could be extracted from the PDF"
            
            # Process content with safety checks
            full_report = ""
            total_pages = len(docs)
            
            for i, data in enumerate(docs):
                try:
                    content = data.page_content
                    
                    # Validate content
                    if not content or len(content.strip()) == 0:
                        logger.warning(f"Empty page {i+1} in PDF: {path}")
                        continue
                    
                    # Clean and format the report data
                    # Remove extra whitespaces and format properly
                    while "\n\n" in content:
                        content = content.replace("\n\n", "\n")
                    
                    # Remove excessive whitespace
                    content = ' '.join(content.split())
                    
                    # Add page information
                    page_info = f"\n--- Page {i+1} of {total_pages} ---\n"
                    full_report += page_info + content + "\n"
                    
                except Exception as e:
                    logger.error(f"Error processing page {i+1}: {str(e)}")
                    full_report += f"\n--- Page {i+1} Error: {str(e)} ---\n"
            
            # Final validation
            if not full_report.strip():
                logger.error(f"No valid content extracted from PDF: {path}")
                return "Error: No valid content could be extracted from the PDF"
            
            # Truncate if too long (prevent memory issues)
            if len(full_report) > 100000:  # 100KB limit
                logger.warning(f"Content truncated due to size: {path}")
                full_report = full_report[:100000] + "\n... [Content truncated due to size]"
            
            logger.info(f"Successfully processed PDF: {path} ({total_pages} pages)")
            return full_report
            
        except Exception as e:
            logger.error(f"Unexpected error processing PDF {path}: {str(e)}")
            return f"Error: Unexpected error processing PDF - {str(e)}"

class NutritionTool:
    async def analyze_nutrition_tool(blood_report_data):
        """Analyze nutrition from blood report data with error handling"""
        try:
            if not blood_report_data:
                return "Error: No blood report data provided"
            
            # Process and analyze the blood report data
            processed_data = blood_report_data
            
            # Clean up the data format safely
            try:
                i = 0
                while i < len(processed_data):
                    if processed_data[i:i+2] == "  ":  # Remove double spaces
                        processed_data = processed_data[:i] + processed_data[i+1:]
                    else:
                        i += 1
            except Exception as e:
                logger.warning(f"Error cleaning nutrition data: {str(e)}")
                # Continue with original data
            
            # TODO: Implement nutrition analysis logic here
            return "Nutrition analysis functionality to be implemented"
            
        except Exception as e:
            logger.error(f"Error in nutrition analysis: {str(e)}")
            return f"Error: Nutrition analysis failed - {str(e)}"

class ExerciseTool:
    async def create_exercise_plan_tool(blood_report_data):
        """Create exercise plan from blood report data with error handling"""
        try:
            if not blood_report_data:
                return "Error: No blood report data provided"
            
            # TODO: Implement exercise planning logic here
            return "Exercise planning functionality to be implemented"
            
        except Exception as e:
            logger.error(f"Error in exercise planning: {str(e)}")
            return f"Error: Exercise planning failed - {str(e)}"

class FileValidationTool:
    """Utility tool for file validation"""
    
    @staticmethod
    def validate_pdf_file(file_path: str) -> dict:
        """Validate PDF file and return status"""
        try:
            if not os.path.exists(file_path):
                return {"valid": False, "error": "File not found"}
            
            if not file_path.lower().endswith('.pdf'):
                return {"valid": False, "error": "Not a PDF file"}
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {"valid": False, "error": "File is empty"}
            
            if file_size > 50 * 1024 * 1024:  # 50MB
                return {"valid": False, "error": "File too large (max 50MB)"}
            
            return {"valid": True, "size": file_size}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """Get file information"""
        try:
            stat = os.stat(file_path)
            return {
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "readable": os.access(file_path, os.R_OK),
                "writable": os.access(file_path, os.W_OK)
            }
        except Exception as e:
            return {"error": str(e)}