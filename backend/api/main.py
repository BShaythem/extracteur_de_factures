from flask import Flask
from backend.api.ollama_routes import ollama_bp
from backend.api.groq_routes import groq_bp
from backend.api.layoutlmv3_routes import layoutlmv3_bp
from backend.api.extraction_routes import extraction_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(ollama_bp, url_prefix='/api/ollama')
app.register_blueprint(groq_bp, url_prefix='/api/groq')
app.register_blueprint(layoutlmv3_bp, url_prefix='/api/layoutlmv3')
app.register_blueprint(extraction_bp, url_prefix='/api/extraction')

if __name__ == '__main__':
    app.run(debug=True)
#python -m backend.api.main
