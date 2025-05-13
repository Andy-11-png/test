import os
import PyPDF2
from werkzeug.utils import secure_filename

def extract_text_from_pdf(pdf_file):
    """
    Extract text content from a PDF file
    """
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text.strip()
    except Exception as e:
        raise Exception(f"Error processing PDF: {str(e)}")

def save_pdf_file(pdf_file, upload_folder):
    """
    Save the PDF file and return the saved path
    """
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    filename = secure_filename(pdf_file.filename)
    file_path = os.path.join(upload_folder, filename)
    pdf_file.save(file_path)
    return file_path 