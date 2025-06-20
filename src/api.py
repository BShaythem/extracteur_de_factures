# filepath: src/api.py
from flask import Flask, request, jsonify
from utils import extract_text_from_any_file
import os
#to start the server, run: python src/api.py
#curl -X POST -F "file=@data/invoice_sample.png" http://127.0.0.1:5000/extract
app = Flask(__name__)

@app.route('/extract', methods=['POST'])
def extract():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    os.makedirs('data', exist_ok=True)  # Crée le dossier si besoin
    file_path = os.path.join('data', file.filename)
    file.save(file_path)
    try:
        text = extract_text_from_any_file(file_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'extracted_text': text})

if __name__ == '__main__':
    app.run(debug=True)