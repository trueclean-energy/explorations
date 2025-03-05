# llm.py
import os
import requests
import json
import tiktoken
from typing import Dict, Optional, Callable
from cost_tracker import CostTracker

class LLMClient:
    """Simple LLM client with token tracking using tiktoken"""
    
    # Default models and their costs per 1K tokens (in USD)
    MODELS = {
        "mistralai/Mixtral-8x7B-Instruct-v0.1": {
            "encoding": "cl100k_base",  # Same as GPT-4
            "cost": {"input": 0.0006, "output": 0.0006}
        },
        "meta-llama/Llama-2-70b-chat": {
            "encoding": "cl100k_base",
            "cost": {"input": 0.0009, "output": 0.0009}
        },
        "deepseek/deepseek-r1:free": {
            "encoding": "cl100k_base",
            "cost": {"input": 0.0005, "output": 0.0005},  # Estimated cost, adjust as needed
            "has_reasoning": True  # Flag to indicate this model provides reasoning
        }
    }
    
    # Provider-specific configurations
    PROVIDERS = {
        "together": {
            "api_url": "https://api.together.xyz/v1/chat/completions",
            "api_key_env": "TOGETHER_API_KEY",
            "handler": "_generate_together",
            "timeout": 30  # 30 seconds timeout
        },
        "openrouter": {
            "api_url": "https://openrouter.ai/api/v1/chat/completions",
            "api_key_env": "OPENROUTER_API_KEY",
            "handler": "_generate_openrouter",
            "timeout": 60  # 60 seconds timeout for OpenRouter
        }
    }
    
    # Operation-specific settings for optimal performance
    OPERATION_SETTINGS = {
        "verify_city": {
            "temperature": 0.1,  # Low temperature for factual city validation
            "max_tokens": 100,   # Short responses needed
            "description": "City name validation requires high precision"
        },
        "extract_city": {
            "temperature": 0.3,  # Slightly higher for name extraction
            "max_tokens": 150,   # Moderate length for extraction with context
            "description": "City name extraction from context needs some creativity"
        },
        "suggest_activity": {
            "temperature": 0.2,  # Low temperature for factual suggestions
            "max_tokens": 250,   # Longer response for JSON with reasoning
            "description": "Activity suggestions need to be specific and weather-appropriate"
        },
        "search_terms": {
            "temperature": 0.3,  # Low temperature for focused search terms
            "max_tokens": 50,    # Very short response needed
            "description": "Generate weather-appropriate search terms"
        },
        "generate": {
            "temperature": 0.7,  # Default for general responses
            "max_tokens": 512,   # Standard length
            "description": "Default settings for general operations"
        }
    }
    
    def __init__(self, provider="together", model=None):
        if provider not in self.PROVIDERS:
            raise ValueError(f"Provider '{provider}' not supported. Available providers: {list(self.PROVIDERS.keys())}")
            
        self.provider = provider
        provider_config = self.PROVIDERS[provider]
        self.api_key = os.getenv(provider_config["api_key_env"])
        
        if not self.api_key:
            raise ValueError(f"API key not found. Please set the {provider_config['api_key_env']} environment variable.")
        
        # Set default model based on provider if not specified
        if model is None:
            if provider == "openrouter":
                model = "deepseek/deepseek-r1:free"
            else:
                model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
                
        self.model = model
        
        # Ensure the model is in our MODELS dictionary
        if self.model not in self.MODELS:
            # Use a default encoding and cost if model not found
            self.encoding = tiktoken.get_encoding("cl100k_base")
            print(f"Warning: Model '{self.model}' not found in MODELS dictionary. Using default encoding and cost.")
            self.model_config = {"encoding": "cl100k_base", "cost": {"input": 0.001, "output": 0.001}, "has_reasoning": False}
        else:
            self.encoding = tiktoken.get_encoding(self.MODELS[self.model]["encoding"])
            self.model_config = self.MODELS[self.model]
            
        self.cost_tracker = CostTracker(self.model)
        
        # Set the handler method based on provider
        self.handler_name = provider_config["handler"]
        self.api_url = provider_config["api_url"]
        self.timeout = provider_config.get("timeout", 30)  # Default timeout of 30 seconds
    
    def generate(self, prompt: str, operation: str = "generate") -> Dict:
        """Generate response with token tracking and operation-specific settings"""
        # Count input tokens
        input_tokens = len(self.encoding.encode(prompt))
        
        # Get operation-specific settings or defaults
        settings = self.OPERATION_SETTINGS.get(operation, self.OPERATION_SETTINGS["generate"])
        
        try:
            # Make API call with optimized settings using the appropriate handler
            handler = getattr(self, self.handler_name)
            response = handler(prompt, settings)
            
            # Track usage if response is valid
            if response and 'choices' in response:
                # For models with reasoning, use reasoning as content if content is empty
                if self.model_config.get("has_reasoning", False) and 'choices' in response:
                    choice = response['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        content = choice['message']['content']
                        # If content is empty but reasoning exists, use reasoning as content
                        if not content and 'reasoning' in choice['message'] and choice['message']['reasoning']:
                            # Extract a concise answer from the reasoning if possible
                            reasoning = choice['message']['reasoning']
                            # Keep the original reasoning for reference
                            choice['message']['original_reasoning'] = reasoning
                            # Use reasoning as content if content is empty
                            choice['message']['content'] = f"Based on my reasoning: {reasoning}"
                
                # Get the content for token counting
                output_text = response['choices'][0]['message']['content']
                call_info = self.cost_tracker.log_call(operation, prompt, output_text)
                
                # Only print detailed stats in verbose mode
                if os.getenv("VERBOSE_LLM", "0") == "1":
                    self.cost_tracker.print_call_stats(call_info)
            
            return response
        except requests.exceptions.Timeout:
            print(f"Request to {self.provider} timed out after {self.timeout} seconds.")
            return {"error": "timeout", "message": f"Request timed out after {self.timeout} seconds."}
        except Exception as e:
            print(f"Error making request to {self.provider}: {str(e)}")
            return {"error": "request_failed", "message": str(e)}
    
    def _generate_together(self, prompt: str, settings: Dict) -> Dict:
        """Make API call to Together AI with operation-specific settings"""
        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": settings["temperature"],
                "max_tokens": settings["max_tokens"]
            },
            timeout=self.timeout
        )
        return response.json()
    
    def _generate_openrouter(self, prompt: str, settings: Dict) -> Dict:
        """Make API call to OpenRouter with operation-specific settings"""
        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost:8000"),  # Required by OpenRouter
                "X-Title": os.getenv("OPENROUTER_TITLE", "SampleAgent")  # Optional but recommended
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": settings["temperature"],
                "max_tokens": settings["max_tokens"]
            },
            timeout=self.timeout
        )
        return response.json()
    
    @property
    def total_cost(self):
        return self.cost_tracker.total_cost