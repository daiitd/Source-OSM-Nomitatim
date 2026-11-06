from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.routes import api_bp
from app.views import views_bp
from app.openapi import openapi_bp

def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for frontend clients
    CORS(app)

    # Register blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(openapi_bp)
    app.register_blueprint(api_bp)

    return app

