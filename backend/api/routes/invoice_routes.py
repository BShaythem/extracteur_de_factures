from flask import Blueprint, request, jsonify, session
import sqlite3
import json
import os
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
from backend.api.routes.auth_routes import require_auth

invoice_bp = Blueprint('invoice', __name__)

# Determine project root (repo root) and absolute uploads directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
UPLOADS_DIR = os.path.join(PROJECT_ROOT, 'uploads')
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR, exist_ok=True)


def resolve_image_path(stored_path: str) -> str | None:
    """Resolve stored image path to an absolute existing path.

    - If stored_path is absolute and exists → return it
    - If stored_path is relative, try relative to PROJECT_ROOT → return if exists
    - Otherwise return None
    """
    try:
        if not stored_path:
            return None
        # Absolute path
        if os.path.isabs(stored_path) and os.path.exists(stored_path):
            return stored_path
        # Relative to project root
        candidate = os.path.join(PROJECT_ROOT, stored_path)
        if os.path.exists(candidate):
            return os.path.abspath(candidate)
        return None
    except Exception:
        return None

def init_invoice_db():
    """Initialize the SQLite database for invoices"""
    conn = sqlite3.connect('invoices.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            extracted_fields TEXT NOT NULL,
            method TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id)
        )
    ''')
    conn.commit()
    # Lightweight migration: ensure 'status' column exists
    try:
        cursor.execute("PRAGMA table_info(invoices)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'status' not in cols:
            cursor.execute("ALTER TABLE invoices ADD COLUMN status TEXT NOT NULL DEFAULT 'Draft'")
            conn.commit()
    except Exception:
        # If pragma fails, proceed without blocking app startup
        pass

    conn.close()

@invoice_bp.route('/invoices', methods=['POST'])
@require_auth
def save_invoice():
    """Save extracted invoice data with file upload"""
    try:
        user_id = session['user_id']
        
        # Check if file was uploaded
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Get extracted fields from request
        extracted_fields = request.form.get('extracted_fields')
        method = request.form.get('method', 'unknown')
        
        if not extracted_fields:
            return jsonify({'error': 'No extracted fields provided'}), 400
        
        # Validate JSON
        try:
            fields_data = json.loads(extracted_fields)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON in extracted_fields'}), 400
        
        # Save image file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{user_id}_{timestamp}_{filename}"
        image_path = os.path.join(UPLOADS_DIR, unique_filename)
        
        file.save(image_path)
        
        # Save to database
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO invoices (user_id, image_path, extracted_fields, method)
            VALUES (?, ?, ?, ?)
        ''', (user_id, image_path, extracted_fields, method))
        
        invoice_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Invoice saved successfully',
            'invoice_id': invoice_id,
            'image_path': image_path
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_bp.route('/invoices/data', methods=['POST'])
@require_auth
def save_invoice_data():
    """Save extracted invoice data without file upload"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        extracted_fields = data.get('extracted_fields')
        method = data.get('method', 'unknown')
        
        if not extracted_fields:
            return jsonify({'error': 'No extracted fields provided'}), 400
        
        # Create a placeholder image path since no file was uploaded
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_path = f"placeholder_{user_id}_{timestamp}.txt"
        
        # Save to database
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO invoices (user_id, image_path, extracted_fields, method)
            VALUES (?, ?, ?, ?)
        ''', (user_id, image_path, json.dumps(extracted_fields), method))
        
        invoice_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Invoice data saved successfully',
            'invoice_id': invoice_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_bp.route('/invoices', methods=['GET'])
@require_auth
def get_user_invoices():
    """Get all invoices for the current user"""
    try:
        user_id = session['user_id']
        
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, image_path, extracted_fields, method, status, created_at
            FROM invoices 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        invoices = []
        for row in cursor.fetchall():
            try:
                invoice_id, image_path, extracted_fields, method, status, created_at = row

                # Safely check if image file exists
                try:
                    # Resolve absolute path considering project root
                    resolved_path = resolve_image_path(image_path)
                    image_exists = bool(resolved_path)
                except Exception:
                    image_exists = False

                # Safely parse extracted_fields JSON
                try:
                    parsed_fields = json.loads(extracted_fields) if isinstance(extracted_fields, str) else (extracted_fields or {})
                except Exception:
                    parsed_fields = {}

                # Helper to get a simple summary value from extracted fields structure
                def get_selected(fields: dict, key: str):
                    try:
                        value_obj = fields.get(key)
                        if isinstance(value_obj, dict):
                            selected = value_obj.get('selected')
                            # If candidates only and no selected, fallback to first candidate value
                            if not selected and isinstance(value_obj.get('candidates'), list) and value_obj['candidates']:
                                return value_obj['candidates'][0].get('value')
                            return selected
                        return None
                    except Exception:
                        return None

                invoices.append({
                    'id': invoice_id,
                    'image_path': image_path,
                    'image_exists': image_exists,
                    'extracted_fields': parsed_fields,
                    'method': method,
                    'status': status,
                    'created_at': created_at,
                    # Flatten common fields for easier frontend use
                    'invoice_number': get_selected(parsed_fields, 'invoice_number'),
                    'supplier_name': get_selected(parsed_fields, 'supplier_name'),
                    'customer_name': get_selected(parsed_fields, 'customer_name'),
                    'invoice_total': get_selected(parsed_fields, 'invoice_total')
                })
            except Exception:
                # Skip malformed rows rather than failing the entire response
                continue
        
        conn.close()
        
        return jsonify({'invoices': invoices}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@require_auth
def get_invoice(invoice_id):
    """Get a specific invoice"""
    try:
        user_id = session['user_id']
        
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, image_path, extracted_fields, method, status, created_at
            FROM invoices 
            WHERE id = ? AND user_id = ?
        ''', (invoice_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Invoice not found'}), 404
        
        invoice_id, image_path, extracted_fields, method, status, created_at = row

        # Safely check if image file exists
        try:
            resolved_path = resolve_image_path(image_path)
            image_exists = bool(resolved_path)
        except Exception:
            image_exists = False

        # Safely parse extracted_fields JSON
        try:
            parsed_fields = json.loads(extracted_fields) if isinstance(extracted_fields, str) else (extracted_fields or {})
        except Exception:
            parsed_fields = {}

        def get_selected(fields: dict, key: str):
            try:
                value_obj = fields.get(key)
                if isinstance(value_obj, dict):
                    selected = value_obj.get('selected')
                    if not selected and isinstance(value_obj.get('candidates'), list) and value_obj['candidates']:
                        return value_obj['candidates'][0].get('value')
                    return selected
                return None
            except Exception:
                return None

        return jsonify({
            'id': invoice_id,
            'image_path': image_path,
            'image_exists': image_exists,
            'extracted_fields': parsed_fields,
            'method': method,
            'status': status,
            'created_at': created_at,
            'invoice_number': get_selected(parsed_fields, 'invoice_number'),
            'supplier_name': get_selected(parsed_fields, 'supplier_name'),
            'customer_name': get_selected(parsed_fields, 'customer_name'),
            'invoice_total': get_selected(parsed_fields, 'invoice_total')
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_bp.route('/invoices/<int:invoice_id>', methods=['PUT'])
@require_auth
def update_invoice(invoice_id):
    """Update extracted fields for an invoice"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        extracted_fields = data.get('extracted_fields')
        
        if not extracted_fields:
            return jsonify({'error': 'No extracted fields provided'}), 400
        
        # Validate JSON
        try:
            fields_data = json.loads(extracted_fields) if isinstance(extracted_fields, str) else extracted_fields
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON in extracted_fields'}), 400
        
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        # Check if invoice exists and belongs to user
        cursor.execute('SELECT id FROM invoices WHERE id = ? AND user_id = ?', 
                      (invoice_id, user_id))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Invoice not found'}), 404
        
        # Update the invoice
        cursor.execute('''
            UPDATE invoices 
            SET extracted_fields = ?, status = ?
            WHERE id = ? AND user_id = ?
        ''', (json.dumps(fields_data), data.get('status', 'Draft'), invoice_id, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Invoice updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@require_auth
def delete_invoice(invoice_id):
    """Delete an invoice"""
    try:
        user_id = session['user_id']
        
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        # Get image path before deleting
        cursor.execute('SELECT image_path FROM invoices WHERE id = ? AND user_id = ?', 
                      (invoice_id, user_id))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Invoice not found'}), 404
        
        image_path = row[0]
        
        # Delete from database
        cursor.execute('DELETE FROM invoices WHERE id = ? AND user_id = ?', 
                      (invoice_id, user_id))
        
        conn.commit()
        conn.close()
        
        # Delete image file if it exists
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                print(f"Warning: Could not delete image file {image_path}: {e}")
        
        return jsonify({'message': 'Invoice deleted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_bp.route('/invoices/<int:invoice_id>/image', methods=['GET'])
@require_auth
def get_invoice_image(invoice_id):
    """Get the image file for an invoice"""
    try:
        user_id = session['user_id']
        
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT image_path FROM invoices WHERE id = ? AND user_id = ?', 
                      (invoice_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Invoice not found'}), 404
        
        image_path = row[0]

        # Resolve absolute path and verify existence
        try:
            abs_path = os.path.abspath(image_path)
        except Exception:
            abs_path = image_path

        if not (abs_path and os.path.exists(abs_path)):
            return jsonify({'error': 'Image file not found'}), 404

        # Guess mimetype from extension
        import mimetypes
        mime, _ = mimetypes.guess_type(abs_path)
        if not mime:
            mime = 'application/octet-stream'

        # Stream the file; guard against unexpected file IO errors
        from flask import send_file
        try:
            return send_file(abs_path, mimetype=mime, conditional=True, as_attachment=False)
        except Exception as e:
            # Don't 500 on image issues; report as not found to let UI fallback
            return jsonify({'error': f'Unable to read image: {str(e)}'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 