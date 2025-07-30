import torch
import numpy as np
from PIL import Image
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import json
import os
from backend.utils.utils import run_paddle_ocr, preprocess_image_for_ocr, pdf_to_image
import re
import cv2

HEADER_WORDS = {
    "facture", "invoice", "n", "no", "number", "date", "total", "amount", "commande", "envoiea",
    "bill", "to", "from", "logo", "company", "address", "name", "client", "customer", "supplier",
    "vendor", "due", "subtotal", "tax", "rate", "items", "description", "quantity", "price",
    "unit", "cost", "payment", "terms", "balance", "paid", "outstanding", "discount", "shipping",
    "handling", "freight", "delivery", "service", "charge", "fee", "credit", "debit", "account",
    "reference", "order", "purchase", "sale", "transaction", "receipt", "statement", "balance",
    "amount", "currency", "dollars", "euros", "pounds", "cents", "percent", "percentage",
    "DATE", "LOGO"  # Added these two specific problematic words
}

def extract_with_layoutlmv3(image_path):
    """
    Extract invoice fields using LayoutLMv3 model.
    Returns a JSON structure with extracted fields (excluding items).
    """
    # Load the trained model
    model_dir = "backend/models/layoutlmv3-invoice" 
    if not os.path.exists(model_dir):
        raise FileNotFoundError(f"Model directory not found: {model_dir}")
    
    processor = LayoutLMv3Processor.from_pretrained(model_dir)
    model = LayoutLMv3ForTokenClassification.from_pretrained(model_dir)
    model.eval()
    
    # Detect device
    device = torch.device("cpu")#torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    # Check if it's a PDF file
    file_ext = os.path.splitext(image_path)[1].lower()
    is_pdf = file_ext == '.pdf'
    
    # Try multiple approaches to load the image
    image = None
    width, height = 0, 0
    
    print(f"Attempting to load {'PDF' if is_pdf else 'image'}: {image_path}")
    print(f"File exists: {os.path.exists(image_path)}")
    if os.path.exists(image_path):
        print(f"File size: {os.path.getsize(image_path)} bytes")
    
    # If it's a PDF, convert it first
    if is_pdf:
        try:
            print("Converting PDF to image...")
            pil_img = pdf_to_image(image_path)
            if pil_img is not None:
                image = pil_img
                width, height = image.size
                print(f"PDF conversion successful: {width}x{height}")
            else:
                print("PDF conversion returned None")
        except Exception as e:
            print(f"PDF conversion failed: {str(e)}")
    
    # If not a PDF or PDF conversion failed, try direct loading
    if image is None:
        # Approach 1: Try direct PIL loading
        try:
            print("Trying direct PIL loading...")
            image = Image.open(image_path).convert("RGB")
            width, height = image.size
            print(f"PIL loading successful: {width}x{height}")
        except Exception as e:
            print(f"PIL loading failed: {str(e)}")
    
    # Approach 2: Try OpenCV loading
    if image is None:
        try:
            print("Trying OpenCV loading...")
            cv_img = cv2.imread(image_path)
            if cv_img is not None:
                cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(cv_img_rgb)
                width, height = image.size
                print(f"OpenCV loading successful: {width}x{height}")
            else:
                print("OpenCV returned None")
        except Exception as e:
            print(f"OpenCV loading failed: {str(e)}")
    
    # Approach 3: Try preprocessing function
    if image is None:
        try:
            print("Trying preprocess_image_for_ocr...")
            preprocessed_img = preprocess_image_for_ocr(image_path, return_scale=False, binarize=False)
            if preprocessed_img is not None:
                image = preprocessed_img
                width, height = image.size
                print(f"Preprocessing successful: {width}x{height}")
            else:
                print("Preprocessing returned None")
        except Exception as e:
            print(f"Preprocessing failed: {str(e)}")
    
    if image is None:
        raise ValueError(f"All image loading methods failed for {image_path}")
    
    # Run OCR using the utility function
    try:
        ocr_result = run_paddle_ocr(image_path)
        print(f"OCR completed, found {len(ocr_result)} text elements")
    except Exception as e:
        print(f"Error during OCR: {str(e)}")
        return _get_empty_result()
    
    # Extract words and bounding boxes
    ocr_words = []
    ocr_bboxes = []
    for item in ocr_result:
        text = item["text"]
        bbox = item["bbox"]  # [x0, y0, x1, y1]
        ocr_words.append(text)
        ocr_bboxes.append(bbox)
    
    if not ocr_words:
        print("No text found in image")
        return _get_empty_result()
    
    # Normalize bboxes to 0-1000 as required by LayoutLMv3
    norm_bboxes = []
    for bbox in ocr_bboxes:
        x0, y0, x1, y1 = bbox
        x0 = int(round(1000 * x0 / width))
        y0 = int(round(1000 * y0 / height))
        x1 = int(round(1000 * x1 / width))
        y1 = int(round(1000 * y1 / height))
        # Ensure order and clip to [0, 1000]
        x0, x1 = sorted([max(0, min(1000, x0)), max(0, min(1000, x1))])
        y0, y1 = sorted([max(0, min(1000, y0)), max(0, min(1000, y1))])
        norm_bboxes.append([x0, y0, x1, y1])
    
    # Prepare processor input
    try:
        encoding = processor(
            text=ocr_words,
            boxes=norm_bboxes,
            images=image,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=512
        )
        
        # Move to device
        for k in encoding:
            encoding[k] = encoding[k].to(device)
        
        # Run inference
        with torch.no_grad():
            outputs = model(**encoding)
            logits = outputs.logits.cpu().numpy()[0]
            pred_ids = np.argmax(logits, axis=-1)
        
        # Get label list from model config
        id2label = model.config.id2label if hasattr(model.config, 'id2label') else {i: str(i) for i in range(model.config.num_labels)}
        pred_labels = [id2label[str(i)] if str(i) in id2label else id2label[i] for i in pred_ids]
        
        # Only keep predictions for actual tokens (not padding)
        actual_len = len(ocr_words)
        pred_labels = pred_labels[:actual_len]
        
        # Extract fields (excluding item-related fields), with candidates and confidence
        extracted_fields = _extract_fields_with_confidence(ocr_words, pred_labels, logits[:actual_len])
        
        return extracted_fields
        
    except Exception as e:
        print(f"Error during model inference: {str(e)}")
        return _get_empty_result()

