"""
Pytest configuration and fixtures.
This file sets up the test environment before any tests run.
"""
import os
import sys

# Set test database environment variables BEFORE any app imports
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['TESTING'] = 'true'

# Add parent directory to path so app can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
