# llm.py
import os
import requests
import json
import tiktoken
from typing import Dict, Optional
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
        "generate": {
            "temperature": 0.7,  # Default for general responses
            "max_tokens": 512,   # Standard length
            "description": "Default settings for general operations"
        }
    }
    
    def __init__(self, provider="together", model=None):
        self.provider = provider
        self.api_key = os.getenv(f"{provider.upper()}_API_KEY")
        self.model = model or "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.encoding = tiktoken.get_encoding(self.MODELS[self.model]["encoding"])
        self.cost_tracker = CostTracker(self.model)
    
    def generate(self, prompt: str, operation: str = "generate") -> Dict:
        """Generate response with token tracking and operation-specific settings"""
        # Count input tokens
        input_tokens = len(self.encoding.encode(prompt))
        
        # Get operation-specific settings or defaults
        settings = self.OPERATION_SETTINGS.get(operation, self.OPERATION_SETTINGS["generate"])
        
        # Make API call with optimized settings
        response = self._generate_together(prompt, settings)
        
        # Track usage if response is valid
        if response and 'choices' in response:
            output_text = response['choices'][0]['message']['content']
            call_info = self.cost_tracker.log_call(operation, prompt, output_text)
            
            # Only print detailed stats in verbose mode
            if os.getenv("VERBOSE_LLM", "0") == "1":
                self.cost_tracker.print_call_stats(call_info)
        
        return response
    
    def _generate_together(self, prompt: str, settings: Dict) -> Dict:
        """Make API call to Together AI with operation-specific settings"""
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": settings["temperature"],
                "max_tokens": settings["max_tokens"]
            }
        )
        return response.json()
    
    @property
    def total_cost(self):
        return self.cost_tracker.total_cost