"""Activity suggestion tool that uses LLM to provide contextual recommendations"""

from typing import Optional, Dict
from .brave_search import BraveSearch

class ActivitySuggester:
    """Suggests weather-appropriate activities using LLM coordination"""
    
    def __init__(self, brave_search: BraveSearch, llm_client):
        self.brave_search = brave_search
        self.llm = llm_client
    
    def get_activity_suggestion(self, city: str, weather: dict, is_forecast: bool = False) -> Optional[str]:
        """Get weather-appropriate activity suggestion using LLM coordination
        
        Args:
            city: City name
            weather: Weather data dict with 'temp' and 'conditions'
            is_forecast: Whether this is forecast data (future) or current weather
        
        Returns:
            Activity suggestion string or None if not available
        """
        
        # 1. First, use LLM to generate weather-appropriate search terms
        print("\n🤔 Thinking: Generating weather-appropriate search terms...")
        
        weather_prompt = f"""
Given these weather conditions for {city}:
- Temperature: {weather['temp']}°C
- Conditions: {weather['conditions']}

Generate 3-5 specific search terms that would help find weather-appropriate attractions.
Consider both the temperature and weather conditions to suggest terms that would lead to comfortable activities.

Examples:
- If it's raining: indoor museum gallery theater covered
- If it's hot (>30°C): air-conditioned indoor aquarium mall shade
- If it's cold (<5°C): indoor warm cozy museum cafe
- If it's pleasant: outdoor park garden walking sightseeing

Respond with ONLY the search terms, separated by spaces. Keep it brief (max 7 words).
Do NOT include quotes or multiple lines in your response.
"""
        
        search_terms_response = self.llm.generate(
            prompt=weather_prompt,
            operation="search_terms"  # Using the new operation setting
        )
        
        # Display token usage for the search terms generation
        if hasattr(self.llm, 'cost_tracker') and hasattr(self.llm.cost_tracker, 'last_call_info'):
            last_call = self.llm.cost_tracker.last_call_info
            input_tokens = last_call.get('input_tokens', 0)
            output_tokens = last_call.get('output_tokens', 0)
            cost = last_call.get('cost', 0)
            print(f"💰 LLM call (search terms): {input_tokens + output_tokens} tokens ({input_tokens} input, {output_tokens} output) - Cost: ${cost:.5f}")
        
        # Extract search terms from the response and clean them
        search_terms = ""
        if search_terms_response and 'choices' in search_terms_response:
            raw_terms = search_terms_response['choices'][0]['message']['content'].strip()
            
            # Clean up the terms - remove quotes, newlines, and extra spaces
            search_terms = raw_terms.replace('"', '').replace('\n', ' ').strip()
            
            # If we have multiple lines or suggestions, just take the first set of terms
            if '\n' in search_terms:
                search_terms = search_terms.split('\n')[0].strip()
                
            print(f"🔍 Generated search terms: {search_terms}")
        
        # 2. Use the generated search terms to create a more targeted query
        query = f"{search_terms} attractions {city}"
        print(f"🔍 Creating search query: '{query}'")
        
        # 3. Perform the search using Brave Search API
        print("🔎 Executing Brave search...")
        search_result = self.brave_search.search(query)
        
        if not search_result:
            # Fallback to a more generic query if the specific one fails
            query = f"most famous landmarks monuments museums attractions {city}"
            print(f"🔍 Fallback search: '{query}'")
            search_result = self.brave_search.search(query)
            
            # Try one more time with a simpler query if still no results
            if not search_result:
                query = f"tourist attractions {city}"
                print(f"🔍 Second fallback search: '{query}'")
                search_result = self.brave_search.search(query)
                if not search_result:
                    print("❌ All searches failed. No results found.")
                    return None
        
        # 4. Now that we have search results, use LLM to analyze and suggest activities
        print("\n🤔 Thinking: Analyzing weather conditions and search results...")
        print("🧠 Using language model to generate activity suggestion")
        
        # Adjust prompt based on whether this is current or forecast data
        if is_forecast:
            time_context = "for the forecasted weather"
            planning_context = "This is a future forecast, so the suggestion should be appropriate for planning ahead."
        else:
            time_context = "for today's weather"
            planning_context = "This is the current weather, so the suggestion should be immediately actionable."
        
        prompt = f"""You are a deep local person from {city} with multiple years of experience. You are the expert in {city} and with your answers you need to impress a tourist to your city.

Given the weather conditions and search results for {city}, suggest ONE specific attraction or activity that would be most appropriate {time_context}.

Weather conditions: {weather['temp']}°C, {weather['conditions']}
{planning_context}

Search results about {city}:
{search_result}

Based on these weather conditions and the search results, what ONE specific activity or attraction would you recommend to a visitor to {city}? 
Explain why it's a good choice given the current weather conditions.

Your response should be in this format:
"\n\nRecommended Activity: [Your specific activity recommendation]
[2-3 sentences explaining why this is a good choice for the weather conditions]"
"""

        response = self.llm.generate(
            prompt=prompt,
            operation="suggest_activity"
        )
        
        # Display token usage and cost information
        if hasattr(self.llm, 'cost_tracker') and hasattr(self.llm.cost_tracker, 'last_call_info'):
            last_call = self.llm.cost_tracker.last_call_info
            input_tokens = last_call.get('input_tokens', 0)
            output_tokens = last_call.get('output_tokens', 0)
            cost = last_call.get('cost', 0)
            print(f"💰 LLM call (activity suggestion): {input_tokens + output_tokens} tokens ({input_tokens} input, {output_tokens} output) - Cost: ${cost:.5f}")
        
        if response and 'choices' in response:
            suggestion = response['choices'][0]['message']['content'].strip()
            return suggestion
        
        return None 