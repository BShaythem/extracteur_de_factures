from flask import Blueprint, request, jsonify
import os
from backend.utils.utils import run_paddle_ocr
from backend.services.groq_service import GroqService

groq_bp = Blueprint('groq_bp', __name__)
groq_service = GroqService()

@groq_bp.route('/extract_llm_groq', methods=['POST'])
def extract_llm_groq():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    os.makedirs('data', exist_ok=True)
    file_path = os.path.join('data', file.filename)
    file.save(file_path)
    try:
        ocr_tokens = run_paddle_ocr(file_path)
        prompt = groq_service.build_llm_prompt2(ocr_tokens)
        llm_json = groq_service.call_groq(prompt)
        return jsonify({'llm_extracted_fields': llm_json})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
