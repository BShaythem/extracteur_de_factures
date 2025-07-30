from flask import Blueprint, request, jsonify
import os
import tempfile
import time
from backend.services.ollama_service import build_llm_prompt, call_ollama
from backend.services.layoutlmv3_service import extract_with_layoutlmv3
from backend.utils.utils import run_paddle_ocr

extraction_bp = Blueprint('extraction_bp', __name__)

def safe_delete_file(file_path, max_retries=3):
    """Safely delete a file with retries for Windows file locking issues"""
    for attempt in range(max_retries):
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                return True
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.1)  # Small delay before retry
            else:
                print(f"Warning: Could not delete temporary file {file_path}")
                return False
        except Exception as e:
            print(f"Warning: Error deleting file {file_path}: {e}")
            return False
    return True

@extraction_bp.route('/extract', methods=['POST'])
def extract_invoice():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    method = request.form.get('method', 'llm')  # llm, layoutlmv3, donut
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Use temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        file.save(tmp_file.name)
        try:
            if method == 'llm':
                # Use LLM approach
                ocr_tokens = run_paddle_ocr(tmp_file.name)
                prompt = build_llm_prompt(ocr_tokens)
                extracted_fields = call_ollama(prompt)
            elif method == 'layoutlmv3':
                # Use LayoutLMv3 approach
                extracted_fields = extract_with_layoutlmv3(tmp_file.name)
            elif method == 'donut':
                # Use Donut approach (you'll need to implement this)
                extracted_fields = extract_with_donut(tmp_file.name)
            else:
                return jsonify({'error': 'Invalid method'}), 400
            
            return jsonify({
                'method': method,
                'extracted_fields': extracted_fields
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            # Clean up temporary file with retry mechanism
            safe_delete_file(tmp_file.name)
