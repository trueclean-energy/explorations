#!/usr/bin/env python3
"""
test_enhanced_search.py - Test script for the LLM-enhanced search query approach

This script demonstrates how the LLM-enhanced search query approach works by:
1. Generating weather-appropriate search terms using the LLM
2. Using those terms to create a targeted search query
3. Performing a search using the Brave Search API
4. Using the LLM to suggest a specific activity based on the search results

Usage:
  python -m tests.test_enhanced_search [city] [temperature] [conditions]

Examples:
  python -m tests.test_enhanced_search "Seattle" 5 "Rain and overcast"
  python -m tests.test_enhanced_search "Dubai" 35 "Clear sky"
  python -m tests.test_enhanced_search "New York" 0 "Snow"
  python -m tests.test_enhanced_search "Paris" 20 "Partly cloudy"
"""

import os
import sys
import time
from dotenv import load_dotenv
from llm import LLMClient
from tools.brave_search import BraveSearch
from tools.activity_suggester import ActivitySuggester

def main():
    # Load environment variables
    load_dotenv()
    
    # Check for API keys
    brave_api_key = os.getenv('BRAVE_API_KEY')
    if not brave_api_key:
        print("Error: BRAVE_API_KEY environment variable not set.")
        print("Please set it in your .env file.")
        sys.exit(1)
    
    # Get provider and model from environment or use defaults
    provider = os.getenv('LLM_PROVIDER') or "together"
    model = os.getenv('LLM_MODEL') or "mistralai/Mixtral-8x7B-Instruct-v0.1"
    
    # Check for provider-specific API keys
    if provider == "together" and not os.getenv("TOGETHER_API_KEY"):
        print("Error: TOGETHER_API_KEY environment variable not set.")
        print("Please set it in your .env file.")
        sys.exit(1)
    elif provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        print("Please set it in your .env file.")
        sys.exit(1)
    
    # Get city, temperature, and conditions from command line arguments
    if len(sys.argv) >= 4:
        city = sys.argv[1]
        try:
            temperature = float(sys.argv[2])
        except ValueError:
            print("Error: Temperature must be a number.")
            sys.exit(1)
        conditions = sys.argv[3]
    else:
        # Default values
        city = "Seattle"
        temperature = 5
        conditions = "Rain and overcast"
    
    print("\n" + "="*60)
    print(f"🧪 TESTING LLM-ENHANCED SEARCH")
    print("="*60)
    
    print(f"\n🌍 Location: {city}")
    print(f"🌡️ Temperature: {temperature}°C")
    print(f"☁️ Conditions: {conditions}")
    
    # Create weather data dictionary
    weather_data = {
        "temp": temperature,
        "conditions": conditions
    }
    
    # Initialize components
    print("\n🔧 Initializing components...")
    llm = LLMClient(provider=provider, model=model)
    brave_search = BraveSearch(brave_api_key)
    activity_suggester = ActivitySuggester(brave_search, llm)
    
    print(f"✓ Using LLM: {llm.model} via {llm.provider}")
    print("✓ Brave Search API initialized")
    print("✓ Activity Suggester initialized")
    
    # Start timer
    start_time = time.time()
    
    # Get activity suggestion
    print("\n🔍 Testing LLM-enhanced search approach...")
    suggestion = activity_suggester.get_activity_suggestion(city, weather_data)
    
    # End timer
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*60)
    print("🔎 RESULTS")
    print("="*60)
    
    if suggestion:
        print("\n✅ Success! Activity suggestion:")
        print(suggestion)
    else:
        print("\n❌ Failed to get activity suggestion.")
    
    # Print performance metrics
    print(f"\n⏱️ Total processing time: {elapsed_time:.2f} seconds")
    
    # Print session summary
    print("\n📊 LLM Usage Summary:")
    llm.cost_tracker.print_session_summary()
    
    print("\n" + "="*60)
    print("🧪 TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main() 