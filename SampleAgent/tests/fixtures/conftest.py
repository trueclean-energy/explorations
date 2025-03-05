"""
Pytest fixtures for Weather Agent tests.
These fixtures provide mock data and configurations for testing.
"""

import json
import pytest
from pathlib import Path
import responses
import os

# Constants
FIXTURES_DIR = Path(__file__).parent
MOCK_API_KEY = "test_api_key_12345"

@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables for testing"""
    monkeypatch.setenv("WEATHER_API_KEY", MOCK_API_KEY)
    monkeypatch.setenv("BRAVE_API_KEY", MOCK_API_KEY)
    monkeypatch.setenv("TOGETHER_API_KEY", MOCK_API_KEY)
    return monkeypatch

@pytest.fixture
def weather_responses():
    """Load mock weather API responses"""
    with open(FIXTURES_DIR / "weather_responses.json") as f:
        return json.load(f)

@pytest.fixture
def brave_responses():
    """Load mock Brave Search API responses"""
    with open(FIXTURES_DIR / "brave_search_responses.json") as f:
        return json.load(f)

@pytest.fixture
def llm_responses():
    """Mock LLM responses for various operations"""
    return {
        "verify_city": {
            "London": {
                "choices": [{
                    "message": {
                        "content": '{"is_valid": true, "city": "London", "country": "United Kingdom", "alternates": [], "confidence": 0.99, "disambiguation": ""}'
                    }
                }]
            },
            "NonexistentCity123": {
                "choices": [{
                    "message": {
                        "content": '{"is_valid": false, "city": "", "country": "", "alternates": [], "confidence": 0.0, "disambiguation": "This does not appear to be a valid city name."}'
                    }
                }]
            },
            "Cambridge": {
                "choices": [{
                    "message": {
                        "content": '{"is_valid": true, "city": "Cambridge", "country": "United Kingdom", "alternates": ["United States"], "confidence": 0.8, "disambiguation": "Major cities named Cambridge exist in both the UK and USA (Massachusetts)"}'
                    }
                }]
            }
        },
        "suggest_activity": {
            "London": {
                "choices": [{
                    "message": {
                        "content": '{"attraction": "British Museum", "type": "indoor", "reasoning": "Perfect indoor activity for rainy weather", "weather_note": "(a great indoor activity for this rainy weather)"}'
                    }
                }]
            },
            "Dubai": {
                "choices": [{
                    "message": {
                        "content": '{"attraction": "Dubai Mall", "type": "indoor", "reasoning": "Air-conditioned venue ideal for hot weather", "weather_note": "(an air-conditioned venue perfect for hot weather)"}'
                    }
                }]
            },
            "Seattle": {
                "choices": [{
                    "message": {
                        "content": '{"attraction": "Space Needle", "type": "indoor/outdoor", "reasoning": "Iconic landmark with both indoor and outdoor areas", "weather_note": "(offers great views on a clear day)"}'
                    }
                }]
            }
        }
    }

@pytest.fixture
def mock_openweather(weather_responses):
    """Mock OpenWeather API responses"""
    with responses.RequestsMock() as rsps:
        # Success responses for various cities
        for city, data in weather_responses["openweather"]["success"].items():
            rsps.add(
                responses.GET,
                "https://api.openweathermap.org/data/2.5/weather",
                json=data,
                status=200,
                match=[responses.matchers.query_param_matcher({"q": city})]
            )
        
        # Error responses
        # 1. City not found
        rsps.add(
            responses.GET,
            "https://api.openweathermap.org/data/2.5/weather",
            json=weather_responses["openweather"]["errors"]["not_found"],
            status=404,
            match=[responses.matchers.query_param_matcher({"q": "NonexistentCity123"})]
        )
        
        # 2. Rate limit
        rsps.add(
            responses.GET,
            "https://api.openweathermap.org/data/2.5/weather",
            json=weather_responses["openweather"]["errors"]["rate_limit"],
            status=429,
            match=[responses.matchers.query_param_matcher({"q": "RateLimitTest"})]
        )
        
        # 3. Invalid API key
        rsps.add(
            responses.GET,
            "https://api.openweathermap.org/data/2.5/weather",
            json=weather_responses["openweather"]["errors"]["invalid_key"],
            status=401,
            match=[responses.matchers.query_param_matcher({"appid": "invalid_key"})]
        )
        
        yield rsps

@pytest.fixture
def mock_llm_client(llm_responses):
    """Mock LLM client for testing"""
    class MockLLMClient:
        def __init__(self):
            self.responses = llm_responses
            
        def generate(self, prompt, operation="generate"):
            # Simple matching logic for testing
            if operation == "verify_city":
                for city, response in self.responses["verify_city"].items():
                    if city in prompt:
                        return response
                return self.responses["verify_city"]["NonexistentCity123"]
                
            elif operation == "suggest_activity":
                for city, response in self.responses["suggest_activity"].items():
                    if city in prompt:
                        return response
                # Default response
                return self.responses["suggest_activity"]["London"]
            
            # Default empty response
            return {"choices": [{"message": {"content": "{}"}}]}
    
    return MockLLMClient()

@pytest.fixture
def mock_activity_suggester(mock_llm_client):
    """Mock ActivitySuggester for testing"""
    class MockActivitySuggester:
        def __init__(self):
            self.llm = mock_llm_client
            self.city_suggestions = {
                "London": "\n🎯 Suggested Activity: Visit British Museum (a great indoor activity for this rainy weather)",
                "Dubai": "\n🎯 Suggested Activity: Visit Dubai Mall (an air-conditioned venue perfect for hot weather)",
                "Seattle": "\n🎯 Suggested Activity: Visit Space Needle (offers great views on a clear day)",
                "Tokyo": "\n🎯 Suggested Activity: Visit Tokyo Skytree (perfect for clear weather)",
                "New York": "\n🎯 Suggested Activity: Visit Metropolitan Museum of Art (a cozy indoor activity during snow)",
                "Paris": "\n🎯 Suggested Activity: Visit Louvre Museum (a perfect indoor activity for this weather)"
            }
            
        def get_activity_suggestion(self, city, weather):
            # Return predefined suggestion or a generic one
            return self.city_suggestions.get(city, f"\n🎯 Suggested Activity: Visit a local attraction in {city}")
    
    return MockActivitySuggester()

@pytest.fixture
def mock_weatherapi(weather_responses):
    """Mock WeatherAPI.com responses"""
    with responses.RequestsMock() as rsps:
        # Success responses
        for city, data in weather_responses["weatherapi"]["success"].items():
            rsps.add(
                responses.GET,
                f"http://api.weatherapi.com/v1/current.json?key={MOCK_API_KEY}&q={city}",
                json=data,
                status=200
            )
        
        # Error responses
        rsps.add(
            responses.GET,
            f"http://api.weatherapi.com/v1/current.json?key={MOCK_API_KEY}&q=NonexistentCity",
            json=weather_responses["weatherapi"]["errors"]["not_found"],
            status=400
        )
        
        rsps.add(
            responses.GET,
            f"http://api.weatherapi.com/v1/current.json?key={MOCK_API_KEY}&q=RateLimitCity",
            json=weather_responses["weatherapi"]["errors"]["rate_limit"],
            status=429
        )
        
        yield rsps

@pytest.fixture
def mock_brave_search(brave_responses):
    """Mock Brave Search API responses"""
    with responses.RequestsMock() as rsps:
        # Success responses
        base_url = "https://api.search.brave.com/res/v1/web/search"
        
        # Seattle attractions
        rsps.add(
            responses.GET,
            f"{base_url}?q=attractions+in+Seattle&count=3",
            json=brave_responses["success"]["seattle_attractions"],
            status=200
        )
        
        # Dubai indoor activities
        rsps.add(
            responses.GET,
            f"{base_url}?q=indoor+activities+Dubai&count=3",
            json=brave_responses["success"]["dubai_indoor"],
            status=200
        )
        
        # London rainy day activities
        rsps.add(
            responses.GET,
            f"{base_url}?q=indoor+activities+London+rain&count=3",
            json=brave_responses["success"]["london_rainy"],
            status=200
        )
        
        # Error responses
        rsps.add(
            responses.GET,
            f"{base_url}?q=rate_limit_test&count=3",
            json=brave_responses["errors"]["rate_limit"],
            status=429
        )
        
        rsps.add(
            responses.GET,
            f"{base_url}?q=no_results_test&count=3",
            json=brave_responses["errors"]["no_results"],
            status=200
        )
        
        yield rsps

@pytest.fixture
def test_cities():
    """Test cities with expected weather and activities"""
    return {
        "London": {
            "weather": {"temp": 15.5, "conditions": "light rain"},
            "activity": "British Museum"
        },
        "Dubai": {
            "weather": {"temp": 35.2, "conditions": "clear sky"},
            "activity": "Dubai Mall"
        },
        "Seattle": {
            "weather": {"temp": 7.05, "conditions": "scattered clouds"},
            "activity": "Space Needle"
        }
    } 