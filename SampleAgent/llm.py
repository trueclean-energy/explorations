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
    
    def __init__(self, provider="together", model=None):
        self.provider = provider
        self.api_key = os.getenv(f"{provider.upper()}_API_KEY")
        self.model = model or "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.encoding = tiktoken.get_encoding(self.MODELS[self.model]["encoding"])
        self.cost_tracker = CostTracker(self.model)
    
    def generate(self, prompt: str, operation: str = "generate") -> Dict:
        """Generate response with token tracking"""
        # Count input tokens
        input_tokens = len(self.encoding.encode(prompt))
        
        # Make API call
        response = self._generate_together(prompt)
        
        # Track usage if response is valid
        if response and 'choices' in response:
            output_text = response['choices'][0]['message']['content']
            call_info = self.cost_tracker.log_call(operation, prompt, output_text)
            self.cost_tracker.print_call_stats(call_info)
        
        return response
    
    def _generate_together(self, prompt: str) -> Dict:
        """Make API call to Together AI"""
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 512
            }
        )
        return response.json()
    
    @property
    def total_cost(self):
        return self.cost_tracker.total_cost