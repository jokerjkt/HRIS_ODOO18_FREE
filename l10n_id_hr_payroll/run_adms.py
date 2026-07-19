#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADMS Server Entry Point
========================
Jalankan: python run_adms.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_adms.app import main

if __name__ == '__main__':
    main()
