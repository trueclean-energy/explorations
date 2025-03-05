from abc import ABC, abstractmethod
import os
import requests

class WeatherProvider(ABC):
    """Abstract base class for weather providers"""
    
    @abstractmethod
    def get_current_weather(self, city: str) -> dict:
        """Get current weather for a city
        Returns: dict with 'temp', 'humidity', 'conditions'"""
        pass
        
    @abstractmethod
    def get_forecast(self, city: str, days: int = 5) -> list:
        """Get weather forecast for a city
        Args:
            city: City name
            days: Number of days to forecast (default 5)
        Returns: 
            List of dicts with forecast data for each day
        """
        pass

class OpenWeatherProvider(WeatherProvider):
    """OpenWeather API implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_endpoint = "api.openweathermap.org"
    
    def get_current_weather(self, city: str) -> dict:
        try:
            weather_url = f"https://{self.base_endpoint}/data/2.5/weather"
            params = {
                'appid': self.api_key,
                'q': city,
                'units': 'metric'
            }
            
            response = requests.get(weather_url, params=params)
            if response.status_code != 200:
                print(f"Error from OpenWeather API: {response.status_code} - {response.text}")
                return self._create_error_response()
            
            data = response.json()
            return {
                'temp': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'conditions': data['weather'][0]['description']
            }
        except Exception as e:
            print(f"Error getting weather from OpenWeather: {e}")
            return self._create_error_response()
    
    def _create_error_response(self) -> dict:
        return {
            'temp': 'unknown',
            'humidity': 'unknown',
            'conditions': 'Could not retrieve weather data'
        }

    def get_forecast(self, city: str, days: int = 5) -> list:
        """Get weather forecast for a city using OpenWeather API"""
        try:
            forecast_url = f"https://{self.base_endpoint}/data/2.5/forecast"
            params = {
                'appid': self.api_key,
                'q': city,
                'units': 'metric',
                'cnt': min(days * 8, 40)  # OpenWeather provides 3-hour forecasts, 8 per day, max 5 days
            }
            
            response = requests.get(forecast_url, params=params)
            if response.status_code != 200:
                print(f"Error from OpenWeather API: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            
            # Process the forecast data
            forecasts = []
            current_day = None
            day_data = None
            
            for item in data['list']:
                # Extract date in YYYY-MM-DD format
                date = item['dt_txt'].split(' ')[0]
                
                # Start a new day if needed
                if date != current_day:
                    if day_data:
                        forecasts.append(day_data)
                    
                    current_day = date
                    day_data = {
                        'date': date,  # Ensure date is in YYYY-MM-DD format
                        'min_temp': item['main']['temp_min'],
                        'max_temp': item['main']['temp_max'],
                        'conditions': item['weather'][0]['description'],
                        'humidity': item['main']['humidity']
                    }
                else:
                    # Update min/max for the day
                    day_data['min_temp'] = min(day_data['min_temp'], item['main']['temp_min'])
                    day_data['max_temp'] = max(day_data['max_temp'], item['main']['temp_max'])
            
            # Add the last day if it exists
            if day_data:
                forecasts.append(day_data)
                
            return forecasts[:days]  # Limit to requested number of days
            
        except Exception as e:
            print(f"Error getting forecast from OpenWeather: {e}")
            return []

class WeatherAPIProvider(WeatherProvider):
    """WeatherAPI.com implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_endpoint = "api.weatherapi.com/v1"
    
    def get_current_weather(self, city: str) -> dict:
        try:
            weather_url = f"https://{self.base_endpoint}/current.json"
            params = {
                'key': self.api_key,
                'q': city
            }
            
            response = requests.get(weather_url, params=params)
            if response.status_code != 200:
                print(f"Error from WeatherAPI: {response.status_code} - {response.text}")
                return self._create_error_response()
            
            data = response.json()
            return {
                'temp': data['current']['temp_c'],
                'humidity': data['current']['humidity'],
                'conditions': data['current']['condition']['text']
            }
        except Exception as e:
            print(f"Error getting weather from WeatherAPI: {e}")
            return self._create_error_response()
    
    def _create_error_response(self) -> dict:
        return {
            'temp': 'unknown',
            'humidity': 'unknown',
            'conditions': 'Could not retrieve weather data'
        }

    def get_forecast(self, city: str, days: int = 5) -> list:
        """Get weather forecast for a city using WeatherAPI.com"""
        try:
            forecast_url = f"https://{self.base_endpoint}/forecast.json"
            params = {
                'key': self.api_key,
                'q': city,
                'days': min(days, 10)  # WeatherAPI.com allows up to 10 days forecast
            }
            
            response = requests.get(forecast_url, params=params)
            if response.status_code != 200:
                print(f"Error from WeatherAPI: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            
            # Process the forecast data
            forecasts = []
            for day in data['forecast']['forecastday']:
                # Ensure date is in YYYY-MM-DD format
                date = day['date']  # WeatherAPI already returns in YYYY-MM-DD format
                
                forecasts.append({
                    'date': date,
                    'min_temp': day['day']['mintemp_c'],
                    'max_temp': day['day']['maxtemp_c'],
                    'conditions': day['day']['condition']['text'],
                    'humidity': day['day']['avghumidity']
                })
                
            return forecasts
            
        except Exception as e:
            print(f"Error getting forecast from WeatherAPI: {e}")
            return [] 