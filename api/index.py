import os
import sys

# Add root directory to path to allow importing app and engine modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
