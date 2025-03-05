import tiktoken
from typing import Dict, Optional
from datetime import datetime

class CostTracker:
    """Tracks token usage and costs for LLM operations"""
    
    def __init__(self, model_name: str, encoding_name: str = "cl100k_base"):
        self.model_name = model_name
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.session_start = datetime.now()
        self.calls = []
        self.total_tokens = {"input": 0, "output": 0}
        self.total_cost = 0.0
        self.last_call_info = None  # Store the most recent call info
        self.operation_stats = {}   # Track stats by operation type
        
        # Cost per 1K tokens (in USD)
        self.COST_PER_1K = {
            "mistralai/Mixtral-8x7B-Instruct-v0.1": {"input": 0.0006, "output": 0.0006},
            "meta-llama/Llama-2-70b-chat": {"input": 0.0009, "output": 0.0009},
            "deepseek/deepseek-r1:free": {"input": 0.0005, "output": 0.0005}  # Estimated cost, adjust as needed
        }
    
    def log_call(self, operation: str, prompt: str, response: str) -> Dict:
        """Log a single LLM call and return usage stats"""
        input_tokens = len(self.encoding.encode(prompt))
        output_tokens = len(self.encoding.encode(response))
        
        # Calculate cost
        model_cost = self.COST_PER_1K.get(self.model_name, {"input": 0.001, "output": 0.001})
        cost = ((input_tokens * model_cost["input"] + 
                output_tokens * model_cost["output"]) / 1000)
        
        # Update totals
        self.total_tokens["input"] += input_tokens
        self.total_tokens["output"] += output_tokens
        self.total_cost += cost
        
        # Update operation-specific stats
        if operation not in self.operation_stats:
            self.operation_stats[operation] = {
                "count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
        
        self.operation_stats[operation]["count"] += 1
        self.operation_stats[operation]["input_tokens"] += input_tokens
        self.operation_stats[operation]["output_tokens"] += output_tokens
        self.operation_stats[operation]["cost"] += cost
        
        # Store call details
        call_info = {
            "timestamp": datetime.now(),
            "operation": operation,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        }
        self.calls.append(call_info)
        self.last_call_info = call_info  # Store the most recent call
        
        return call_info
    
    def print_call_stats(self, call_info: Dict):
        """Print statistics for a single call"""
        print("\nLLM Usage Stats:")
        print(f"→ Operation: {call_info['operation']}")
        print(f"→ Model: {self.model_name}")
        print(f"→ Input tokens: {call_info['input_tokens']}")
        print(f"→ Output tokens: {call_info['output_tokens']}")
        print(f"→ Cost: ${call_info['cost']:.6f}")
        print(f"→ Session total: ${self.total_cost:.6f}\n")
    
    def get_session_summary(self) -> Dict:
        """Get summary of all usage in this session"""
        return {
            "session_start": self.session_start,
            "session_duration": datetime.now() - self.session_start,
            "total_calls": len(self.calls),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "operation_stats": self.operation_stats,
            "calls": self.calls
        }
    
    def print_session_summary(self):
        """Print detailed session summary"""
        summary = self.get_session_summary()
        print("\nLLM Session Summary:")
        print(f"→ Session duration: {summary['session_duration']}")
        print(f"→ Total LLM API calls: {summary['total_calls']}")
        print(f"→ Total tokens: {summary['total_tokens']['input']} in, {summary['total_tokens']['output']} out")
        print(f"→ Total cost: ${summary['total_cost']:.6f}")
        
        # Print operation-specific stats if there are any operations
        if self.operation_stats:
            print("\nBreakdown by operation:")
            for op, stats in sorted(self.operation_stats.items(), key=lambda x: x[1]['count'], reverse=True):
                print(f"  • {op}: {stats['count']} calls, {stats['input_tokens'] + stats['output_tokens']} tokens, ${stats['cost']:.6f}")
    
    def print_detailed_summary(self):
        """Print a very detailed summary with all calls"""
        self.print_session_summary()
        
        print("\nDetailed LLM call history:")
        for i, call in enumerate(self.calls):
            print(f"Call {i+1} - {call['operation']} at {call['timestamp'].strftime('%H:%M:%S')}")
            print(f"  Tokens: {call['input_tokens']} in, {call['output_tokens']} out")
            print(f"  Cost: ${call['cost']:.6f}")
            print("") 