import io
import PyPDF2
from fastapi import UploadFile
import docx
import csv

async def extract_text_from_file(file: UploadFile) -> str:
    """
    Extract text from various file formats
    """
    content_type = file.content_type
    filename = file.filename.lower()
    
    # Read file content into memory
    file_bytes = await file.read()
    # Reset file pointer for other potential uses if needed, 
    # but here we usually don't need it as we've read it all.
    # However, since we are in an async function, we should be careful.
    
    try:
        if content_type == "application/pdf" or filename.endswith(".pdf"):
            return extract_text_from_pdf(file_bytes)
        
        elif content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ] or filename.endswith((".docx", ".doc")):
            return extract_text_from_docx(file_bytes)
        
        elif content_type == "text/plain" or filename.endswith(".txt"):
            return file_bytes.decode("utf-8", errors="ignore")
        
        elif content_type == "text/csv" or filename.endswith(".csv"):
            return extract_text_from_csv(file_bytes)
        
        else:
            # Try decoding as text as a last resort
            try:
                return file_bytes.decode("utf-8")
            except:
                return f"[Unsupported file type: {content_type}]"
                
    except Exception as e:
        print(f"Error extracting text from {filename}: {e}")
        return f"[Error extracting text: {str(e)}]"

def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        text = f"[PDF Extraction Error: {str(e)}]"
    return text

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"[DOCX Extraction Error: {str(e)}]"

def extract_text_from_csv(file_bytes: bytes) -> str:
    try:
        content = file_bytes.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(content))
        return "\n".join([",".join(row) for row in reader])
    except Exception as e:
        return f"[CSV Extraction Error: {str(e)}]"
