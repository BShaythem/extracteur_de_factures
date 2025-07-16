import os
import json
import time
from groq import Groq

class GroqService:
    def extract_donut_json(self, invoice_text, fields=None, model="llama3-8b-8192"):
        """
        Extract Donut-style JSON from invoice text using Groq LLM.
        Args:
            invoice_text (str): The OCR text from the invoice.
            fields (list): List of fields to extract.
            model (str): Model name for Groq.
        Returns:
            dict: Extracted JSON object.
        """
        if fields is None:
            fields = [
                "invoice_number", "invoice_date", "due_date", "customer_name", "customer_address",
                "supplier_name", "supplier_address", "item_description", "item_quantity",
                "item_total_price", "item_unit_price", "tax_amount", "tax_rate",
                "invoice_subtotal", "invoice_total"
            ]
        prompt = (
            "You are an invoice extraction assistant.\n"
            "Given the following invoice text, extract the following fields as a JSON object.\n"
            f"Fields: {', '.join(fields)}\n"
            "If a field is missing, use an empty string or empty list. For repeating items, use a list.\n"
            "Invoice text:\n"
            f"{invoice_text}\n"
            "Return only the JSON object, no explanation.\n"
            "Example output:\n"
            "{\n  \"invoice_number\": \"12345\",\n  \"invoice_date\": \"2025-07-16\",\n  \"items\": [\n    {\"item_description\": \"Widget A\", \"item_quantity\": \"2\", \"item_unit_price\": \"10.00\", \"item_total_price\": \"20.00\"}\n  ],\n  \"invoice_total\": \"20.00\"\n}\n"
        )
        return self.call_groq(prompt, model=model, force_result_key=False)
    
    def __init__(self, api_key=None):
        self.client = Groq(
            api_key=api_key or os.getenv("GROQ_API_KEY")
        )
        self.last_request_time = 0
        self.request_interval = 2.0  # 2 seconds between requests for free tier
    
    def build_llm_prompt2(self, ocr_tokens):
        """Build prompt for invoice annotation task"""
        prompt = (
            "You are an invoice annotation assistant.\n"
            "Given the following OCR tokens and their bounding boxes, return a JSON with a 'result' key.\n"
            "Each element in 'result' should be a dict with:\n"
            "  'value': { 'x': <top-left-x in percent>, 'y': <top-left-y in percent>, 'width': <width in percent>, 'height': <height in percent>, 'rotation': 0, 'labels': [<field>] }\n"
            "If a field spans multiple tokens, group them in a single box.\n"
            "The labels should be: invoice_number, invoice_date, due_date, vendor-name, vendor-address, customer-name, customer-address, item-description, item-quantity, item-unit_price, item-total_price, subtotal, tax_rate, total_amount\n"
            "OCR tokens:\n"
        )
        for token in ocr_tokens:
            prompt += f"Text: '{token['text']}' at bbox {token['bbox']}\n"
        
        prompt += (
            "\nReturn only the JSON with the 'result' key, no explanation.\n"
            "Example output:\n"
            "{\n  \"result\": [\n    {\n      \"value\": { \"x\": 10.5, \"y\": 5.2, \"width\": 15.0, \"height\": 3.1, \"rotation\": 0, \"labels\": [\"invoice_number\"] }\n    }\n  ]\n}\n"
        )
        return prompt
    
    def call_groq(self, prompt, model="llama3-8b-8192", force_result_key=True):
        """Call GroqCloud API with rate limiting"""
        # Rate limiting for free tier
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.request_interval:
            time.sleep(self.request_interval - time_since_last)
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=model,
                temperature=0.1,
                max_tokens=2048  # Reduced for free tier
            )
            
            self.last_request_time = time.time()
            response_text = chat_completion.choices[0].message.content
            
            # Try to parse JSON response
            try:
                response_json = json.loads(response_text)
                if force_result_key and "result" not in response_json:
                    return {"result": []}
                return response_json
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from text
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        response_json = json.loads(json_match.group())
                        if force_result_key and "result" not in response_json:
                            return {"result": []}
                        return response_json
                    except json.JSONDecodeError:
                        pass
                
                # If all fails, return empty result
                return {"result": []}
                
        except Exception as e:
            print(f"Error calling GroqCloud: {e}")
            time.sleep(5)  # Wait longer on error
            return {"result": []}

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
