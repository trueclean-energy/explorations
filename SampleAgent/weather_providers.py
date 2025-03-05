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