def clean_value(field, value):
    if not value or not isinstance(value, str):
        return ""
    
    original_value = value
    value = value.strip()
    
    # Remove common header words
    value = re.sub(r"\b(?:" + "|".join(HEADER_WORDS) + ")\b", "", value, flags=re.IGNORECASE).strip()
    
    # Additional aggressive filtering for names
    if field in {"supplier_name", "customer_name"}:
        # Remove common invoice header words
        value = re.sub(r"facture|invoice|client|customer|name|n|bill|to|from|logo|company|date", "", value, flags=re.IGNORECASE).strip()
        # Must contain at least one letter and be reasonable length
        if not re.search(r"[A-Za-z]", value) or len(value) < 2 or len(value) > 100:
            return ""
        # Remove if it's just numbers or common words
        if re.match(r"^\d+$", value) or value.lower() in {"date", "time", "page", "total", "logo", "bill", "from", "to"}:
            return ""
    
    elif field in {"supplier_address", "customer_address"}:
        # Remove common header words
        value = re.sub(r"address|location|street|city|state|zip|postal|code|bill|to", "", value, flags=re.IGNORECASE).strip()
        # Must have at least 2 words for an address
        if len(value.split()) < 2:
            return ""
    
    elif field == "invoice_number":
        # Allow numbers-only or # followed by numbers, require min length 4
        value = re.sub(r"[^A-Za-z0-9-#]", "", value)
        if len(value) < 4:
            return ""
        # Must be either all numbers or # followed by numbers
        if not (re.match(r"^\d+$", value) or re.match(r"^#\d+$", value)):
            return ""
    
    elif field in {"invoice_date", "due_date"}:
        # Accept dates with month names (e.g., '12 Jan 2024', 'January 12, 2024')
        # Accept dd/mm/yyyy, yyyy-mm-dd, dd Mon yyyy, Mon dd, yyyy, Month dd, yyyy
        date_patterns = [
            r"\d{2}/\d{2}/\d{4}",
            r"\d{4}-\d{2}-\d{2}",
            r"\d{1,2} [A-Za-z]{3,9} \d{4}",
            r"[A-Za-z]{3,9} \d{1,2},? \d{4}"
        ]
        match = None
        for pat in date_patterns:
            match = re.search(pat, value)
            if match:
                value = match.group()
                break
        if not match:
            return ""
    
    elif field in {"invoice_total", "tax_amount", "invoice_subtotal"}:
        # Accept zero, allow up to 1,000,000, allow currency symbols
        match = re.search(r"[\$€£]?-?\d+[\.,]?\d*", value.replace(",", "."))
        if match:
            num_str = match.group().replace(",", ".")
            try:
                num = float(re.sub(r"[^\d.-]", "", num_str))
                if num < 0 or num > 1000000:
                    return ""
            except Exception:
                return ""
            value = num_str
        else:
            return ""
    
    elif field == "tax_rate":
        # Accept up to 200
        match = re.search(r"\d{1,3}(\.\d+)?%?", value)
        if match:
            value = match.group().replace("%", "")
            try:
                num = float(value)
                if num < 0 or num > 200:
                    return ""
            except Exception:
                return ""
        else:
            return ""
    
    # Debug: print if we filtered out something
    if original_value != value:
        print(f"Filtered '{original_value}' -> '{value}' for field {field}")
    
    return value.strip()

