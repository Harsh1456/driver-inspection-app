import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from database import db

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables with correct schema...")
    db.create_all()
    print("✅ Database reset successfully with image_path column!")
    print("You can now run: python app.py")