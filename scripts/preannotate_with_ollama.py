import os
import json
import sys
import time
from PIL import Image

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.utils.utils import run_paddle_ocr
from backend.services.ollama_service import call_ollama
from backend.services.groq_service import GroqService  # Import for build_llm_prompt2

# Configuration
DATASET_DIR = "data/invoices/valid"
OUTPUT_FILE = "annotations_coco_ollama_valid.json"
SUPPORTED_EXTS = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".pdf"]
BATCH_SIZE = 20  # Smaller batches for Ollama (slower processing)

# Labels mapping
LABELS = [
    "invoice_number", "invoice_date", "due_date", "vendor-name", "vendor-address",
    "customer-name", "customer-address", "item-description", "item-quantity",
    "item-unit_price", "item-total_price", "subtotal", "tax_rate", "total_amount"
]

def get_image_files(dataset_dir):
    """Get all image files from dataset directory"""
    files = []
    for f in os.listdir(dataset_dir):
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS:
            files.append(os.path.join(dataset_dir, f))
    return sorted(files)

def get_image_dimensions(image_path):
    """Get image dimensions"""
    try:
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception:
        return 1000, 1000  # Default fallback

def validate_and_fix_bbox(x_percent, y_percent, width_percent, height_percent):
    """Validate and fix bounding box coordinates to be within valid range"""
    
    # Clamp values to valid percentage range (0-100)
    x_percent = max(0, min(100, x_percent))
    y_percent = max(0, min(100, y_percent))
    width_percent = max(0, min(100, width_percent))
    height_percent = max(0, min(100, height_percent))
    
    # Ensure bbox doesn't go out of image bounds
    if x_percent + width_percent > 100:
        width_percent = 100 - x_percent
    
    if y_percent + height_percent > 100:
        height_percent = 100 - y_percent
    
    # Minimum size validation (at least 0.1% of image)
    width_percent = max(0.1, width_percent)
    height_percent = max(0.1, height_percent)
    
    return x_percent, y_percent, width_percent, height_percent

def convert_to_coco_format(annotations, image_files):
    """Convert annotations to COCO format with bounds checking"""
    label2id = {label: idx+1 for idx, label in enumerate(LABELS)}
    
    images = []
    coco_annotations = []
    categories = [{"id": label2id[label], "name": label} for label in LABELS]
    
    ann_id = 1
    total_annotations = 0
    valid_annotations = 0
    
    for img_id, (image_path, annotation) in enumerate(zip(image_files, annotations), 1):
        width, height = get_image_dimensions(image_path)
        filename = os.path.basename(image_path)
        
        images.append({
            "id": img_id,
            "file_name": filename,
            "width": width,
            "height": height
        })
        
        # Process annotations for this image
        for result in annotation.get("result", []):
            if "value" not in result:
                continue
                
            value = result["value"]
            labels = value.get("labels", [])
            
            if not labels:
                continue
                
            label = labels[0]  # Take first label
            if label not in label2id:
                continue
            
            total_annotations += 1
            
            # Get coordinates with validation
            x_percent = value.get("x", 0)
            y_percent = value.get("y", 0)
            width_percent = value.get("width", 0)
            height_percent = value.get("height", 0)
            
            # Validate data types
            try:
                x_percent = float(x_percent)
                y_percent = float(y_percent)
                width_percent = float(width_percent)
                height_percent = float(height_percent)
            except (ValueError, TypeError):
                print(f"Warning: Invalid coordinate values for {filename}, skipping annotation")
                continue
            
            # Fix out of bounds coordinates
            x_percent, y_percent, width_percent, height_percent = validate_and_fix_bbox(
                x_percent, y_percent, width_percent, height_percent
            )
            
            # Convert percentage coordinates to absolute
            abs_x = int(x_percent / 100 * width)
            abs_y = int(y_percent / 100 * height)
            abs_width = int(width_percent / 100 * width)
            abs_height = int(height_percent / 100 * height)
            
            # Final validation - ensure positive dimensions
            if abs_width <= 0 or abs_height <= 0:
                print(f"Warning: Invalid bbox dimensions for {filename}, skipping annotation")
                continue
            
            coco_annotations.append({
                "id": ann_id,
                "image_id": img_id,
                "category_id": label2id[label],
                "bbox": [abs_x, abs_y, abs_width, abs_height],
                "area": abs_width * abs_height,
                "iscrowd": 0
            })
            ann_id += 1
            valid_annotations += 1
    
    print(f"Annotation validation: {valid_annotations}/{total_annotations} annotations are valid")
    
    return {
        "images": images,
        "annotations": coco_annotations,
        "categories": categories
    }

def process_batch(image_files, batch_start, batch_end):
    """Process a batch of images with Ollama"""
    batch_annotations = []
    
    # Create a temporary GroqService instance just for the prompt building
    groq_service = GroqService()
    
    for i in range(batch_start, min(batch_end, len(image_files))):
        image_path = image_files[i]
        print(f"Processing {i+1}/{len(image_files)}: {os.path.basename(image_path)}")
        
        try:
            # Run OCR
            ocr_tokens = run_paddle_ocr(image_path)
            
            if not ocr_tokens:
                print(f"Warning: No OCR tokens found for {os.path.basename(image_path)}")
                batch_annotations.append({"result": []})
                continue
            
            # Build prompt using the same method as Groq
            prompt = groq_service.build_llm_prompt2(ocr_tokens)
            
            # Call Ollama instead of Groq
            annotation = call_ollama(prompt, force_result_key=True)
            
            # Validate that we got a proper response
            if not isinstance(annotation, dict) or "result" not in annotation:
                print(f"Warning: Invalid response format for {os.path.basename(image_path)}")
                annotation = {"result": []}
            
            batch_annotations.append(annotation)
            
            # Progress indicator
            if (i + 1) % 5 == 0:  # More frequent updates for debugging
                print(f"Completed {i+1} images...")
                
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            batch_annotations.append({"result": []})
    
    return batch_annotations

def main():
    # Get image files
    image_files = get_image_files(DATASET_DIR)
    print(f"Found {len(image_files)} images to process")
    
    if not image_files:
        print("No images found!")
        return
    
    # Process in batches
    all_annotations = []
    
    for batch_start in range(0, len(image_files), BATCH_SIZE):
        batch_end = batch_start + BATCH_SIZE
        print(f"\nProcessing batch {batch_start//BATCH_SIZE + 1} (images {batch_start+1}-{min(batch_end, len(image_files))})")
        
        batch_annotations = process_batch(image_files, batch_start, batch_end)
        all_annotations.extend(batch_annotations)
        
        # Save intermediate results
        temp_file = f"temp_annotations_ollama_batch_{batch_start//BATCH_SIZE + 1}.json"
        with open(temp_file, 'w') as f:
            json.dump(all_annotations, f, indent=2)
        print(f"Saved intermediate results to {temp_file}")
        
        # Small delay between batches to avoid overwhelming local Ollama
        if batch_end < len(image_files):
            print("Waiting 5 seconds between batches...")
            time.sleep(5)
    
    # Convert to COCO format
    print("\nConverting to COCO format...")
    coco_data = convert_to_coco_format(all_annotations, image_files)
    
    # Save final COCO file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(coco_data, f, indent=2)
    
    print(f"\nComplete! Saved {len(coco_data['images'])} images and {len(coco_data['annotations'])} annotations to {OUTPUT_FILE}")
    print(f"Categories: {len(coco_data['categories'])}")
    
    # Clean up temp files
    for batch_num in range(1, len(image_files)//BATCH_SIZE + 2):
        temp_file = f"temp_annotations_ollama_batch_{batch_num}.json"
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    main()
