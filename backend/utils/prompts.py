def build_llm_prompt(ocr_tokens):
    """
    Build a prompt for LLM-based invoice extraction that returns standardized format.
    """
    prompt = f"""You are an expert invoice data extraction system. Extract information from the following OCR text and return it in a specific JSON format.

OCR Text:
{ocr_tokens}

Please extract the following fields and return them in this exact JSON format:

{{
    "extracted_fields": {{
        "supplier_name": {{
            "candidates": [
                {{"confidence": 0.95, "value": "Company Name"}}
            ],
            "selected": "Company Name"
        }},
        "supplier_address": {{
            "candidates": [
                {{"confidence": 0.92, "value": "Company Address"}}
            ],
            "selected": "Company Address"
        }},
        "customer_name": {{
            "candidates": [
                {{"confidence": 0.88, "value": "Customer Name"}}
            ],
            "selected": "Customer Name"
        }},
        "customer_address": {{
            "candidates": [
                {{"confidence": 0.90, "value": "Customer Address"}}
            ],
            "selected": "Customer Address"
        }},
        "invoice_number": {{
            "candidates": [
                {{"confidence": 0.95, "value": "INV-2024-001"}}
            ],
            "selected": "INV-2024-001"
        }},
        "invoice_date": {{
            "candidates": [
                {{"confidence": 0.92, "value": "15/01/2024"}}
            ],
            "selected": "15/01/2024"
        }},
        "due_date": {{
            "candidates": [
                {{"confidence": 0.89, "value": "15/02/2024"}}
            ],
            "selected": "15/02/2024"
        }},
        "invoice_subtotal": {{
            "candidates": [
                {{"confidence": 0.94, "value": "150.00"}}
            ],
            "selected": "150.00"
        }},
        "tax_amount": {{
            "candidates": [
                {{"confidence": 0.91, "value": "15.00"}}
            ],
            "selected": "15.00"
        }},
        "tax_rate": {{
            "candidates": [
                {{"confidence": 0.93, "value": "10%"}}
            ],
            "selected": "10%"
        }},
        "invoice_total": {{
            "candidates": [
                {{"confidence": 0.96, "value": "165.00"}}
            ],
            "selected": "165.00"
        }},
        "items": {{
            "candidates": [
                {{
                    "confidence": 0.90,
                    "value": {{
                        "description": "Item Description",
                        "quantity": "1",
                        "unit_price": "150.00",
                        "total_price": "150.00"
                    }}
                }}
            ],
            "selected": [
                {{
                    "description": "Item Description",
                    "quantity": "1",
                    "unit_price": "150.00", 
                    "total_price": "150.00"
                }}
            ]
        }}
    }}
}}

IMPORTANT RULES:
1. Return ONLY valid JSON - no explanations or extra text
2. Use realistic confidence scores between 0.8-0.96
3. For each field, provide 1-3 candidates with different confidence scores
4. The "selected" value should be the candidate with highest confidence
5. If a field is not found, use empty candidates array and empty selected value
6. For items, extract all line items found in the invoice
7. Use proper date formats (DD/MM/YYYY or MM/DD/YYYY)
8. Use proper currency formats (numbers with decimal points)
9. Invoice numbers should be alphanumeric or # followed by numbers
10. Names should be actual person/company names, not header words like "DATE", "LOGO", "FROM", etc.

Extract the data now:"""

    return prompt
