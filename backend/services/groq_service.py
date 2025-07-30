import os
import json
import time
from groq import Groq
from dotenv import load_dotenv
from backend.utils.prompts import build_llm_prompt

load_dotenv()

class GroqService:
    def __init__(self, api_key=None):
        print("GROQ_API_KEY from env:", os.getenv("GROQ_API_KEY"))
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required for Groq service")
        self.client = Groq(api_key=api_key)
        self.last_request_time = 0
        self.request_interval = 2.0

    def call_groq(self, prompt):
        """
        Call Groq API and return standardized format.
        """
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.request_interval:
                time.sleep(self.request_interval - time_since_last)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            self.last_request_time = time.time()
            llm_response = response.choices[0].message.content.strip()
            
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
                        return self._get_empty_result()
                else:
                    return self._get_empty_result()
                    
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from Groq response: {e}")
                print(f"Raw response: {llm_response}")
                return self._get_empty_result()
                
        except Exception as e:
            print(f"Error calling Groq: {str(e)}")
            return self._get_empty_result()

    def build_llm_prompt2(self, ocr_tokens):
        """
        Build prompt using the standardized format from prompts.py
        """
        return build_llm_prompt(ocr_tokens)

    def _get_empty_result(self):
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

# Example usage
if __name__ == "__main__":
    # Set your API key
    groq_service = GroqService(api_key="your-api-key-here")
    
    # Example OCR tokens
    ocr_tokens = [
        {"text": "INVOICE", "bbox": [100, 50, 200, 80]},
        {"text": "12345", "bbox": [300, 50, 400, 80]},
        {"text": "Total:", "bbox": [100, 200, 150, 230]},
        {"text": "$500.00", "bbox": [200, 200, 300, 230]}
    ]
    
    # Build prompt and call API
    prompt = groq_service.build_llm_prompt2(ocr_tokens)
    result = groq_service.call_groq(prompt)
    
    print(json.dumps(result, indent=2))
