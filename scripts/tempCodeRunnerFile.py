import os
import json
import sys
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.utils.utils import run_paddle_ocr

def convert_bbox_to_label_studio_format(bbox, img_width, img_height):
    """Convert bbox from [x0, y0, x1, y1] to Label Studio percentage format"""
    x0, y0, x1, y1 = bbox
    
    return {
        "x": (x0 / img_width) * 100,
        "y": (y0 / img_height) * 100,
        "width": ((x1 - x0) / img_width) * 100,
        "height": ((y1 - y0) / img_height) * 100
    }

def find_token_by_text(tokens, text, tolerance=0.8):
    """Find OCR token that best matches the given text"""
    import difflib
    
    best_match = None
    best_ratio = 0
    
    for i, token in enumerate(tokens):
        ratio = difflib.SequenceMatcher(None, token['text'].lower(), text.lower()).ratio()
        if ratio > best_ratio and ratio > tolerance:
            best_ratio = ratio
            best_match = i
    
    return best_match

def prepare_label_studio_data():
    """Prepare data for Label Studio import with OCR token positioning"""
    
    # Use absolute paths for Windows
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    IMAGE_DIR = os.path.join(BASE_DIR, "data", "invoices-donut", "valid")
    JSON_DIR = os.path.join(BASE_DIR, "data", "invoices-donut", "donut_json")
    OUTPUT_FILE = os.path.join(BASE_DIR, "data", "label_studio_tasks.json")
    
    tasks = []
    
    # Get all image files
    image_files = [f for f in os.listdir(IMAGE_DIR) 
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    print(f"Processing {len(image_files)} images...")
    
    for i, image_file in enumerate(image_files):
        print(f"Processing {i+1}/{len(image_files)}: {image_file}")
        
        image_path = os.path.join(IMAGE_DIR, image_file)
        json_file = os.path.splitext(image_file)[0] + '.json'
        json_path = os.path.join(JSON_DIR, json_file)
        
        # Get image dimensions
        with Image.open(image_path) as img:
            img_width, img_height = img.size
        
        # Get OCR tokens with bounding boxes
        try:
            tokens = run_paddle_ocr(image_path)
        except Exception as e:
            print(f"Error getting OCR for {image_file}: {e}")
            tokens = []
        
        # Load existing JSON if available
        existing_data = {}
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        
        # Create Label Studio task WITH proper image reference
        task = {
            "data": {
                "image": f"/data/upload/{image_file}",  # This is the key fix!
                "filename": image_file,
                "image_name": image_file,
                "ocr_tokens": tokens
            },
            "annotations": [],
            "predictions": []
        }
        
        # Add existing annotations as predictions (pre-annotations)
        if existing_data and tokens:
            annotations = []
            
            for field, value in existing_data.items():
                if not value or field == 'items':
                    continue
                
                # Handle different field types
                if isinstance(value, list):
                    value_text = ' '.join(str(v) for v in value)
                else:
                    value_text = str(value)
                
                # Find matching tokens for this field value
                words = value_text.split()
                matched_tokens = []
                
                for word in words:
                    token_idx = find_token_by_text(tokens, word)
                    if token_idx is not None:
                        matched_tokens.append(token_idx)
                
                # If we found matching tokens, create bounding box annotations
                if matched_tokens:
                    # Get combined bounding box for all matched tokens
                    min_x = min(tokens[idx]['orig_bbox'][0] for idx in matched_tokens)
                    min_y = min(tokens[idx]['orig_bbox'][1] for idx in matched_tokens)
                    max_x = max(tokens[idx]['orig_bbox'][2] for idx in matched_tokens)
                    max_y = max(tokens[idx]['orig_bbox'][3] for idx in matched_tokens)
                    
                    # Convert to Label Studio format
                    ls_bbox = convert_bbox_to_label_studio_format(
                        [min_x, min_y, max_x, max_y], img_width, img_height
                    )
                    
                    annotations.append({
                        "value": {
                            "rectanglelabels": [field],
                            **ls_bbox
                        },
                        "from_name": "bbox_labels",
                        "to_name": "image",
                        "type": "rectanglelabels"
                    })
            
            # Add as predictions (pre-annotations that can be modified)
            if annotations:
                task["predictions"] = [{
                    "result": annotations,
                    "score": 0.8,
                    "model_version": "pre-annotation"
                }]
        
        tasks.append(task)
    
    # Save tasks
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Created {len(tasks)} tasks for Label Studio")
    print(f"📁 Import file: {OUTPUT_FILE}")
    print(f"📁 Image directory: {IMAGE_DIR}")
    print("\n📋 CORRECTED Next Steps:")
    print("1. Start Label Studio: label-studio start --port 8080")
    print("2. Create new project")
    print("3. Set up labeling interface with XML config")
    print("4. Upload ALL images first (Data Manager → Upload)")
    print("5. THEN import this JSON file (it will now match uploaded images)")
    print("6. Images should automatically link to tasks by filename")

if __name__ == "__main__":
    prepare_label_studio_data()