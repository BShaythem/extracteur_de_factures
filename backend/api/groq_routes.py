import os
import tempfile
import time
from flask import Blueprint, request, jsonify
from backend.utils.utils import run_paddle_ocr
from backend.services.groq_service import GroqService
from backend.utils.prompts import build_llm_prompt

groq_bp = Blueprint('groq_bp', __name__)

_groq_service = None
def get_groq_service():
    global _groq_service
    if _groq_service is None:
        try:
            _groq_service = GroqService()
        except Exception as e:
            print(f"Warning: Could not initialize Groq service: {e}")
            return None
    return _groq_service

def safe_delete_file(file_path, max_retries=5):
    """Safely delete a file with retries."""
    for attempt in range(max_retries):
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                print(f"Successfully deleted: {file_path}")
                return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1}: File {file_path} is still in use, retrying...")
                time.sleep(0.1)
            else:
                print(f"Warning: Could not delete {file_path} after {max_retries} attempts: {e}")
                return False
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
            return False
    return True

@groq_bp.route('/extract_llm_groq', methods=['POST'])
def extract_llm_groq():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    groq_service = get_groq_service()
    if groq_service is None:
        return jsonify({'error': 'Groq service not available. Please set GROQ_API_KEY environment variable.'}), 503
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        file.save(tmp_file.name)
        try:
            # Run OCR
            ocr_tokens = run_paddle_ocr(tmp_file.name)
            if not ocr_tokens:
                return jsonify({'error': 'No text found in image'}), 400
            
            # Build prompt and call Groq
            prompt = build_llm_prompt(ocr_tokens)
            extracted_fields = groq_service.call_groq(prompt)
            
            return jsonify({
                'method': 'llm',
                'extracted_fields': extracted_fields
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            safe_delete_file(tmp_file.name)
