import os
import tempfile
import time
from flask import Blueprint, request, jsonify
from backend.utils.utils import run_paddle_ocr
from backend.services.ollama_service import call_ollama
from backend.utils.prompts import build_llm_prompt

ollama_bp = Blueprint('ollama_bp', __name__)

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

@ollama_bp.route('/extract_llm_ollama', methods=['POST'])
def extract_llm_ollama():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        file.save(tmp_file.name)
        try:
            # Run OCR
            ocr_tokens = run_paddle_ocr(tmp_file.name)
            if not ocr_tokens:
                return jsonify({'error': 'No text found in image'}), 400
            
            # Build prompt and call Ollama
            prompt = build_llm_prompt(ocr_tokens)
            extracted_fields = call_ollama(prompt)
            
            return jsonify({
                'method': 'llm',
                'extracted_fields': extracted_fields
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            safe_delete_file(tmp_file.name)