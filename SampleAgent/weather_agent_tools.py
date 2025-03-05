from tool_registry import ToolRegistry, Tool, ToolCategory
from tools.weather_providers import OpenWeatherProvider, WeatherAPIProvider
from tools.brave_search import BraveSearch
import os
from typing import Optional

class WeatherAgentToolRegistry(ToolRegistry):
    def __init__(self):
        super().__init__()
        self._initialize_tools()
    
    def _initialize_tools(self) -> None:
        """Initialize and register all tools"""
        # Initialize service providers
        weather_provider = self._get_weather_provider()
        brave_search = BraveSearch(os.getenv('BRAVE_API_KEY'))
        
        # Register weather tool
        self.register_tool(Tool(
            name="get_current_weather",
            description="Get current weather conditions for a specified city",
            category=ToolCategory.EXTERNAL_API,
            function=weather_provider.get_current_weather,
            parameters={
                "city": {
                    "type": "string",
                    "description": "Name of the city to get weather for"
                }
            },
            required_params=["city"]
        ))
        
        # Register Brave Search tools
        self.register_tool(Tool(
            name="web_search",
            description="Perform a web search using Brave Search API",
            category=ToolCategory.EXTERNAL_API,
            function=brave_search.search,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query to execute"
                }
            },
            required_params=["query"]
        ))
        
        self.register_tool(Tool(
            name="get_activity_suggestion",
            description="Get weather-appropriate activity suggestions for a location",
            category=ToolCategory.EXTERNAL_API,
            function=brave_search.get_activity_suggestion,
            parameters={
                "city": {
                    "type": "string",
                    "description": "City to get activity suggestions for"
                },
                "weather": {
                    "type": "dict",
                    "description": "Current weather conditions",
                    "schema": {
                        "temp": "number",
                        "conditions": "string"
                    }
                }
            },
            required_params=["city", "weather"]
        ))
    
    def _get_weather_provider(self):
        """Initialize the appropriate weather provider based on configuration"""
        provider_name = os.getenv('WEATHER_PROVIDER', 'openweather')
        api_key = os.getenv('WEATHER_API_KEY')
        
        if not api_key:
            raise ValueError("WEATHER_API_KEY environment variable is required")
        
        if provider_name == 'openweather':
            return OpenWeatherProvider(api_key)
        elif provider_name == 'weatherapi':
            return WeatherAPIProvider(api_key)
        else:
            raise ValueError(f"Unsupported weather provider: {provider_name}") 