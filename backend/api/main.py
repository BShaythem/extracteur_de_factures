from flask import Flask
from backend.api.ollama_routes import ollama_bp
from backend.api.groq_routes import groq_bp
# Import other blueprints/routes as needed

app = Flask(__name__)
app.register_blueprint(ollama_bp)
app.register_blueprint(groq_bp)

if __name__ == '__main__':
    app.run(debug=True)
#python -m backend.api.main