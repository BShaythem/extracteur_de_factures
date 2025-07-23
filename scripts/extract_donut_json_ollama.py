import os
import json
from tqdm import tqdm
import sys
import time  # <-- Add this import
# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.services.ollama_service import call_ollama
from backend.utils.utils import run_paddle_ocr
from PIL import Image

# --- CONFIGURATION ---
IMAGE_DIR = "data/invoices-donut/test"  # Change as needed
OUTPUT_DIR = "data/invoices-donut/donut_json/test  "  # Where to save Donut JSON files
MODEL = "mistral"  # Change to your Ollama model name if needed

BATCH_SIZE = 10  # Number of images to process per batch
SLEEP_BETWEEN_BATCHES = 60  # Seconds to rest between batches

FIELDS = [
    "supplier_name", "supplier_address", "customer_name", "customer_address",
    "invoice_number", "invoice_date", "due_date", "tax_amount", "tax_rate",
    "invoice_subtotal", "invoice_total", "item_description", "item_quantity",
    "item_unit_price", "item_total_price"
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_text_from_tokens(tokens):
    return " ".join([t["text"] for t in tokens])

def build_donut_prompt(text):
    prompt = f"""
You are an invoice extraction assistant.
Given the following invoice text, extract the following fields as a JSON object.
Fields: {', '.join(FIELDS)}
If a field is missing, use an empty string or empty list. For repeating items, use a list.
Invoice text:
{text}
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

image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]

total = len(image_files)
for batch_start in range(0, total, BATCH_SIZE):
    batch_files = image_files[batch_start:batch_start+BATCH_SIZE]
    for img_name in tqdm(batch_files, desc=f"Processing images {batch_start+1}-{min(batch_start+BATCH_SIZE, total)} of {total}"):
        img_path = os.path.join(IMAGE_DIR, img_name)
        tokens = run_paddle_ocr(img_path)
        text = extract_text_from_tokens(tokens)
        prompt = build_donut_prompt(text)
        result = call_ollama(prompt, model=MODEL, force_result_key=False)
        # Save result as JSON
        out_path = os.path.join(OUTPUT_DIR, os.path.splitext(img_name)[0] + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    if batch_start + BATCH_SIZE < total:
        print(f"Batch complete. Resting for {SLEEP_BETWEEN_BATCHES} seconds...")
        time.sleep(SLEEP_BETWEEN_BATCHES)

print(f"Extraction complete. JSON files saved to {OUTPUT_DIR}")