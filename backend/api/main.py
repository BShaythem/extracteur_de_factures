from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from backend.api.routes.ollama_routes import ollama_bp
from backend.api.routes.groq_routes import groq_bp
from backend.api.routes.layoutlmv3_routes import layoutlmv3_bp
from backend.api.routes.extraction_routes import extraction_bp
from backend.api.routes.auth_routes import auth_bp, init_db
from backend.api.routes.invoice_routes import invoice_bp, init_invoice_db

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Enable CORS for frontend communication
CORS(app, supports_credentials=True)

# Initialize databases
init_db()
init_invoice_db()

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(invoice_bp, url_prefix='/api/invoice')
app.register_blueprint(ollama_bp, url_prefix='/api/ollama')
app.register_blueprint(groq_bp, url_prefix='/api/groq')
app.register_blueprint(layoutlmv3_bp, url_prefix='/api/layoutlmv3')
app.register_blueprint(extraction_bp, url_prefix='/api/extraction')

if __name__ == '__main__':
    app.run(debug=True)
#python -m backend.api.main
