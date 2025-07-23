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