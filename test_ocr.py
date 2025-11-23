import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

try:
    print("Tesseract version:", pytesseract.get_tesseract_version())
    print("OCR working!")
except Exception as e:
    print("Error:", e)
