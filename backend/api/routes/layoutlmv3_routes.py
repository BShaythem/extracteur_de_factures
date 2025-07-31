from flask import Blueprint, request, jsonify
import os
import tempfile
import time
from backend.services.layoutlmv3_service import extract_with_layoutlmv3

layoutlmv3_bp = Blueprint('layoutlmv3_bp', __name__)

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

@layoutlmv3_bp.route('/extract_layoutlmv3', methods=['POST'])
def extract_layoutlmv3():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Determine file extension from original filename
    original_ext = os.path.splitext(file.filename)[1].lower()
    if not original_ext:
        original_ext = '.jpg'  # Default extension
    
    # Use temporary file with proper extension
    with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as tmp_file:
        file.save(tmp_file.name)
        
        # Verify file was saved properly
        if not os.path.exists(tmp_file.name) or os.path.getsize(tmp_file.name) == 0:
            return jsonify({'error': 'Failed to save uploaded file'}), 500
        
        print(f"Saved temporary file: {tmp_file.name}, size: {os.path.getsize(tmp_file.name)} bytes")
        
        try:
            # Extract fields using LayoutLMv3
            extracted_fields = extract_with_layoutlmv3(tmp_file.name)
            
            return jsonify({
                'method': 'layoutlmv3',
                'extracted_fields': extracted_fields
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            # Clean up temporary file with retry mechanism
            safe_delete_file(tmp_file.name)
