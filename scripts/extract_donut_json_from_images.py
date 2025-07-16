import os
import json
from tqdm import tqdm
import sys
# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.services.groq_service import GroqService
from backend.utils.utils import run_paddle_ocr
from PIL import Image

# --- CONFIGURATION ---
IMAGE_DIR = "data/invoices-8/test"  # Change as needed
OUTPUT_DIR = "data/invoices-8/donut_json"  # Where to save Donut JSON files
API_KEY = os.getenv("GROQ_API_KEY")  # Or set directly
MODEL = "llama3-8b-8192"

FIELDS = [
    "invoice_number", "invoice_date", "due_date", "customer_name", "customer_address",
    "supplier_name", "supplier_address", "item_description", "item_quantity",
    "item_total_price", "item_unit_price", "tax_amount", "tax_rate",
    "invoice_subtotal", "invoice_total"
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

groq_service = GroqService(api_key=API_KEY)

def extract_text_from_tokens(tokens):
    return " ".join([t["text"] for t in tokens])

def build_donut_prompt(text):
    prompt = (
        "You are an invoice extraction assistant.\n"
        "Given the following invoice text, extract the following fields as a JSON object.\n"
        f"Fields: {', '.join(FIELDS)}\n"
        "If a field is missing, use an empty string or empty list. For repeating items, use a list.\n"
        "Invoice text:\n"
        f"{text}\n"
        "Return only the JSON object, no explanation.\n"
        "Example output:\n"
        "{\n  \"invoice_number\": \"12345\",\n  \"invoice_date\": \"2025-07-16\",\n  \"items\": [\n    {\"item_description\": \"Widget A\", \"item_quantity\": \"2\", \"item_unit_price\": \"10.00\", \"item_total_price\": \"20.00\"}\n  ],\n  \"invoice_total\": \"20.00\"\n}\n"
    )
    return prompt

image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]

for img_name in tqdm(image_files, desc="Processing images"):
    img_path = os.path.join(IMAGE_DIR, img_name)
    tokens = run_paddle_ocr(img_path)
    text = extract_text_from_tokens(tokens)
    prompt = build_donut_prompt(text)
    result = groq_service.call_groq(prompt, model=MODEL, force_result_key=False)
    # Save result as JSON
    out_path = os.path.join(OUTPUT_DIR, os.path.splitext(img_name)[0] + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
print(f"Extraction complete. JSON files saved to {OUTPUT_DIR}")
