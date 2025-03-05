import os
import requests
from typing import Optional
import re

class BraveSearch:
    """Simple wrapper for Brave Search API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
    
    def search(self, query: str) -> Optional[str]:
        """Make a search query and return the most relevant result"""
        print(f"🔍 Searching Brave: '{query}'")  # Debug log
        
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
        
        params = {
            "q": query,
            "count": 3  # Get top 3 results to find the most relevant
        }
        
        try:
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("web", {}).get("results"):
                    result = data["web"]["results"][0]["description"]
                    print(f"✓ Found: {result[:100]}...")  # Debug log
                    return result
                print("❌ No results found")  # Debug log
            else:
                print(f"❌ Brave Search error: {response.status_code} - {response.text}")  # Debug log
            return None
        except Exception as e:
            print(f"❌ Brave Search error: {e}")
            return None
    
    def get_activity_suggestion(self, city: str, weather: dict) -> Optional[str]:
        """Get weather-appropriate activity suggestion"""
        print("\n🤔 Thinking: Finding a suitable activity for the current weather...")
        
        temp = float(weather['temp'])
        conditions = weather['conditions'].lower()
        
        # Weather-aware query construction
        weather_context = []
        if 'rain' in conditions or 'storm' in conditions:
            weather_context = ["indoor", "rainy day", "museum", "indoor attractions"]
            query = f"indoor activities museums attractions {city} when raining -tripadvisor -yelp"
        elif 'snow' in conditions:
            weather_context = ["winter", "snow", "cozy"]
            query = f"winter indoor activities attractions {city} snow day -tripadvisor -yelp"
        elif temp > 30:
            weather_context = ["cool", "indoor", "air-conditioned", "escape heat"]
            query = f"indoor air-conditioned attractions {city} escape heat -tripadvisor -yelp"
        elif temp < 5:
            weather_context = ["warm", "indoor", "cozy"]
            query = f"indoor warm cozy attractions {city} winter -tripadvisor -yelp"
        elif 'clear' in conditions and 15 <= temp <= 25:
            weather_context = ["outdoor", "nice weather", "perfect day"]
            query = f"outdoor attractions {city} nice weather -tripadvisor -yelp"
        else:
            weather_context = ["popular", "must-see"]
            query = f"must visit famous attractions {city} -tripadvisor -yelp"
        
        print(f"Weather Context: {', '.join(weather_context)}")
        print(f"🔍 Searching for: Activities in {city} suitable for {weather['temp']}°C, {weather['conditions']}")
        
        result = self.search(query)
        if result:
            # Clean up the suggestion
            suggestion = result.split('.')[0]  # Take first sentence
            
            # Remove HTML and formatting artifacts
            suggestion = re.sub(r'<[^>]+>', '', suggestion)  # Remove HTML tags
            suggestion = re.sub(r'&\w+;', '', suggestion)   # Remove HTML entities
            suggestion = re.sub(r'\b(top|best|popular)\b', '', suggestion, flags=re.I)
            suggestion = re.sub(r'\s+', ' ', suggestion).strip()
            
            # Extract meaningful activity
            if len(suggestion) > 100 or any(x in suggestion.lower() for x in ['tripadvisor', 'yelp', 'reviews']):
                for pattern in [
                    r'(?:visit|explore|enjoy)\s+([^,.]+)',
                    r'(?:the|at)\s+([^,.]+(?:Museum|Park|Garden|Bridge|Tower|Palace|Castle|Square|Market|Aquarium|Gallery|Theater|Centre|Center))',
                    r'([^,.]+(?:Museum|Park|Garden|Bridge|Tower|Palace|Castle|Square|Market|Aquarium|Gallery|Theater|Centre|Center))'
                ]:
                    if match := re.search(pattern, suggestion, re.I):
                        suggestion = match.group(1).strip()
                        break
                else:
                    return None
            
            # Format the suggestion based on weather context
            weather_note = ""
            if 'indoor' in ' '.join(weather_context).lower():
                weather_note = " (perfect indoor activity for this weather)"
            elif 'outdoor' in ' '.join(weather_context).lower():
                weather_note = " (great weather for outdoor activities)"
            
            print(f"✓ Found suitable activity: {suggestion}")
            return f"\n🎯 Suggested Activity: {suggestion}{weather_note}"
        
        print("❌ Could not find a suitable activity")
        return None 