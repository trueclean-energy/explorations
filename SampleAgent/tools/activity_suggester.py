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
        
        # 1. First, get search results about the city's attractions
        query = f"most famous landmarks monuments museums attractions {city}"
        print(f"🔍 Searching for: Activities in {city} suitable for {weather['temp']}°C, {weather['conditions']}")
        print("🔧 Using tool: brave_search API")
        search_result = self.brave_search.search(query)
        if not search_result:
            return None
            
        # 2. Use LLM to analyze weather and suggest appropriate activities
        print("\n🤔 Thinking: Analyzing weather conditions and finding suitable activities...")
        print("🧠 Using language model API for activity suggestions")
        
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
            operation="activity_suggestion"
        )
        
        # Display token usage and cost information
        if hasattr(self.llm, 'cost_tracker') and hasattr(self.llm.cost_tracker, 'last_call_info'):
            last_call = self.llm.cost_tracker.last_call_info
            input_tokens = last_call.get('input_tokens', 0)
            output_tokens = last_call.get('output_tokens', 0)
            cost = last_call.get('cost', 0)
            print(f"💰 LLM call: {input_tokens + output_tokens} tokens ({input_tokens} input, {output_tokens} output) - Cost: ${cost:.5f}")
        
        if response and 'choices' in response:
            suggestion = response['choices'][0]['message']['content'].strip()
            return suggestion
        
        return None 