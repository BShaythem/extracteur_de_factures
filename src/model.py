import pytesseract
import cv2
from utils import extract_text_from_invoice, pdf_to_images, extract_text_from_any_file

# Si besoin, décommentez et adaptez le chemin Tesseract sous Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

