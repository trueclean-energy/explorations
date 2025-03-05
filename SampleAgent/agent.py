import os
import re
import requests
import json
# import psycopg2  # Commented out PostgreSQL in favor of SQLite
import sqlite3  # Added for simpler local database
from dotenv import load_dotenv
from llm import LLMClient  # Import the LLM client
from tools.weather_providers import OpenWeatherProvider, WeatherAPIProvider
from tools.brave_search import BraveSearch
from tool_registry import ToolRegistry, Tool, ToolCategory
from tools.activity_suggester import ActivitySuggester
from typing import Optional

load_dotenv()

class WeatherAgentToolRegistry(ToolRegistry):
    def __init__(self):
        super().__init__()
        self._initialize_tools()
    
    def _initialize_tools(self) -> None:
        """Initialize and register all tools"""
        # Initialize service providers
        weather_provider = self._get_weather_provider()
        brave_search = BraveSearch(os.getenv('BRAVE_API_KEY'))
        
        # Initialize LLM client for activity suggester
        llm_client = LLMClient(
            provider=os.getenv("LLM_PROVIDER") or "together",
            model=os.getenv("LLM_MODEL") or "mistralai/Mixtral-8x7B-Instruct-v0.1"
        )
        
        # Initialize activity suggester
        activity_suggester = ActivitySuggester(brave_search, llm_client)
        
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
        
        # Register forecast tool
        self.register_tool(Tool(
            name="get_weather_forecast",
            description="Get weather forecast for a specified city",
            category=ToolCategory.EXTERNAL_API,
            function=weather_provider.get_forecast,
            parameters={
                "city": {
                    "type": "string",
                    "description": "Name of the city to get forecast for"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to forecast (default 5)"
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
            description="Get weather-appropriate activity suggestions for a location using LLM-enhanced search",
            category=ToolCategory.EXTERNAL_API,
            function=activity_suggester.get_activity_suggestion,
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
                },
                "is_forecast": {
                    "type": "boolean",
                    "description": "Whether this is forecast data (future) or current weather"
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

class WeatherAgent:
    def __init__(self, weather_provider_name="openweather", llm_model=None, llm_provider=None):
        # Handle list models request before initializing LLM
        if llm_model == "list":
            print("\nAvailable LLM models:")
            for model, details in LLMClient.MODELS.items():
                print(f"→ {model} (${details['cost']['input']}/1K input tokens)")
            return
            
        # Use specified provider with optional model selection
        self.llm = LLMClient(
            provider=llm_provider or os.getenv("LLM_PROVIDER") or "together",
            model=llm_model or os.getenv("LLM_MODEL") or "mistralai/Mixtral-8x7B-Instruct-v0.1"  # Ensure default model
        )
        
        print(f"\nUsing LLM Model: {self.llm.model} via {self.llm.provider}")
        
        # Initialize tool registry (which will set up weather provider and other tools)
        os.environ['WEATHER_PROVIDER'] = weather_provider_name
        self.tool_registry = WeatherAgentToolRegistry()
        
        # Initialize components
        self.weather_provider = self.tool_registry._get_weather_provider()
        self.brave = BraveSearch(os.getenv('BRAVE_API_KEY'))
        
        # Get the activity suggester from the tool registry
        activity_tool = self.tool_registry.get_tool("get_activity_suggestion")
        self.activity_suggester = activity_tool.function.__self__ if activity_tool else ActivitySuggester(self.brave, self.llm)
        
        # Track API calls that aren't LLM calls
        self.api_calls = {
            "weather": 0,
            "forecast": 0,
            "search": 0,
            "total": 0
        }
        
        self.db = self._init_db()
    
    """
    # PostgreSQL implementation - commented out in favor of simpler SQLite
    def _init_db(self):
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST')
        )
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    query TEXT,
                    response TEXT
                )
            ''')
        return conn
    """
    
    def _init_db(self):
        # SQLite implementation - simpler local database without requiring a server
        db_path = os.path.join(os.path.dirname(__file__), 'weather_agent.db')
        conn = sqlite3.connect(db_path)
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query TEXT,
                    response TEXT
                )
            ''')
        return conn
    
    def process_query(self, query):
        print(f"\nProcessing: {query}")
        print("-----------------------------------")
        
        # 1. Intent detection
        print("\n🤔 Thinking: Understanding what weather information you need...")
        intent = self._detect_intent(query)
        print(f"→ Detected intent: {intent}")
        
        # 2. City extraction
        print("\n🤔 Thinking: Identifying the location you're asking about...")
        city = self._extract_city(query)
        if not city:
            response = "I couldn't understand which city you're asking about. Please specify a city name clearly, like 'weather in San Francisco' or 'Tokyo weather'."
            print("→ Could not identify a valid city name")
            return response
        
        print(f"→ Target location: {city}")
        
        # 3. Execution using tool registry
        print("\nStep 3: Retrieving weather information")
        if intent == "current":
            print(f"→ Fetching current weather for {city}...")
            weather_tool = self.tool_registry.get_tool("get_current_weather")
            try:
                print("🔧 Using tool: get_current_weather")
                result = weather_tool.execute(city=city)
                # Track API call
                self.api_calls["weather"] += 1
                self.api_calls["total"] += 1
                
                if result['temp'] == 'unknown':
                    print("→ Could not retrieve weather data from API")
                    response = f"I'm sorry, I couldn't get the current weather for {city}."
                else:
                    print(f"→ Successfully retrieved weather data: {result['temp']}°C, {result['conditions']}")
                    response = f"Current weather in {city}: {result['temp']}°C, {result['conditions']}"
                    
                    # Use the activity suggester for current weather
                    print("🔧 Using tool: get_activity_suggestion")
                    if suggestion := self.activity_suggester.get_activity_suggestion(city, result, is_forecast=False):
                        response += suggestion
                        # Track search API call (happens inside activity_suggester)
                        self.api_calls["search"] += 1
                        self.api_calls["total"] += 1
                        
                        # Display token usage and cost information for activity suggestion
                        if hasattr(self.llm, 'cost_tracker') and hasattr(self.llm.cost_tracker, 'last_call_info'):
                            last_call = self.llm.cost_tracker.last_call_info
                            input_tokens = last_call.get('input_tokens', 0)
                            output_tokens = last_call.get('output_tokens', 0)
                            cost = last_call.get('cost', 0)
                            print(f"💰 LLM call: {input_tokens + output_tokens} tokens ({input_tokens} input, {output_tokens} output) - Cost: ${cost:.5f}")
            except Exception as e:
                print(f"Error using weather tool: {e}")
                response = f"I'm sorry, I encountered an error getting weather for {city}."
        elif intent == "forecast":
            # Extract time reference from query
            time_reference = re.search(r'\b(tomorrow|next|upcoming|this weekend|next week|future)\b', query.lower())
            time_phrase = time_reference.group(0) if time_reference else "the future"
            
            print(f"→ User requested forecast for {city} for {time_phrase}")
            
            # Determine number of days based on time phrase
            if "weekend" in time_phrase:
                # Calculate days until weekend (Saturday and Sunday)
                from datetime import datetime, timedelta
                today = datetime.now()
                
                # Find the next Saturday (weekday 5)
                days_to_saturday = (5 - today.weekday()) % 7
                if days_to_saturday == 0 and today.hour >= 18:  # If it's Saturday evening, get next weekend
                    days_to_saturday = 7
                
                # Calculate the dates for Saturday and Sunday
                next_saturday = today + timedelta(days=days_to_saturday)
                next_sunday = next_saturday + timedelta(days=1)
                
                # Format dates for display
                saturday_date = next_saturday.strftime('%Y-%m-%d')
                sunday_date = next_sunday.strftime('%Y-%m-%d')
                
                print(f"→ Weekend dates: {saturday_date} (Sat) and {sunday_date} (Sun)")
                
                # Request enough days to include the weekend
                forecast_days = days_to_saturday + 2  # Add 2 to include both Saturday and Sunday
            elif "week" in time_phrase:
                forecast_days = 7
            elif "tomorrow" in time_phrase:
                forecast_days = 1
            else:
                forecast_days = 5  # Default to 5-day forecast
                
            # Get forecast
            forecast_tool = self.tool_registry.get_tool("get_weather_forecast")
            try:
                print("🔧 Using tool: get_weather_forecast")
                forecasts = forecast_tool.execute(city=city, days=forecast_days)
                # Track API call
                self.api_calls["forecast"] += 1
                self.api_calls["total"] += 1
                
                if not forecasts:
                    response = f"I'm sorry, I couldn't get the weather forecast for {city}."
                else:
                    # Format the forecast response based on the time phrase
                    if "weekend" in time_phrase:
                        # Weekend forecast - find the correct dates for Saturday and Sunday
                        weekend_forecasts = []
                        
                        # Debug the forecasts we received
                        print(f"→ Received {len(forecasts)} days of forecast data:")
                        for i, f in enumerate(forecasts):
                            print(f"  Day {i+1}: {f['date']}")
                        
                        # Find the forecasts for Saturday and Sunday by date
                        for forecast in forecasts:
                            if forecast['date'] == saturday_date:
                                weekend_forecasts.append((forecast, "Saturday"))
                            elif forecast['date'] == sunday_date:
                                weekend_forecasts.append((forecast, "Sunday"))
                        
                        # If we couldn't find the exact weekend dates, use the first two days
                        if len(weekend_forecasts) < 2:
                            print("⚠️ Could not find exact weekend dates in forecast data, using available days")
                            if len(weekend_forecasts) == 0 and len(forecasts) >= 2:
                                weekend_forecasts = [(forecasts[0], "Saturday"), (forecasts[1], "Sunday")]
                            elif len(weekend_forecasts) == 0 and len(forecasts) == 1:
                                weekend_forecasts = [(forecasts[0], "Weekend")]
                            elif len(weekend_forecasts) == 1 and len(forecasts) >= 2:
                                # We have one weekend day, add the next day as the other weekend day
                                if weekend_forecasts[0][1] == "Saturday" and len(forecasts) > 1:
                                    for i, f in enumerate(forecasts):
                                        if f['date'] == weekend_forecasts[0][0]['date'] and i+1 < len(forecasts):
                                            weekend_forecasts.append((forecasts[i+1], "Sunday"))
                                            break
                                elif weekend_forecasts[0][1] == "Sunday":
                                    for i, f in enumerate(forecasts):
                                        if f['date'] == weekend_forecasts[0][0]['date'] and i > 0:
                                            weekend_forecasts.insert(0, (forecasts[i-1], "Saturday"))
                                            break
                        
                        response = f"Weather forecast for {city} this weekend:\n\n"
                        for forecast, day_label in weekend_forecasts:
                            response += f"• {forecast['date']} ({day_label}): {forecast['min_temp']}°C to {forecast['max_temp']}°C, {forecast['conditions']}\n"
                    elif "tomorrow" in time_phrase:
                        # Tomorrow's forecast
                        tomorrow = forecasts[0]
                        response = f"Weather forecast for {city} tomorrow ({tomorrow['date']}):\n"
                        response += f"Temperature: {tomorrow['min_temp']}°C to {tomorrow['max_temp']}°C\n"
                        response += f"Conditions: {tomorrow['conditions']}\n"
                        response += f"Humidity: {tomorrow['humidity']}%"
                    else:
                        # Multi-day forecast
                        response = f"Weather forecast for {city} for the next {len(forecasts)} days:\n\n"
                        for day in forecasts:
                            response += f"• {day['date']}: {day['min_temp']}°C to {day['max_temp']}°C, {day['conditions']}\n"
                    
                    # Add activity suggestion for the first day of forecast
                    if forecasts:
                        first_day = forecasts[0]
                        weather_data = {
                            'temp': (first_day['min_temp'] + first_day['max_temp']) / 2,  # Average temp
                            'conditions': first_day['conditions']
                        }
                        print("🔧 Using tool: get_activity_suggestion")
                        if suggestion := self.activity_suggester.get_activity_suggestion(city, weather_data, is_forecast=True):
                            response += f"\n{suggestion}"
                            # Track search API call (happens inside activity_suggester)
                            self.api_calls["search"] += 1
                            self.api_calls["total"] += 1
                            
                            # Display token usage and cost information for activity suggestion
                            if hasattr(self.llm, 'cost_tracker') and hasattr(self.llm.cost_tracker, 'last_call_info'):
                                last_call = self.llm.cost_tracker.last_call_info
                                input_tokens = last_call.get('input_tokens', 0)
                                output_tokens = last_call.get('output_tokens', 0)
                                cost = last_call.get('cost', 0)
                                print(f"💰 LLM call: {input_tokens + output_tokens} tokens ({input_tokens} input, {output_tokens} output) - Cost: ${cost:.5f}")
            except Exception as e:
                print(f"Error using forecast tool: {e}")
                response = f"I'm sorry, I encountered an error getting the forecast for {city}."
        elif intent == "history":
            print("→ Historical weather functionality is not implemented yet")
            response = f"I'm sorry, I don't have access to historical weather data for {city} yet."
        else:
            response = "I can help with current weather information. Please specify a location."
        
        print("\nStep 4: Saving this interaction to the database")
        # 4. Logging to SQLite
        with self.db:
            self.db.execute('''
                INSERT INTO interactions (query, response)
                VALUES (?, ?)
            ''', (query, response))
        print("→ Interaction saved")
        print("-----------------------------------")
        
        # Display session summary after each query
        print("\nCurrent Session Summary:")
        self.llm.cost_tracker.print_session_summary()
        
        # Display API call summary
        print("\nAPI Call Summary:")
        print(f"→ Weather API calls: {self.api_calls['weather']}")
        print(f"→ Forecast API calls: {self.api_calls['forecast']}")
        print(f"→ Search API calls: {self.api_calls['search']}")
        print(f"→ Total API calls: {self.api_calls['total'] + self.llm.cost_tracker.get_session_summary()['total_calls']}")
        
        return response
    
    def _detect_intent(self, query):
        # Simple rule-based approach for maximum transparency
        query = query.lower()
        if re.search(r'\b(current|now|today)\b', query):
            return "current"
        if re.search(r'\b(history|last week|past)\b', query):
            return "history"
        if re.search(r'\b(forecast|tomorrow|next|upcoming|this weekend|next week|future)\b', query):
            return "forecast"
        
        # Default to current for simplicity - most weather queries are about current weather
        print("No specific time reference found, defaulting to current weather")
        return "current"
    
    def _extract_city(self, query):
        """Extract city name from query with better accuracy"""
        # First try pattern matching
        patterns = [
            r'\b(?:in|at|for|near|around)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)(?:\s+(?:weather|temperature|forecast))',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*[A-Z]{2}\b'
        ]
        
        candidate_city = None
        for pattern in patterns:
            if match := re.search(pattern, query, re.I):
                candidate_city = ' '.join(word.capitalize() for word in match.group(1).split())
                break
        
        # Always verify with LLM
        print("\n🤔 Thinking: Verifying if this is a valid city name...")
        print("🧠 Using language model API for city verification")
        verify_prompt = (
            f"Analyze the location '{candidate_city or query}' and provide information in the following JSON format:\n"
            "{\n"
            '  "is_valid": true/false,\n'
            '  "city": "Correct city name with proper capitalization",\n'
            '  "country": "Primary country where this city is located",\n'
            '  "alternates": ["Country1", "Country2"],  // If same city name exists in multiple countries\n'
            '  "confidence": 0.0-1.0,  // How confident in this identification\n'
            '  "disambiguation": "Additional context if needed"\n'
            "}\n\n"
            "Example response:\n"
            "{\n"
            '  "is_valid": true,\n'
            '  "city": "Cambridge",\n'
            '  "country": "United Kingdom",\n'
            '  "alternates": ["United States"],\n'
            '  "confidence": 0.9,\n'
            '  "disambiguation": "Major cities named Cambridge exist in both the UK and USA (Massachusetts)"\n'
            "}\n\n"
            "Provide only the JSON response, no additional text."
        )
        
        response = self.llm.generate(
            prompt=verify_prompt,
            operation="verify_city"
        )
        
        # Display token usage and cost information
        if hasattr(self.llm, 'cost_tracker') and hasattr(self.llm.cost_tracker, 'last_call_info'):
            last_call = self.llm.cost_tracker.last_call_info
            input_tokens = last_call.get('input_tokens', 0)
            output_tokens = last_call.get('output_tokens', 0)
            cost = last_call.get('cost', 0)
            print(f"💰 LLM call: {input_tokens + output_tokens} tokens ({input_tokens} input, {output_tokens} output) - Cost: ${cost:.5f}")
        
        if response and 'choices' in response:
            try:
                result = json.loads(response['choices'][0]['message']['content'].strip())
                
                # Handle valid city with high confidence
                if result.get('is_valid') and result.get('confidence', 0) > 0.7:
                    city_name = result['city']
                    
                    # Print geographic context
                    print(f"✓ Verified city: {city_name}, {result['country']}")
                    if result.get('alternates'):
                        print(f"  Note: Also exists in {', '.join(result['alternates'])}")
                    if result.get('disambiguation'):
                        print(f"  Context: {result['disambiguation']}")
                    
                    return city_name
                
                # Handle ambiguous cases
                elif result.get('is_valid') and result.get('alternates'):
                    print(f"⚠️  Ambiguous city name: {result['city']}")
                    print(f"  Found in: {result['country']} and {', '.join(result['alternates'])}")
                    # For now, return the primary country's city
                    # TODO: Could be enhanced to ask user for clarification
                    return result['city']
                
                # Handle invalid cities
                else:
                    print("❌ Invalid or unknown city name")
                    if result.get('disambiguation'):
                        print(f"  Note: {result['disambiguation']}")
                    return None
                    
            except json.JSONDecodeError:
                print("❌ Could not parse city validation response")
                return None
        
        print("❌ Could not verify city name")
        return None

if __name__ == "__main__":
    import sys
    
    # Show available models if requested
    if "--list-models" in sys.argv:
        WeatherAgent(llm_model="list")
        sys.exit(0)
    
    # Show available tools if requested
    if "--list-tools" in sys.argv:
        agent = WeatherAgent()
        print("\nAvailable Tools:")
        print("===============")
        for tool in agent.tool_registry.list_tools():
            print(f"\n→ {tool['name']}")
            print(f"  Description: {tool['description']}")
            print(f"  Category: {tool['category']}")
            print("  Parameters:")
            for param_name, param_info in tool['parameters'].items():
                required = "required" if param_name in tool['required_params'] else "optional"
                print(f"    - {param_name} ({required}): {param_info['description']}")
        sys.exit(0)
    
    # Get model from environment or use default
    model = os.getenv("TOGETHER_MODEL")
    agent = WeatherAgent(llm_model=model)
    
    print("\nWeather Agent Ready!")
    print("Type 'exit' to quit, or ask about the weather.")
    print("Example: 'What's the weather in Tokyo?'")
    
    while True:
        try:
            query = input("\nAsk about the weather (or type 'exit' to quit): ").strip()
            
            # Check for exit command first
            if query.lower() == 'exit':
                print("\nFinal Usage Statistics:")
                agent.llm.cost_tracker.print_detailed_summary()
                print("\nThank you for using the Weather Agent! Goodbye.")
                break
            
            # Only process non-empty queries
            if query:
                response = agent.process_query(query)
                print(response)
        
        except KeyboardInterrupt:
            print("\nExiting...")
            print("\nFinal Usage Statistics:")
            agent.llm.cost_tracker.print_detailed_summary()
            break
        except Exception as e:
            print(f"Error: {e}")