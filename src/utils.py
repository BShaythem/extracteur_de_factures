# filepath: src/utils.py
import pytesseract
import cv2
import os
from PIL import Image
import fitz  # PyMuPDF
import numpy as np

# Set tesseract path if not in PATH (uncomment and adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def pdf_to_images(pdf_path, output_folder=None, fmt='png'):
    """
    Converts a PDF file to images (one per page) using PyMuPDF.
    Args:
        pdf_path (str): Path to the PDF file.
        output_folder (str, optional): Folder to save images. If None, images are not saved to disk.
        fmt (str): Image format (e.g., 'png', 'jpeg').
    Returns:
        List of PIL.Image objects.
    """
    doc = fitz.open(pdf_path)
    images = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)
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

def preprocess_image_for_ocr(img_path):
    """
    Preprocess the image for OCR: convert to grayscale, apply adaptive thresholding, and resize if necessary.
    Args:
        img_path (str): Path to the image file.
    Returns:
        PIL.Image.Image: Preprocessed image.
    """
    cv_img = cv2.imread(img_path)
    if cv_img is None:
        return None
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 31, 15)
    h, w = bin_img.shape
    if min(h, w) < 1000:
        scale = 1000.0 / min(h, w)
        bin_img = cv2.resize(bin_img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)
    image = Image.fromarray(bin_img)
    return image

def ocr_tokens_and_bboxes(image):
    """
    Perform OCR on the image and extract tokens and their bounding boxes.
    Args:
        image (PIL.Image.Image): Input image.
    Returns:
        List of tokens with bounding box information.
    """
    width, height = image.size
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    tokens = []
    for i in range(len(ocr_data['text'])):
        text = ocr_data['text'][i]
        if not text.strip():
            continue
        x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
        x0, y0, x1, y1 = x, y, x + w, y + h
        norm_box = [
            int(1000 * x0 / width),
            int(1000 * y0 / height),
            int(1000 * x1 / width),
            int(1000 * y1 / height)
        ]
        tokens.append({
            "text": text,
            "bbox": norm_box,
            "orig_bbox": [x0, y0, x1, y1],
            "position": (y, x)
        })
    return tokens

def bio_tag_tokens(tokens, regions):
    """
    Apply BIO tagging to the tokens based on the given regions.
    Args:
        tokens (list): List of tokens.
        regions (list): List of regions with bounding box information.
    Returns:
        List of BIO tags for the tokens.
    """
    labels = ["O"] * len(tokens)
    # Ensure region labels are used exactly as in COCO (case, spaces, etc.)
    for region in regions:
        rx, ry, rw, rh = region['bbox']
        rx1, ry1 = rx + rw, ry + rh
        region_label = str(region['label'])  # Use as-is from COCO
        inside = []
        for idx, t in enumerate(tokens):
            tx0, ty0, tx1, ty1 = t["orig_bbox"]
            if not (tx1 < rx or tx0 > rx1 or ty1 < ry or ty0 > ry1):
                inside.append(idx)
        if inside:
            labels[inside[0]] = f"B-{region_label}"
            for idx in inside[1:]:
                labels[idx] = f"I-{region_label}"
    return labels

def deskew_image_and_bboxes(image, bboxes=None):
    """
    Deskew the image using OpenCV and rotate bounding boxes accordingly.
    Args:
        image (PIL.Image.Image): Input image.
        bboxes (list, optional): List of bounding boxes [[x0, y0, x1, y1], ...] in pixel coordinates.
    Returns:
        deskewed_image (PIL.Image.Image): Deskewed image.
        rotated_bboxes (list): Rotated bounding boxes (if bboxes provided), else None.
        angle (float): Rotation angle in degrees (counterclockwise).
    """
    import cv2
    import numpy as np
    from PIL import Image

    # Convert PIL to OpenCV
    img_cv = np.array(image)
    if img_cv.ndim == 3 and img_cv.shape[2] == 3:
        gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_cv
    # Threshold to get binary image
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Invert: text should be white
    bw = 255 - bw
    # Find coordinates of all non-zero pixels
    coords = np.column_stack(np.where(bw > 0))
    angle = 0.0
    if len(coords) > 0:
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
    # Rotate image
    (h, w) = img_cv.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated_cv = cv2.warpAffine(img_cv, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    deskewed_image = Image.fromarray(rotated_cv)
    # Rotate bboxes if provided
    rotated_bboxes = None
    if bboxes is not None:
        rotated_bboxes = []
        for bbox in bboxes:
            # bbox: [x0, y0, x1, y1]
            points = np.array([
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]]
            ])
            ones = np.ones(shape=(len(points), 1))
            points_ones = np.hstack([points, ones])
            transformed = M.dot(points_ones.T).T
            x_coords = transformed[:, 0]
            y_coords = transformed[:, 1]
            x0r, y0r, x1r, y1r = min(x_coords), min(y_coords), max(x_coords), max(y_coords)
            rotated_bboxes.append([int(x0r), int(y0r), int(x1r), int(y1r)])
    return deskewed_image, rotated_bboxes, angle

