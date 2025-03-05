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
from weather_agent_tools import WeatherAgentToolRegistry

load_dotenv()


class WeatherAgent:
    def __init__(self, weather_provider_name="openweather", llm_model=None):
        # Handle list models request before initializing LLM
        if llm_model == "list":
            print("\nAvailable LLM models:")
            for model, details in LLMClient.MODELS.items():
                print(f"→ {model} (${details['cost']['input']}/1K input tokens)")
            return
            
        # Use Together AI with optional model selection
        self.llm = LLMClient(
            provider="together",
            model=llm_model or os.getenv("TOGETHER_MODEL") or "mistralai/Mixtral-8x7B-Instruct-v0.1"  # Ensure default model
        )
        
        print(f"\nUsing LLM Model: {self.llm.model}")
        
        # Initialize tool registry (which will set up weather provider and other tools)
        os.environ['WEATHER_PROVIDER'] = weather_provider_name
        self.tool_registry = WeatherAgentToolRegistry()
        
        # Keep direct references for backward compatibility
        self.weather_provider = self.tool_registry._get_weather_provider()
        self.brave = BraveSearch(os.getenv('BRAVE_API_KEY'))
        
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
                result = weather_tool.execute(city=city)
                if result['temp'] == 'unknown':
                    print("→ Could not retrieve weather data from API")
                    response = f"I'm sorry, I couldn't get the current weather for {city}."
                else:
                    print(f"→ Successfully retrieved weather data: {result['temp']}°C, {result['conditions']}")
                    response = f"Current weather in {city}: {result['temp']}°C, {result['conditions']}"
                    
                    # Add activity suggestion using tool registry
                    activity_tool = self.tool_registry.get_tool("get_activity_suggestion")
                    if suggestion := activity_tool.execute(city=city, weather=result):
                        response += suggestion
            except Exception as e:
                print(f"Error using weather tool: {e}")
                response = f"I'm sorry, I encountered an error getting weather for {city}."
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
        
        return response
    
    def _detect_intent(self, query):
        # Simple rule-based approach for maximum transparency
        query = query.lower()
        if re.search(r'\b(current|now|today)\b', query):
            return "current"
        if re.search(r'\b(history|last week|past)\b', query):
            return "history"
        
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
        verify_prompt = (
            f"Is '{candidate_city or query}' a valid city name? "
            "First line: Answer ONLY 'yes' or 'no'.\n"
            "Second line: If no, extract the correct city name with proper capitalization.\n"
            "Do not include any other text."
        )
        
        response = self.llm.generate(
            prompt=verify_prompt,
            operation="verify_city"
        )
        
        if response and 'choices' in response:
            answer = response['choices'][0]['message']['content'].strip().split('\n')
            if answer[0].lower() == 'yes' and candidate_city:
                print("✓ Confirmed valid city name")
                return candidate_city
            elif len(answer) > 1:
                extracted = answer[1].strip()
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', extracted):
                    print("✓ Found correct city name")
                    return extracted
        
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
            query = input("\nAsk about the weather (or type 'exit' to quit): ")
            if query.lower() == 'exit':
                # Print final usage statistics
                print("\nFinal Usage Statistics:")
                agent.llm.cost_tracker.print_session_summary()
                break
            print(agent.process_query(query))
        except KeyboardInterrupt:
            print("\nExiting...")
            agent.llm.cost_tracker.print_session_summary()
            break
        except Exception as e:
            print(f"Error: {e}")