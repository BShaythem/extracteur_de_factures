from flask import Blueprint, request, jsonify
import os
from backend.utils.utils import run_paddle_ocr
from backend.services.ollama_service import build_llm_prompt, call_ollama

ollama_bp = Blueprint('ollama_bp', __name__)

@ollama_bp.route('/extract_llm_ollama', methods=['POST'])
def extract_llm_ollama():
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
        prompt = build_llm_prompt(ocr_tokens)
        llm_json = call_ollama(prompt)
        return jsonify({'llm_extracted_fields': llm_json})
    except Exception as e:
        return jsonify({'error': str(e)}), 500