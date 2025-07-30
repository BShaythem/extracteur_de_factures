import json
import time
import requests
from backend.utils.prompts import build_llm_prompt

def call_ollama(prompt):
    """
    Call Ollama API and return standardized format.
    """
    try:
        # Call Ollama API
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama2",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code}")
        
        result = response.json()
        llm_response = result.get("response", "").strip()
        
        # Try to parse JSON from the response
        try:
            # Extract JSON from the response (in case there's extra text)
            start_idx = llm_response.find('{')
            end_idx = llm_response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = llm_response[start_idx:end_idx]
                parsed_data = json.loads(json_str)
                
                # Ensure it has the expected structure
                if "extracted_fields" in parsed_data:
                    return parsed_data["extracted_fields"]
                else:
                    # If it doesn't have the right structure, create empty result
                    return _get_empty_result()
            else:
                return _get_empty_result()
                
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from Ollama response: {e}")
            print(f"Raw response: {llm_response}")
            return _get_empty_result()
            
    except Exception as e:
        print(f"Error calling Ollama: {str(e)}")
        return _get_empty_result()

def _get_empty_result():
    """
    Return empty result in standardized format.
    """
    return {
        "supplier_name": {"candidates": [], "selected": ""},
        "supplier_address": {"candidates": [], "selected": ""},
        "customer_name": {"candidates": [], "selected": ""},
        "customer_address": {"candidates": [], "selected": ""},
        "invoice_number": {"candidates": [], "selected": ""},
        "invoice_date": {"candidates": [], "selected": ""},
        "due_date": {"candidates": [], "selected": ""},
        "invoice_subtotal": {"candidates": [], "selected": ""},
        "tax_amount": {"candidates": [], "selected": ""},
        "tax_rate": {"candidates": [], "selected": ""},
        "invoice_total": {"candidates": [], "selected": ""},
        "items": {"candidates": [], "selected": []}
    }