def _extract_fields_with_confidence(tokens, labels, logits):
    target_fields = [
        'supplier_name', 'supplier_address', 'customer_name', 'customer_address',
        'invoice_number', 'invoice_date', 'due_date', 'tax_amount', 'tax_rate',
        'invoice_subtotal', 'invoice_total'
    ]
    results = {}
    for field in target_fields:
        candidates = []
        field_tokens = []
        field_confs = []
        capture = False
        for i, (token, label) in enumerate(zip(tokens, labels)):
            if label == f"B-{field}":
                if field_tokens:
                    value = " ".join(field_tokens).strip()
                    avg_conf = float(np.mean(field_confs)) if field_confs else 0.0
                    if value and avg_conf > 0.4:
                        candidates.append({"value": value, "confidence": avg_conf})
                    field_tokens = [token]
                    # Calculate confidence from logits
                    try:
                        conf = float(np.max(torch.nn.functional.softmax(torch.tensor(logits[i]), dim=-1).numpy()))
                        field_confs = [conf]
                    except Exception:
                        field_confs = [0.5]  # Default confidence if calculation fails
                    capture = True
                else:
                    field_tokens = [token]
                    # Calculate confidence from logits
                    try:
                        conf = float(np.max(torch.nn.functional.softmax(torch.tensor(logits[i]), dim=-1).numpy()))
                        field_confs = [conf]
                    except Exception:
                        field_confs = [0.5]  # Default confidence if calculation fails
                    capture = True
            elif label == f"I-{field}" and capture:
                field_tokens.append(token)
                # Calculate confidence from logits
                try:
                    conf = float(np.max(torch.nn.functional.softmax(torch.tensor(logits[i]), dim=-1).numpy()))
                    field_confs.append(conf)
                except Exception:
                    field_confs.append(0.5)  # Default confidence if calculation fails
            elif label.startswith("B-") and capture:
                value = " ".join(field_tokens).strip()
                avg_conf = float(np.mean(field_confs)) if field_confs else 0.0
                if value and avg_conf > 0.4:
                    candidates.append({"value": value, "confidence": avg_conf})
                field_tokens = []
                field_confs = []
                capture = False
            else:
                if capture:
                    value = " ".join(field_tokens).strip()
                    avg_conf = float(np.mean(field_confs)) if field_confs else 0.0
                    if value and avg_conf > 0.4:
                        candidates.append({"value": value, "confidence": avg_conf})
                    field_tokens = []
                    field_confs = []
                    capture = False
        if field_tokens:
            value = " ".join(field_tokens).strip()
            avg_conf = float(np.mean(field_confs)) if field_confs else 0.0
            if value and avg_conf > 0.4:
                candidates.append({"value": value, "confidence": avg_conf})
        # Post-process candidates
        for cand in candidates:
            cand["value"] = clean_value(field, cand["value"])
        # Remove empty values and sort by confidence
        candidates = [c for c in candidates if c["value"]]
        # Remove duplicates (case-insensitive, strip spaces)
        seen = set()
        unique_candidates = []
        for c in candidates:
            key = c["value"].strip().lower()
            if key not in seen:
                unique_candidates.append(c)
                seen.add(key)
        candidates = unique_candidates
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        selected = candidates[0]["value"] if candidates else ""
        results[field] = {
            "candidates": candidates,
            "selected": selected
        }
    # Always return items as empty list
    results["items"] = {"candidates": [], "selected": []}
    return results

def _get_empty_result():
    """
    Return empty result structure when no text is found.
    """
    return {
        "supplier_name": "",
        "supplier_address": "",
        "customer_name": "",
        "customer_address": "",
        "invoice_number": "",
        "invoice_date": "",
        "due_date": "",
        "tax_amount": "",
        "tax_rate": "",
        "invoice_subtotal": "",
        "invoice_total": "",
        "items": []
    }
