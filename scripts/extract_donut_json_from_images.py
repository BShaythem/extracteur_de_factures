import os
import json
import time
from tqdm import tqdm
import sys
from typing import List
# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.services.groq_service import GroqService
from backend.utils.utils import run_paddle_ocr
from PIL import Image
from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURATION ---
IMAGE_DIR = "data/invoices-donut/valid"  # Change as needed
OUTPUT_DIR = "data/invoices-donut/donut_json"  # Where to save Donut JSON files
API_KEY = os.getenv("GROQ_API_KEY")  # Or set directly
MODEL = "llama3-8b-8192"

FIELDS = [
    "supplier_name", "supplier_address(postal address, not email)", "customer_name", "customer_address(postal address, not email)",
    "invoice_number", "invoice_date", "due_date", "tax_amount", "tax_rate",
    "invoice_subtotal", "invoice_total", "item_description", "item_quantity",
    "item_unit_price", "item_total_price"
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

groq_service = GroqService(api_key=API_KEY)

def extract_text_from_tokens(tokens):
    return " ".join([t["text"] for t in tokens])

def build_donut_prompt(tokens):
    prompt = f"""
You are an invoice extraction assistant.
Given the following OCR output (each token with its bounding box), extract the following fields as a JSON object.
Fields: {', '.join(FIELDS)}
If a field is missing, use an empty string or empty list. For repeating items, use a list.
OCR tokens:
{json.dumps(tokens, ensure_ascii=False, indent=2)}
Return only the JSON object, no explanation.
Example output:
{{
  "supplier_name": "Acme Corp",
  "supplier_address": "123 Main St",
  "customer_name": "John Doe",
  "customer_address": "456 Elm St",
  "invoice_number": "12345",
  "invoice_date": "2025-07-16",
  "due_date": "2025-08-16",
  "tax_amount": "5.00",
  "tax_rate": "10%",
  "invoice_subtotal": "50.00",
  "invoice_total": "55.00",
  "items": [
    {{
      "item_description": "Widget A",
      "item_quantity": "2",
      "item_unit_price": "10.00",
      "item_total_price": "20.00"
    }}
  ]
}}
"""
    return prompt

def process_batch(batch: List[str], delay: float = 2.0, max_retries: int = 3):
    for img_name in batch:
        img_path = os.path.join(IMAGE_DIR, img_name)
        tokens = run_paddle_ocr(img_path)
        prompt = build_donut_prompt(tokens)
        #print(f"\n--- Prompt for {img_name} ---\n{prompt}\n--- End of prompt ---\n")
        retries = 0
        while True:
            try:
                result = groq_service.call_groq(prompt, model=MODEL, force_result_key=False)
                break
            except Exception as e:
                # Check for rate limit error (GroqError or HTTP 429)
                if hasattr(e, 'status_code') and e.status_code == 429 or 'rate limit' in str(e).lower():
                    wait_time = delay * (2 ** retries)
                    print(f"Rate limit hit. Waiting {wait_time:.1f}s before retrying ({retries+1}/{max_retries})...")
                    time.sleep(wait_time)
                    retries += 1
                    if retries >= max_retries:
                        print(f"Failed to process {img_name} after {max_retries} retries. Skipping.")
                        result = {"error": "rate limit", "image": img_name}
                        break
                else:
                    print(f"Error processing {img_name}: {e}")
                    result = {"error": str(e), "image": img_name}
                    break
        # Save result as JSON
        out_path = os.path.join(OUTPUT_DIR, os.path.splitext(img_name)[0] + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        time.sleep(delay)

def batch_list(lst, batch_size):
    for i in range(0, len(lst), batch_size):
        yield lst[i:i+batch_size]

image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]

BATCH_SIZE = 5  # Adjust as needed for your rate limit
for batch in tqdm(list(batch_list(image_files, BATCH_SIZE)), desc="Processing batches"):
    process_batch(batch)

print(f"Extraction complete. JSON files saved to {OUTPUT_DIR}")
