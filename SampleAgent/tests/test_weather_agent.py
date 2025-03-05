"""
Unit and Integration Tests for Weather Agent
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import responses
import os

from tools.brave_search import BraveSearch
from tools.weather_providers import WeatherProvider, OpenWeatherProvider, WeatherAPIProvider
from tools.activity_suggester import ActivitySuggester
from agent import WeatherAgent

# Load test cases
TEST_CASES_PATH = Path(__file__).parent / "test_cases_weather.json"
with open(TEST_CASES_PATH) as f:
    TEST_CASES = json.load(f)

class TestWeatherProvider:
    """Test suite for weather providers"""
    
    @pytest.fixture
    def mock_weather_api(self):
        """Mock weather API responses"""
        with responses.RequestsMock() as rsps:
            # OpenWeather API mock
            rsps.add(
                responses.GET,
                "https://api.openweathermap.org/data/2.5/weather",
                json={
                    "main": {"temp": 20.5, "humidity": 65},
                    "weather": [{"description": "clear sky"}]
                },
                status=200
            )
            # WeatherAPI mock
            rsps.add(
                responses.GET,
                "https://api.weatherapi.com/v1/current.json",
                json={
                    "current": {
                        "temp_c": 20.5,
                        "humidity": 65,
                        "condition": {"text": "Clear"}
                    }
                },
                status=200
            )
            yield rsps
    
    def test_openweather_provider(self, mock_weather_api):
        """Test OpenWeather provider"""
        provider = OpenWeatherProvider("test_key")
        result = provider.get_current_weather("London")
        assert result["temp"] == 20.5
        assert "clear" in result["conditions"].lower()
    
    def test_weatherapi_provider(self, mock_weather_api):
        """Test WeatherAPI provider"""
        provider = WeatherAPIProvider("test_key")
        result = provider.get_current_weather("London")
        assert result["temp"] == 20.5
        assert "clear" in result["conditions"].lower()
    
    def test_provider_error_handling(self):
        """Test error handling in providers"""
        provider = OpenWeatherProvider("")
        result = provider.get_current_weather("NonexistentCity")
        assert result["temp"] == "unknown"
        assert "could not retrieve" in result["conditions"].lower()

class TestBraveSearch:
    """Test suite for Brave Search functionality"""
    
    @pytest.fixture
    def brave_search(self):
        return BraveSearch("test_key")
    
    @pytest.fixture
    def mock_brave_api(self):
        """Mock Brave Search API responses"""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.search.brave.com/res/v1/web/search",
                json={
                    "web": {
                        "results": [
                            {
                                "title": "Space Needle",
                                "description": "The Space Needle is Seattle's most iconic landmark..."
                            }
                        ]
                    }
                },
                status=200
            )
            yield rsps
    
    def test_search_validation(self, brave_search):
        """Test input validation"""
        assert brave_search.search("") is None
        assert brave_search.search(" " * 5) is None
    
    def test_suggestion_validation(self, brave_search):
        """Test suggestion validation"""
        assert brave_search.validate_suggestion("", "Seattle") is False
        assert brave_search.validate_suggestion("Space Needle", "Seattle") is True
        assert brave_search.validate_suggestion("Random Museum", "Unknown City") is True
    
    def test_activity_suggestion(self, brave_search, mock_brave_api):
        """Test activity suggestion logic"""
        weather = {"temp": 25, "conditions": "clear"}
        suggestion = brave_search.get_activity_suggestion("Seattle", weather)
        assert suggestion is not None
        assert "Space Needle" in suggestion
        assert "Visit" in suggestion

class TestActivitySuggester:
    """Test suite for ActivitySuggester"""
    
    @pytest.fixture
    def activity_suggester(self):
        """Create activity suggester with mocked dependencies"""
        brave_search = Mock()
        llm_client = Mock()
        return ActivitySuggester(brave_search, llm_client)
    
    def test_activity_suggestion(self, activity_suggester):
        """Test activity suggestion with LLM coordination"""
        # Mock the search result
        activity_suggester.brave_search.search.return_value = "Seattle is known for the Space Needle, Pike Place Market, and the Museum of Pop Culture."
        
        # Mock the LLM response
        activity_suggester.llm.generate.return_value = {
            'choices': [{
                'message': {
                    'content': '{"attraction": "Space Needle", "type": "indoor/outdoor", "reasoning": "Iconic landmark with indoor and outdoor areas", "weather_note": "(perfect for clear weather)"}'
                }
            }]
        }
        
        # Test the suggestion
        weather = {"temp": 20, "conditions": "clear"}
        suggestion = activity_suggester.get_activity_suggestion("Seattle", weather)
        
        # Verify results
        assert suggestion is not None
        assert "Space Needle" in suggestion
        assert "perfect for clear weather" in suggestion
        
        # Verify the LLM was called with appropriate parameters
        activity_suggester.llm.generate.assert_called_once()
        args, kwargs = activity_suggester.llm.generate.call_args
        assert kwargs["operation"] == "suggest_activity"
        assert "Seattle" in kwargs["prompt"]
        assert "20" in kwargs["prompt"]
        assert "clear" in kwargs["prompt"]

class TestWeatherAgent:
    """Test suite for Weather Agent"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance with mocked dependencies"""
        with patch('agent.LLMClient'):
            return WeatherAgent()
    
    @pytest.fixture
    def mock_tools(self, agent):
        """Mock all external tool calls"""
        agent.weather_provider.get_current_weather = Mock(
            return_value={"temp": 20, "conditions": "clear"}
        )
        agent.activity_suggester.get_activity_suggestion = Mock(
            return_value="\n🎯 Suggested Activity: Visit Space Needle (perfect for clear weather)"
        )
        return agent
    
    def test_process_query(self, mock_tools):
        """Test query processing"""
        response = mock_tools.process_query("What's the weather in Seattle?")
        assert "Seattle" in response
        assert "20°C" in response
        assert "Space Needle" in response
    
    def test_error_handling(self, mock_tools):
        """Test error handling"""
        mock_tools.weather_provider.get_current_weather.return_value = {
            "temp": "unknown",
            "conditions": "Could not retrieve weather data"
        }
        response = mock_tools.process_query("Weather in NonexistentCity")
        assert "couldn't get" in response.lower()
    
    @pytest.mark.parametrize("test_case", TEST_CASES["test_cases"])
    def test_integration(self, agent, test_case):
        """Integration tests using test cases"""
        query = test_case["query"]
        expected = test_case["expected"]
        
        if expected.get("error"):
            # Test error cases
            response = agent.process_query(query)
            assert any(msg.lower() in response.lower() 
                      for msg in ["couldn't get", "couldn't understand", "error"])
        else:
            # Test successful cases
            response = agent.process_query(query)
            assert expected["city"] in response
            if "known_attractions" in expected:
                assert any(attr in response for attr in expected["known_attractions"])

def test_end_to_end():
    """End-to-end test with real API calls"""
    if not os.getenv("WEATHER_API_KEY") or not os.getenv("BRAVE_API_KEY"):
        pytest.skip("API keys not available for end-to-end test")
    
    agent = WeatherAgent()
    response = agent.process_query("What's the weather in London?")
    
    assert "London" in response
    assert "°C" in response
    assert "🎯 Suggested Activity:" in response

if __name__ == "__main__":
    pytest.main([__file__, "-v"])