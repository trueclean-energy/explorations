#!/usr/bin/env python3
"""
run_enhanced_search_test.py - Simple script to run the enhanced search test

This script is a convenience wrapper to run the enhanced search test from the main directory.

Usage:
  python run_enhanced_search_test.py [city] [temperature] [conditions]

Examples:
  python run_enhanced_search_test.py "Seattle" 5 "Rain and overcast"
  python run_enhanced_search_test.py "Dubai" 35 "Clear sky"
  python run_enhanced_search_test.py "New York" 0 "Snow"
  python run_enhanced_search_test.py "Paris" 20 "Partly cloudy"
"""

import sys
from tests.test_enhanced_search import main

if __name__ == "__main__":
    # Pass command line arguments to the test script
    main() 