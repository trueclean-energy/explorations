#!/usr/bin/env python3
# example_llm.py - Example of using the LLM client with different providers and models
import os
import sys
import json
from llm import LLMClient

def main():
    """
    Example of using the LLM client with different providers and models.
    This example shows how to switch between Together and OpenRouter,
    and how to use different models with each provider.
    """
    # Check command line arguments
    if len(sys.argv) > 1:
        provider = sys.argv[1].lower()
        model = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        provider = "together"  # Default provider
        model = None  # Use default model for the provider
    
    # Verify API keys are set
    if provider == "together" and not os.getenv("TOGETHER_API_KEY"):
        print("Error: TOGETHER_API_KEY environment variable not set.")
        print("Please set it with: export TOGETHER_API_KEY=your_api_key")
        sys.exit(1)
    elif provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        print("Please set it with: export OPENROUTER_API_KEY=your_api_key")
        sys.exit(1)
    
    try:
        # Create LLM client with specified provider and model
        llm = LLMClient(provider=provider, model=model)
        
        # Print the selected provider and model
        print(f"Using provider: {llm.provider}")
        print(f"Using model: {llm.model}")
        
        # Demonstrate different operations
        print("\n=== Example 1: Basic Generation ===")
        basic_prompt = "Explain the concept of transfer learning in 2-3 sentences."
        print(f"Sending prompt to {llm.model} via {llm.provider}...")
        basic_response = llm.generate(basic_prompt)
        print_response(basic_response, llm)
        
        print("\n=== Example 2: Weather-Based Search Terms Generation ===")
        # Example weather data
        weather_data = {
            "city": "Seattle",
            "temp": 5,
            "conditions": "Rain and overcast"
        }
        
        # Create a prompt for generating search terms
        search_terms_prompt = f"""
Given these weather conditions for {weather_data['city']}:
- Temperature: {weather_data['temp']}°C
- Conditions: {weather_data['conditions']}

Generate 3-5 specific search terms that would help find weather-appropriate attractions.
Consider both the temperature and weather conditions to suggest terms that would lead to comfortable activities.

Examples:
- If it's raining: indoor, museum, gallery, theater, covered
- If it's hot (>30°C): air-conditioned, indoor, aquarium, mall, shade
- If it's cold (<5°C): indoor, warm, cozy, museum, cafe
- If it's pleasant: outdoor, park, garden, walking, sightseeing

Respond with ONLY the search terms, separated by spaces. Keep it brief (max 7 words).
"""
        
        print(f"Generating weather-appropriate search terms for {weather_data['city']}...")
        print(f"Weather: {weather_data['temp']}°C, {weather_data['conditions']}")
        
        # Use the search_terms operation for optimal settings
        search_terms_response = llm.generate(
            prompt=search_terms_prompt,
            operation="search_terms"
        )
        
        print_response(search_terms_response, llm)
        
        # Extract the search terms
        if 'choices' in search_terms_response and search_terms_response['choices'][0]['message']['content']:
            search_terms = search_terms_response['choices'][0]['message']['content'].strip()
            print(f"\nGenerated search terms: {search_terms}")
            
            # Show how these terms would be used in a search query
            search_query = f"{search_terms} attractions landmarks {weather_data['city']}"
            print(f"Resulting search query: '{search_query}'")
        
        print("\n=== Example 3: City Verification ===")
        verify_prompt = """
Analyze the location 'Cambridge' and provide information in the following JSON format:
{
  "is_valid": true/false,
  "city": "Correct city name with proper capitalization",
  "country": "Primary country where this city is located",
  "alternates": ["Country1", "Country2"],  // If same city name exists in multiple countries
  "confidence": 0.0-1.0,  // How confident in this identification
  "disambiguation": "Additional context if needed"
}

Provide only the JSON response, no additional text.
"""
        
        print("Verifying city information...")
        verify_response = llm.generate(
            prompt=verify_prompt,
            operation="verify_city"
        )
        
        print_response(verify_response, llm)
        
        # Parse and display the JSON response
        if 'choices' in verify_response and verify_response['choices'][0]['message']['content']:
            try:
                city_info = json.loads(verify_response['choices'][0]['message']['content'].strip())
                print("\nParsed city information:")
                print(f"City: {city_info.get('city', 'Unknown')}")
                print(f"Country: {city_info.get('country', 'Unknown')}")
                print(f"Confidence: {city_info.get('confidence', 0)}")
                if city_info.get('alternates'):
                    print(f"Also exists in: {', '.join(city_info['alternates'])}")
                if city_info.get('disambiguation'):
                    print(f"Note: {city_info['disambiguation']}")
            except json.JSONDecodeError:
                print("Could not parse JSON response")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nUsage:")
        print("  python example_llm.py [provider] [model]")
        print("\nExamples:")
        print("  python example_llm.py                                    # Use default provider (Together) and model (Mixtral)")
        print("  python example_llm.py together                           # Use Together AI with default model")
        print("  python example_llm.py together meta-llama/Llama-2-70b-chat  # Use Together AI with Llama 2 model")
        print("  python example_llm.py openrouter                         # Use OpenRouter with default model (DeepSeek R1)")
        print("  python example_llm.py openrouter deepseek/deepseek-r1:free  # Use OpenRouter with DeepSeek R1 model")

def print_response(response, llm):
    """Print the response content and token usage information"""
    if 'choices' in response and response['choices'][0]['message']['content']:
        content = response['choices'][0]['message']['content']
        print("\nResponse:")
        print(content)
    else:
        print("\nNo valid content in the response.")
        print("Response object:")
        print(response)
    
    # Print token usage and cost
    if hasattr(llm, 'cost_tracker') and hasattr(llm.cost_tracker, 'last_call_info'):
        call_info = llm.cost_tracker.last_call_info
        if call_info:
            print(f"\nToken usage: {call_info['input_tokens']} input, {call_info['output_tokens']} output")
            print(f"Estimated cost: ${call_info['cost']:.6f}")

if __name__ == "__main__":
    main() 