#!/usr/bin/env python3
"""
Database initialization script
Run this to set up the database with default templates
"""

import os
import sys

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models.database import db

def init_database():
    """Initialize the database with default templates"""
    print("Initializing database...")
    
    # The database initialization happens automatically when Database() is instantiated
    # This is already done in the import above
    
    print("Database initialized successfully!")
    print(f"Database file: {db.db_path}")
    
    # Check templates
    templates = db.get_templates()
    print(f"Total templates in database: {len(templates)}")
    
    for template in templates:
        print(f"  - {template['name']} ({template['category']}, {template['template_type']})")

if __name__ == '__main__':
    init_database()

