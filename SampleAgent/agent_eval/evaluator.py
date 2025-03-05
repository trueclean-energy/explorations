"""
Weather Agent Evaluator

This module provides a comprehensive evaluation framework for the Weather Agent.
It tests various aspects including:
- Accuracy of weather information
- Quality of activity suggestions
- Response time and performance
- Edge case handling
- API usage efficiency
"""

import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class EvaluationMetrics:
    """Stores metrics for a single evaluation run"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_response_time: float = 0.0
    suggestion_quality_score: float = 0.0
    api_calls: int = 0
    rate_limit_hits: int = 0
    error_rate: float = 0.0

@dataclass
class TestCase:
    """Represents a single test case"""
    query: str
    expected: Dict
    weather_data: Optional[Dict] = None
    max_response_time: float = 5.0  # seconds

class WeatherAgentEvaluator:
    """Evaluates the Weather Agent's performance and accuracy"""
    
    def __init__(self, test_cases_path: str = "agent_eval/test_cases.json"):
        self.test_cases = self._load_test_cases(test_cases_path)
        self.metrics = EvaluationMetrics()
        self.results: List[Dict] = []
    
    def _load_test_cases(self, path: str) -> List[TestCase]:
        """Load test cases from JSON file"""
        try:
            with open(path) as f:
                data = json.load(f)
                return [TestCase(**case) for case in data["test_cases"]]
        except Exception as e:
            logger.error(f"Failed to load test cases: {e}")
            return []
    
    def evaluate_suggestion(self, suggestion: str, expected: Dict) -> Tuple[float, List[str]]:
        """
        Evaluate the quality of an activity suggestion
        Returns: (score, reasons)
        """
        if not suggestion:
            return 0.0, ["No suggestion provided"]
        
        score = 0.0
        reasons = []
        
        # Extract the attraction name and weather note
        attraction_match = re.search(r"🎯 Suggested Activity: Visit ([^(]+)(?:\s+\(([^)]+)\))?", suggestion)
        if not attraction_match:
            return 0.1, ["Suggestion format incorrect"]
        
        attraction = attraction_match.group(1).strip()
        weather_note = attraction_match.group(2) if attraction_match.group(2) else ""
        
        # Check for known attractions
        if "known_attractions" in expected:
            for known in expected["known_attractions"]:
                if known.lower() in attraction.lower():
                    score += 0.4
                    reasons.append(f"Matched known attraction: {known}")
                    break
            else:
                # Check if it's a specific attraction (not generic)
                if re.match(r"^[A-Z][a-z']+(?: [A-Z][a-z']+)*$", attraction):
                    score += 0.2
                    reasons.append("Specific attraction name (though not in known list)")
                else:
                    reasons.append("Generic or unknown attraction")
        
        # Check for weather appropriateness in the note
        if "weather_appropriate_terms" in expected and weather_note:
            for term in expected["weather_appropriate_terms"]:
                if term.lower() in weather_note.lower():
                    score += 0.3
                    reasons.append(f"Weather-appropriate term in note: {term}")
                    break
            else:
                # Check if note is contextual to weather
                weather_terms = ["weather", "temperature", "indoor", "outdoor", "hot", "cold", "rain", "snow", "sunny", "warm", "cool"]
                if any(term in weather_note.lower() for term in weather_terms):
                    score += 0.2
                    reasons.append("Weather-contextual note (though not matching expected terms)")
        
        # Check quality of the suggestion
        if len(attraction.split()) >= 2:  # At least two words
            score += 0.1
            reasons.append("Specific multi-word attraction")
        
        if weather_note and len(weather_note) > 10:  # Substantive note
            score += 0.1
            reasons.append("Detailed weather note")
        
        # Penalize bad patterns
        bad_patterns = ["welcome to", "official website", "contact us", "things to do", "attractions in"]
        for pattern in bad_patterns:
            if pattern in attraction.lower():
                score -= 0.2
                reasons.append(f"Contains bad pattern: {pattern}")
        
        return min(1.0, score), reasons
    
    def evaluate_weather_response(self, response: str, expected: Dict) -> Tuple[float, List[str]]:
        """
        Evaluate the quality of a weather response
        Returns: (score, reasons)
        """
        score = 0.0
        reasons = []
        
        # Check for temperature
        if re.search(r"\d+\.?\d*°C", response):
            score += 0.4
            reasons.append("Contains temperature")
        
        # Check for weather conditions
        if re.search(r"(clear|cloudy|rain|snow|storm|overcast)", response.lower()):
            score += 0.3
            reasons.append("Contains weather conditions")
        
        # Check for city name
        if expected.get("city") and expected["city"] in response:
            score += 0.3
            reasons.append("Contains city name")
        
        return min(1.0, score), reasons
    
    def run_evaluation(self, agent) -> Dict:
        """Run the full evaluation suite"""
        start_time = time.time()
        
        for case in self.test_cases:
            self.metrics.total_queries += 1
            try:
                # Time the response
                query_start = time.time()
                response = agent.process_query(case.query)
                query_time = time.time() - query_start
                
                # Evaluate response
                weather_score, weather_reasons = self.evaluate_weather_response(response, case.expected)
                suggestion_score, suggestion_reasons = self.evaluate_suggestion(response, case.expected)
                
                # Track metrics
                if query_time <= case.max_response_time and (weather_score + suggestion_score) / 2 >= 0.7:
                    self.metrics.successful_queries += 1
                else:
                    self.metrics.failed_queries += 1
                
                self.results.append({
                    "query": case.query,
                    "response": response,
                    "response_time": query_time,
                    "weather_score": weather_score,
                    "suggestion_score": suggestion_score,
                    "weather_reasons": weather_reasons,
                    "suggestion_reasons": suggestion_reasons
                })
                
            except Exception as e:
                logger.error(f"Error evaluating case {case.query}: {e}")
                self.metrics.failed_queries += 1
                self.results.append({
                    "query": case.query,
                    "error": str(e)
                })
        
        # Calculate final metrics
        total_time = time.time() - start_time
        self.metrics.avg_response_time = total_time / len(self.test_cases)
        self.metrics.error_rate = self.metrics.failed_queries / self.metrics.total_queries
        self.metrics.suggestion_quality_score = sum(r.get("suggestion_score", 0) for r in self.results) / len(self.results)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate a detailed evaluation report"""
        report = {
            "summary": {
                "total_queries": self.metrics.total_queries,
                "success_rate": (self.metrics.successful_queries / self.metrics.total_queries) * 100,
                "avg_response_time": f"{self.metrics.avg_response_time:.2f}s",
                "suggestion_quality": f"{self.metrics.suggestion_quality_score:.2%}",
                "error_rate": f"{self.metrics.error_rate:.2%}"
            },
            "detailed_results": self.results,
            "recommendations": self._generate_recommendations()
        }
        
        # Save report to file
        report_path = Path("agent_eval/latest_report.json")
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations based on evaluation results"""
        recommendations = []
        
        # Response time recommendations
        slow_responses = [r for r in self.results if r.get("response_time", 0) > 3.0]
        if slow_responses:
            recommendations.append(
                f"Consider optimizing response time for {len(slow_responses)} queries "
                "that took longer than 3 seconds. Consider caching search results or "
                "reducing LLM token usage."
            )
        
        # Quality recommendations
        low_quality = [r for r in self.results if r.get("suggestion_score", 0) < 0.7]
        if low_quality:
            recommendations.append(
                f"Improve suggestion quality for {len(low_quality)} responses "
                "that scored below 70%. Review the LLM prompt in ActivitySuggester "
                "to ensure it extracts specific attractions."
            )
            
            # Analyze specific issues
            generic_issues = sum(1 for r in self.results if "Generic or unknown attraction" in r.get("suggestion_reasons", []))
            if generic_issues > 0:
                recommendations.append(
                    f"Found {generic_issues} generic attraction suggestions. "
                    "Enhance the LLM prompt with more examples of specific attractions."
                )
                
            weather_issues = sum(1 for r in self.results if not any("weather" in reason for reason in r.get("suggestion_reasons", [])))
            if weather_issues > 0:
                recommendations.append(
                    f"Found {weather_issues} suggestions without proper weather context. "
                    "Improve weather-specific reasoning in the LLM prompt."
                )
        
        # Error handling recommendations
        if self.metrics.error_rate > 0.1:
            recommendations.append(
                "High error rate detected. Add better error handling in ActivitySuggester "
                "for LLM parsing failures and search result processing."
            )
            
        # LLM-specific recommendations
        if any("format incorrect" in r.get("suggestion_reasons", []) for r in self.results):
            recommendations.append(
                "LLM response format issues detected. Add stricter JSON validation and "
                "fallback mechanisms when parsing fails."
            )
            
        # Search quality recommendations
        if any("no results" in str(r.get("error", "")).lower() for r in self.results):
            recommendations.append(
                "Search failures detected. Consider adding fallback search queries "
                "and a cache of known attractions for popular cities."
            )
        
        return recommendations

if __name__ == "__main__":
    # Example usage
    from agent import WeatherAgent
    
    evaluator = WeatherAgentEvaluator()
    agent = WeatherAgent()
    report = evaluator.run_evaluation(agent)
    
    print("\nEvaluation Report Summary:")
    print("==========================")
    for metric, value in report["summary"].items():
        print(f"{metric}: {value}")
    
    print("\nTop Recommendations:")
    print("===================")
    for rec in report["recommendations"]:
        print(f"- {rec}")