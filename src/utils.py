# filepath: src/utils.py
import pytesseract
import cv2
from pdf2image import convert_from_path
import os
from PIL import Image

# Set tesseract path if not in PATH (uncomment and adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def pdf_to_images(pdf_path, output_folder=None, fmt='png'):
    """
    Converts a PDF file to images (one per page).
    Args:
        pdf_path (str): Path to the PDF file.
        output_folder (str, optional): Folder to save images. If None, images are not saved to disk.
        fmt (str): Image format (e.g., 'png', 'jpeg').
    Returns:
        List of PIL.Image objects.
    """
    images = convert_from_path(pdf_path)
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
        for i, img in enumerate(images):
            img.save(f"{output_folder}/page_{i+1}.{fmt}", fmt.upper())
    return images

def extract_text_from_invoice(image):
    """
    Extract text from an image file path or a PIL Image.
    Args:
        image (str or PIL.Image.Image): Path to image or PIL Image object.
    Returns:
        str: Extracted text.
    """
    if isinstance(image, str):
        img = cv2.imread(image)
        if img is None:
            raise FileNotFoundError(f"Image not found at path: {image}")
        text = pytesseract.image_to_string(img)
    elif isinstance(image, Image.Image):
        text = pytesseract.image_to_string(image)
    else:
        raise ValueError("Input must be a file path or PIL.Image.Image")
    return text



def extract_text_from_any_file(file_path):
    """
    Extracts text from an image or PDF file.
    Args:
        file_path (str): Path to the file (image or PDF).
    Returns:
        str: Extracted text.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        images = pdf_to_images(file_path)
        texts = [extract_text_from_invoice(img) for img in images]
        return "\n".join(texts)
    else:
        return extract_text_from_invoice(file_path)