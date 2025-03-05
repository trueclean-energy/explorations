import os
import requests
from typing import Optional
import re
import time

class BraveSearch:
    """Simple wrapper for Brave Search API"""
    
    # Known valid attractions for major cities
    CITY_ATTRACTIONS = {
        "Seattle": ["Space Needle", "Pike Place Market", "Museum of Pop Culture", 
                   "Chihuly Garden", "Seattle Art Museum", "Pacific Science Center"],
        "New York": ["Empire State Building", "Central Park", "Metropolitan Museum", 
                    "Times Square", "Statue of Liberty"],
        # Add more cities
    }
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
    
    def validate_suggestion(self, suggestion: str, city: str) -> bool:
        """Validate if a suggestion is legitimate for a city"""
        if not suggestion or len(suggestion) > 100:
            return False
            
        # Check against known attractions if city is in our database
        if city in self.CITY_ATTRACTIONS:
            return any(attr.lower() in suggestion.lower() 
                      for attr in self.CITY_ATTRACTIONS[city])
        
        # For unknown cities, check for common attraction patterns
        return bool(re.search(r'\b(Museum|Park|Garden|Tower|Palace|Temple|Castle|Square|Market)\b', 
                            suggestion, re.I))
    
    def search(self, query: str) -> Optional[str]:
        """Make a search query and return the most relevant result"""
        if not query or len(query.strip()) < 3:
            return None
            
        # Log the search query without duplicating what the activity suggester already logged
        print(f"🔍 Executing Brave Search API call for: '{query}'")
        
        try:
            response = requests.get(
                self.base_url,
                headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
                params={"q": query, "count": 5}
            )
            
            if response.status_code == 200:
                data = response.json()
                if results := data.get("web", {}).get("results"):
                    # Filter out administrative/contact pages
                    filtered_results = [
                        r for r in results 
                        if not any(term in r.get("description", "").lower() 
                                 for term in ["address:", "phone:", "contact", "directions to", 
                                            "office hours", "welcome to", "official website"])
                    ]
                    
                    if filtered_results:
                        print(f"✓ Found {len(filtered_results)} relevant results")
                        return filtered_results[0]["description"]
                    else:
                        print("⚠️ No relevant results after filtering")
                else:
                    print("⚠️ No results found in API response")
            elif response.status_code == 429:
                print("⚠️ Rate limit hit, waiting before retry...")
                time.sleep(2)
            else:
                print(f"⚠️ API returned status code: {response.status_code}")
            return None
        except Exception as e:
            print(f"❌ Brave Search error: {e}")
            return None
    
    def get_activity_suggestion(self, city: str, weather: dict) -> Optional[str]:
        """Get weather-appropriate activity suggestion"""
        print("\n🤔 Thinking: Finding a suitable activity for the current weather...")
        
        # Debug logging
        print(f"Debug: Input city = {city}")
        print(f"Debug: Weather data = {weather}")
        
        temp = float(weather['temp'])
        conditions = weather['conditions'].lower()
        
        print(f"Debug: Parsed temperature = {temp}°C")
        print(f"Debug: Parsed conditions = {conditions}")
        
        # Weather-aware query construction with more specific terms
        if 'rain' in conditions or 'storm' in conditions:
            print("Debug: Using rain/storm context")
            weather_context = "indoor"
            query = f"famous indoor museum gallery {city} -tripadvisor -booking"
        elif 'snow' in conditions:
            print("Debug: Using snow context")
            weather_context = "indoor"
            query = f"best indoor attractions {city} museum gallery -tripadvisor -booking"
        elif temp > 30:
            print("Debug: Using hot weather context")
            weather_context = "indoor"
            query = f"famous shopping mall museum gallery aquarium {city} -tripadvisor -yelp"
        elif temp < 5:
            print("Debug: Using cold weather context")
            weather_context = "indoor"
            query = f"indoor cultural attractions {city} museum gallery -tripadvisor -booking"
        elif 'clear' in conditions and 15 <= temp <= 25:
            print("Debug: Using nice weather context")
            weather_context = "outdoor"
            query = f"must visit landmark monument park {city} -tripadvisor -booking"
        else:
            print("Debug: Using default context")
            weather_context = "general"
            query = f"most famous landmark monument {city} -tripadvisor -booking"
        
        print(f"Debug: Final query = {query}")
        
        # Known attraction patterns with word boundaries
        attraction_patterns = [
            r'\b(?:the\s+)?((?:[A-Z][a-z\']+ )*(?:Museum|Gallery|Park|Garden|Tower|Palace|Temple|Castle|Square|Market|Aquarium|Theatre|Center|Centre))\b',
            r'\b(?:the\s+)?((?:[A-Z][a-z\']+ )*(?:Cathedral|Mosque|Shrine|Monument|Bridge|Library|Opera House|Stadium))\b',
            # Famous specific landmarks
            r'\b(?:the\s+)?((?:Taj Mahal|Eiffel Tower|Big Ben|Tower Bridge|Space Needle|Empire State Building|Petronas Towers|Marina Bay Sands))\b'
        ]
        
        # Try to find a valid attraction
        result = self.search(query)
        if not result:  # If first search fails, try a simpler query
            query = f"most famous landmark {city}"
            print(f"Debug: Fallback query = {query}")
            result = self.search(query)
        
        if result:
            # Clean up the result
            result = re.sub(r'<[^>]+>', '', result)  # Remove HTML
            result = re.sub(r'&\w+;', '', result)    # Remove HTML entities
            
            # Try to extract a valid attraction name
            for pattern in attraction_patterns:
                if match := re.search(pattern, result, re.I):
                    attraction = match.group(1).strip()
                    # Validate the attraction
                    if (
                        attraction 
                        and len(attraction) >= 3  # Must be at least 3 chars
                        and len(attraction) <= 50  # But not too long
                        and not any(x in attraction.lower() for x in ['things to do', 'attractions in', 'welcome to'])
                        and attraction.split()[0][0].isupper()  # Must start with capital letter
                    ):
                        # Add weather-appropriate note
                        weather_note = ""
                        if weather_context == "indoor":
                            if temp > 30:
                                weather_note = " (an air-conditioned venue perfect for hot weather)"
                            else:
                                weather_note = " (a great indoor activity for this weather)"
                        elif weather_context == "outdoor":
                            weather_note = " (perfect weather for outdoor activities)"
                        
                        print(f"✓ Found suitable activity: {attraction}")
                        return f"\n🎯 Suggested Activity: Visit {attraction}{weather_note}"
        
        # If no valid attraction found, try city-specific attractions
        if city in self.CITY_ATTRACTIONS:
            attraction = self.CITY_ATTRACTIONS[city][0]  # Use the first known attraction
            weather_note = " (a popular local attraction)"
            return f"\n🎯 Suggested Activity: Visit {attraction}{weather_note}"
        
        print("❌ Could not find a suitable activity")
        return None 