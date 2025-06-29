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

def preprocess_image_for_ocr(img_path, return_scale=False):
    """
    Preprocess the image for OCR: denoise, sharpen, enhance contrast, binarize, and resize if necessary.
    Args:
        img_path (str): Path to the image file.
        return_scale (bool): If True, also return the scale factor (w_scale, h_scale) applied.
    Returns:
        PIL.Image.Image: Preprocessed image.
        (optional) (w_scale, h_scale): scale factors for width and height
    """
    cv_img = cv2.imread(img_path)
    if cv_img is None:
        return (None, None, None) if return_scale else None
    # Denoise
    cv_img = cv2.fastNlMeansDenoisingColored(cv_img, None, 10, 10, 7, 21)
    # Sharpen
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    cv_img = cv2.filter2D(cv_img, -1, kernel)
    # Convert to grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    # Contrast enhancement (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    # Adaptive thresholding
    try:
        bin_img = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 15
        )
    except Exception:
        bin_img = gray
    h, w = bin_img.shape
    orig_h, orig_w = h, w
    w_scale = h_scale = 1.0
    if min(h, w) < 1000:
        scale = 1000.0 / min(h, w)
        bin_img = cv2.resize(bin_img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)
        h, w = bin_img.shape
        w_scale = w / orig_w
        h_scale = h / orig_h
    image = Image.fromarray(bin_img).convert("RGB")
    if return_scale:
        return image, w_scale, h_scale
    return image

def normalize_bbox(bbox, width, height):
    x0, y0, x1, y1 = bbox
    return [
        int(1000 * x0 / width),
        int(1000 * y0 / height),
        int(1000 * x1 / width),
        int(1000 * y1 / height)
    ]

def ocr_tokens_and_bboxes(image):
    """
    Perform OCR on both the original and inverted grayscale images, merge tokens.
    Returns:
        List of dicts with text, norm bbox, orig bbox, position
    """
    width, height = image.size
    # Convert to grayscale
    gray = np.array(image.convert("L"))
    # OCR on original
    data1 = pytesseract.image_to_data(Image.fromarray(gray), output_type=pytesseract.Output.DICT)
    # OCR on inverted
    inv_gray = cv2.bitwise_not(gray)
    data2 = pytesseract.image_to_data(Image.fromarray(inv_gray), output_type=pytesseract.Output.DICT)
    tokens = []
    seen = set()
    for data in [data1, data2]:
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            if not text or all(c in ",.-|_:;" for c in text):
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            if w == 0 or h == 0:
                continue
            x0, y0, x1, y1 = x, y, x + w, y + h
            key = (text, x0, y0, x1, y1)
            if key in seen:
                continue
            seen.add(key)
            tokens.append({
                "text": text,
                "bbox": normalize_bbox([x0, y0, x1, y1], width, height),
                "orig_bbox": [x0, y0, x1, y1],
                "position": (y, x)
            })
    return tokens

def bbox_iou(boxA, boxB):
    # Compute intersection over union between two boxes
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH
    if interArea == 0:
        return 0.0
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return interArea / float(boxAArea + boxBArea - interArea)

def bio_tag_tokens(tokens, regions, w_scale=1.0, h_scale=1.0, iou_threshold=0.1, debug=False):
    """
    BIO-tag tokens based on overlap with annotation regions.
    Args:
        tokens (list): List of tokens (with 'orig_bbox').
        regions (list): List of regions with 'bbox' (COCO format) and 'label'.
        w_scale, h_scale: scaling factors applied to the image (and thus to COCO boxes)
        iou_threshold (float): IOU threshold for matching.
        debug (bool): If True, print debug info.
    Returns:
        List of BIO tags for the tokens.
    """
    labels = ["O"] * len(tokens)
    for region in regions:
        rx, ry, rw, rh = region['bbox']
        # Scale COCO box to OCR image size
        rx, ry, rw, rh = rx * w_scale, ry * h_scale, rw * w_scale, rh * h_scale
        region_box = [rx, ry, rx + rw, ry + rh]
        region_label = region['label']
        matched_indices = []
        for i, t in enumerate(tokens):
            token_box = t["orig_bbox"]
            iou = bbox_iou(token_box, region_box)
            if debug and iou > 0:
                print(f"Token: {t['text']} | Token box: {token_box} | Region: {region_label} | Region box: {region_box} | IOU: {iou:.3f}")
            if iou > iou_threshold:
                matched_indices.append(i)
        if matched_indices:
            labels[matched_indices[0]] = f"B-{region_label}"
            for i in matched_indices[1:]:
                labels[i] = f"I-{region_label}"
    if debug and all(l == "O" for l in labels):
        print("[DEBUG] No tokens matched any region. Check coordinate systems and IOU threshold.")
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

