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

def create_all_ocr_tokens_as_annotations(tokens, img_width, img_height):
    """Create annotations for ALL OCR tokens with their text as labels"""
    annotations = []
    
    for i, token in enumerate(tokens):
        if 'orig_bbox' in token and token.get('text', '').strip():
            bbox = token['orig_bbox']
            ls_bbox = convert_bbox_to_label_studio_format(bbox, img_width, img_height)
            
            # Create annotation with token text as the label (you can change labels later)
            annotations.append({
                "id": f"token_{i}",
                "value": {
                    "rectanglelabels": ["token"],  # Generic label - you'll reassign these
                    "text": [token['text']],  # Include the actual text
                    **ls_bbox
                },
                "from_name": "bbox_labels",
                "to_name": "image",
                "type": "rectanglelabels"
            })
    
    return annotations

def prepare_label_studio_data():
    """Prepare data for Label Studio import with ALL OCR tokens visible"""
    
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
            print(f"   Found {len(tokens)} OCR tokens")
        except Exception as e:
            print(f"   Error getting OCR for {image_file}: {e}")
            tokens = []
        
        # Load existing JSON if available
        existing_data = {}
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            print(f"   Loaded existing JSON with {len(existing_data)} fields")
        
        # Create Label Studio task WITH local file path
        task = {
            "data": {
                "image": f"/data/local-files/?d=valid/{image_file}",
                "filename": image_file,
                "current_json": existing_data,  # Include current JSON data in the task
                "ocr_tokens": tokens,  # Include all OCR tokens
                "token_texts": [token.get('text', '') for token in tokens]  # Easy access to token texts
            },
            "annotations": [],
            "predictions": []
        }
        
        # Create annotations for ALL OCR tokens
        if tokens:
            ocr_annotations = create_all_ocr_tokens_as_annotations(tokens, img_width, img_height)
            
            # Add ALL tokens as predictions (pre-annotations that can be modified)
            task["predictions"] = [{
                "result": ocr_annotations,
                "score": 1.0,
                "model_version": "ocr_tokens"
            }]
            print(f"   Created {len(ocr_annotations)} OCR token annotations")
        
        tasks.append(task)
    
    # Save tasks
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Created {len(tasks)} tasks for Label Studio")
    print(f"📁 Import file: {OUTPUT_FILE}")
    print(f"\n🎯 What you'll see in Label Studio:")
    print("- ALL OCR tokens as bounding boxes on the image")
    print("- Current JSON data in the task data panel")
    print("- You can relabel boxes to correct field assignments")
    print("- Token texts are preserved for easy copying")

if __name__ == "__main__":
    prepare_label_studio_data()