import os
import json
import sys
import time
from PIL import Image

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.utils.utils import run_paddle_ocr
from backend.services.groq_service import GroqService

# Configuration
DATASET_DIR = "data/invoices/train"
OUTPUT_FILE = "annotations_coco.json"
SUPPORTED_EXTS = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".pdf"]
BATCH_SIZE = 50  # Process in batches to avoid overwhelming free tier
RESUME_FROM_BATCH = 9  # Batch number to resume from (1-based index)

# Labels mapping
LABELS = [
    "invoice_number", "invoice_date", "due_date", "vendor-name", "vendor-address",
    "customer-name", "customer-address", "subtotal", "tax_rate", "total_amount"
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

def convert_to_coco_format(annotations, image_files):
    """Convert annotations to COCO format"""
    label2id = {label: idx+1 for idx, label in enumerate(LABELS)}
    
    images = []
    coco_annotations = []
    categories = [{"id": label2id[label], "name": label} for label in LABELS]
    
    ann_id = 1
    
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
                
            # Convert percentage coordinates to absolute
            x_percent = value.get("x", 0)
            y_percent = value.get("y", 0)
            width_percent = value.get("width", 0)
            height_percent = value.get("height", 0)
            
            abs_x = int(x_percent / 100 * width)
            abs_y = int(y_percent / 100 * height)
            abs_width = int(width_percent / 100 * width)
            abs_height = int(height_percent / 100 * height)
            
            coco_annotations.append({
                "id": ann_id,
                "image_id": img_id,
                "category_id": label2id[label],
                "bbox": [abs_x, abs_y, abs_width, abs_height],
                "area": abs_width * abs_height,
                "iscrowd": 0
            })
            ann_id += 1
    
    return {
        "images": images,
        "annotations": coco_annotations,
        "categories": categories
    }

def process_batch(groq_service, image_files, batch_start, batch_end):
    """Process a batch of images"""
    batch_annotations = []
    
    for i in range(batch_start, min(batch_end, len(image_files))):
        image_path = image_files[i]
        print(f"Processing {i+1}/{len(image_files)}: {os.path.basename(image_path)}")
        
        try:
            # Run OCR
            ocr_tokens = run_paddle_ocr(image_path)
            
            # Build prompt and call Groq
            prompt = groq_service.build_llm_prompt2(ocr_tokens)
            annotation = groq_service.call_groq(prompt)
            
            batch_annotations.append(annotation)
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"Completed {i+1} images...")
                
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            batch_annotations.append({"result": []})
    
    return batch_annotations

def main():
    # Initialize Groq service
    groq_service = GroqService()  # Uses GROQ_API_KEY from environment

    # Get image files
    image_files = get_image_files(DATASET_DIR)
    print(f"Found {len(image_files)} images to process")

    if not image_files:
        print("No images found!")
        return

    # Load previous annotations if resuming
    all_annotations = []
    if RESUME_FROM_BATCH > 1:
        for batch_num in range(1, RESUME_FROM_BATCH):
            temp_file = f"temp_annotations_batch_{batch_num}.json"
            if os.path.exists(temp_file):
                with open(temp_file, 'r') as f:
                    batch_data = json.load(f)
                all_annotations = batch_data  # Use the last saved cumulative annotations
                print(f"Loaded annotations up to batch {batch_num}")

    # Start processing from the specified batch
    for batch_start in range((RESUME_FROM_BATCH - 1) * BATCH_SIZE, len(image_files), BATCH_SIZE):
        batch_end = batch_start + BATCH_SIZE
        print(f"\nProcessing batch {batch_start//BATCH_SIZE + 1} (images {batch_start+1}-{min(batch_end, len(image_files))})")

        batch_annotations = process_batch(groq_service, image_files, batch_start, batch_end)
        all_annotations.extend(batch_annotations)

        # Save intermediate results
        temp_file = f"temp_annotations_batch_{batch_start//BATCH_SIZE + 1}.json"
        with open(temp_file, 'w') as f:
            json.dump(all_annotations, f, indent=2)
        print(f"Saved intermediate results to {temp_file}")

        # Wait between batches to respect rate limits
        if batch_end < len(image_files):
            print("Waiting 30 seconds between batches...")
            time.sleep(30)

    # Convert to COCO format
    print("\nConverting to COCO format...")
    coco_data = convert_to_coco_format(all_annotations, image_files)

    # Save final COCO file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(coco_data, f, indent=2)

    print(f"\nComplete! Saved {len(coco_data['images'])} images and {len(coco_data['annotations'])} annotations to {OUTPUT_FILE}")
    print(f"Categories: {len(coco_data['categories'])}")

    # Clean up temp files
    for batch_num in range(0, len(image_files)//BATCH_SIZE + 1):
        temp_file = f"temp_annotations_batch_{batch_num}.json"
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    main()