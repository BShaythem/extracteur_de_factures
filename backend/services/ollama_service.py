import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"  # Adjust if needed

def build_llm_prompt(ocr_tokens):
    """
    Build a prompt for the LLM using OCR tokens and bounding boxes.
    """
    prompt = '''
You are a document parser that extracts structured data from OCR tokens of an invoice. Each token includes a text string and its bounding box.
Your task is to extract the most accurate values for each of the fields listed below using the OCR tokens and their positions. If a value is not found, leave it as an empty string. For each extracted field, also include a confidence score between 0 and 1 based on how certain you are (e.g., 0.95 if clearly matched, 0.5 if it's a guess).
Only return a **valid JSON** in this format:
{
  "invoice_number": {"value": "", "confidence": 0.0},
  "invoice_date": {"value": "", "confidence": 0.0},
  "due_date": {"value": "", "confidence": 0.0},
  "bill_to": {"value": "", "confidence": 0.0},
  "amount_due": {"value": "", "confidence": 0.0},
  "items": [
    {
      "name": {"value": "", "confidence": 0.0},
      "quantity": {"value": "", "confidence": 0.0},
      "unit_price": {"value": "", "confidence": 0.0},
      "total_price": {"value": "", "confidence": 0.0}
    }
  ]
}

Now process the following OCR tokens and bounding boxes:
    '''
    for token in ocr_tokens:
        prompt += f"Token: {token['text']}, BBox: {token['bbox']}\n"
    return prompt

def build_llm_prompt2(ocr_tokens):
    """
    Build a prompt for the LLM to return Label Studio compatible annotation format.
    The prompt should instruct the LLM to output a JSON with a 'result' key, where each element is a dict with
    'value': { 'x': ..., 'y': ..., 'width': ..., 'height': ..., 'rotation': 0, 'labels': [<field>] }
    and coordinates are in percent (0-100) relative to the image size.
    """
    prompt = (
        "You are an invoice annotation assistant.\n"
        "Given the following OCR tokens and their bounding boxes, return a JSON with a 'result' key.\n"
        "Each element in 'result' should be a dict with:\n"
        "  'value': { 'x': <top-left-x in percent>, 'y': <top-left-y in percent>, 'width': <width in percent>, 'height': <height in percent>, 'rotation': 0, 'labels': [<field>] }\n"
        "If a field spans multiple tokens, group them in a single box.\n"
        "The labels should be: invoice_number, invoice_date, due_date, biller_name, total_amount_due, tax, currency, item_description, item_quantity, item_unit_price, item_total_price, item_tax_rate.\n"
        "Example OCR tokens:\n"
    )
    for token in ocr_tokens:
        prompt += f"Token: {token['text']}, BBox: {token['bbox']}\n"
    prompt += (
        "\nReturn only the JSON with the 'result' key, no explanation.\n"
        "Example output:\n"
        "{\n  'result': [\n    {\n      'value': { 'x': 10.5, 'y': 5.2, 'width': 15.0, 'height': 3.1, 'rotation': 0, 'labels': ['invoice_number'] }\n    },\n    ...\n  ]\n}\n"
    )
    return prompt

def call_ollama(prompt, model="mistral", force_result_key=False):
    """
    Call the Ollama API with the prompt and return the parsed JSON response.
    If force_result_key is True, always return a dict with a 'result' key (for Label Studio pre-annotation).
    Otherwise, return the parsed JSON as-is (for classic LLM extraction).
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    llm_response = response.json()["response"]
    try:
        json_start = llm_response.find('{')
        json_end = llm_response.rfind('}') + 1
        json_str = llm_response[json_start:json_end]
        parsed = json.loads(json_str.replace("'", '"'))
        if force_result_key:
            if isinstance(parsed, dict) and 'result' in parsed:
                return {"result": parsed['result']}
            if isinstance(parsed, list):
                return {"result": parsed}
            return {"result": []}
        return parsed
    except Exception:
        if force_result_key:
            try:
                if 'result' in llm_response:
                    json_start = llm_response.find('[')
                    json_end = llm_response.rfind(']') + 1
                    result_str = llm_response[json_start:json_end]
                    result = json.loads(result_str.replace("'", '"'))
                    return {"result": result}
            except Exception:
                pass
            return {"result": []}
        return {"raw_response": llm_response}
