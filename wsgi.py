import os
import sys
import logging

# Add your project directory to the sys.path
project_home = '/home/ubuntu/driver-inspection-app'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set up logging
logging.basicConfig(stream=sys.stderr)

# Import your application
from app import app as application

# Set secret key for production
if not application.config['SECRET_KEY']:
    application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key-change-in-production')