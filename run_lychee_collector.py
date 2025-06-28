#!/usr/bin/env python3
"""
Lychee Data Collector - Main Entry Point
Run this file to start the application
"""

import tkinter as tk
import sys
import os

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from lychee_collector.main_app import main

if __name__ == "__main__":
    print("Starting Lychee Data Collector...")
    print("Features:")
    print("• Dual camera support with live editing")
    print("• Real-time image processing (rotate, flip, crop)")
    print("• iPhone Continuity Camera detection")
    print("• Complete data management system")
    print("• Enhanced camera selection")
    print("=" * 50)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)