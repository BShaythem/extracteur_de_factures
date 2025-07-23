import os
import cv2
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
import paddle
from pdf2image import convert_from_path

# Initialize PaddleOCR (GPU/CPU is auto-detected by installed paddlepaddle)
ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=False)

def pdf_to_image(pdf_path, dpi=200):
    """
    Convert the first page of a PDF to a PIL image.
    """
    images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=1)
    if not images:
        raise ValueError("No pages found in PDF.")
    return images[0]

def preprocess_image_for_ocr(img_path_or_pil, return_scale=False, binarize=True):
    """
    Preprocess the image for OCR: denoise, sharpen, enhance contrast, binarize (optional), and resize if necessary.
    Accepts a file path or a PIL.Image.Image.
    """
    if isinstance(img_path_or_pil, Image.Image):
        cv_img = cv2.cvtColor(np.array(img_path_or_pil), cv2.COLOR_RGB2BGR)
    else:
        cv_img = cv2.imread(img_path_or_pil)
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
    if binarize:
        # Adaptive thresholding
        try:
            bin_img = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 31, 15
            )
        except Exception:
            bin_img = gray
    else:
        bin_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    h, w = bin_img.shape[:2] if binarize else bin_img.shape[:2]
    orig_h, orig_w = h, w
    w_scale = h_scale = 1.0
    if min(h, w) < 1000:
        scale = 1000.0 / min(h, w)
        bin_img = cv2.resize(bin_img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)
        h, w = bin_img.shape[:2]
        w_scale = w / orig_w
        h_scale = h / orig_h
    image = Image.fromarray(bin_img).convert("RGB")
    if return_scale:
        return image, w_scale, h_scale
    return image

def run_paddle_ocr(file_path):
    """
    Accepts an image or PDF file path.
    Returns a list of dicts: [{"text": ..., "bbox": [...]}, ...]
    """
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".pdf":
        pil_img = pdf_to_image(file_path)
        preprocessed_img = preprocess_image_for_ocr(pil_img, return_scale=False, binarize=False)
        img = np.array(preprocessed_img.convert("RGB"))
    else:
        preprocessed_img = preprocess_image_for_ocr(file_path, return_scale=False, binarize=False)
        img = np.array(preprocessed_img.convert("RGB"))
    height, width = img.shape[:2]
    result = ocr_engine.ocr(img, cls=True)
    ocr_output = []
    for line in result[0]:
        text = line[1][0].strip()
        if not text or all(c in ",.-|_:;" for c in text):
            continue
        box = line[0]  # 4 points: [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        bbox_rect = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
        ocr_output.append({"text": text, "bbox": bbox_rect})
    return ocr_output



def normalize_bbox(bbox, width, height):
    x0, y0, x1, y1 = bbox
    return [
        int(1000 * x0 / width),
        int(1000 * y0 / height),
        int(1000 * x1 / width),
        int(1000 * y1 / height)
    ]

def ocr_tokens_and_bboxes(image, granularity="word"):
    """
    Perform OCR using PaddleOCR and return tokens and bounding boxes.
    Args:
        image: PIL.Image or file path
        granularity: 'word' (default) or 'line' (PaddleOCR returns both)
    Returns:
        List of dicts with text, norm bbox, orig bbox, position
    """
    if isinstance(image, Image.Image):
        img = np.array(image.convert("RGB"))
    elif isinstance(image, str):
        img = cv2.imread(image)
        if img is None:
            raise FileNotFoundError(f"Image not found at path: {image}")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    else:
        raise ValueError("Input must be a file path or PIL.Image.Image")
    width, height = img.shape[1], img.shape[0]
    result = ocr_engine.ocr(img, cls=True)
    tokens = []
    # PaddleOCR returns [ [ [box, (text, conf)], ... ] ]
    for line in result[0]:
        text = line[1][0].strip()
        if not text or all(c in ",.-|_:;" for c in text):
            continue
        box = line[0]  # 4 points: [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
        x_coords = [pt[0] for pt in box]
        y_coords = [pt[1] for pt in box]
        x0, y0, x1, y1 = int(min(x_coords)), int(min(y_coords)), int(max(x_coords)), int(max(y_coords))
        tokens.append({
            "text": text,
            "bbox": normalize_bbox([x0, y0, x1, y1], width, height),
            "orig_bbox": [x0, y0, x1, y1],
            "position": (y0, x0)
        })
    # Optionally, for line-level tokens, group by lines (not implemented here)
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
        iou_threshold (float): IOU threshold for matching (default 0.1, may need tuning for PaddleOCR).
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
    

