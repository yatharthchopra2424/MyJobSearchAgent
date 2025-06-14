import os
import platform
import pytesseract

def configure_tesseract():
    if platform.system() == "Windows":
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
