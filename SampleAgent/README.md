# Weather Agent

A sophisticated weather agent that provides weather information and suggests weather-appropriate activities for any city worldwide. The agent uses weather APIs for current conditions and Brave Search to intelligently suggest relevant activities based on the weather.

## Quick Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:
```
WEATHER_API_KEY=your_openweather_or_weatherapi_key
BRAVE_API_KEY=your_brave_search_key
LLM_PROVIDER=together  # or openrouter
LLM_MODEL=mistralai/Mixtral-8x7B-Instruct-v0.1  # or another supported model
TOGETHER_API_KEY=your_together_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## Usage

Start the agent:
```bash
python agent.py
```

You can then ask about weather and get activity suggestions for any city, for example:
- "What's the weather in Tokyo?"
- "How's the weather in Paris?"
- "Weather in Cape Town?"

Additional commands:
```bash
# List available LLM models
python agent.py --list-models

# List available tools
python agent.py --list-tools

# Run with verbose LLM logging
VERBOSE_LLM=1 python agent.py

# Specify LLM provider and model
python agent.py --provider openrouter --model deepseek/deepseek-r1:free
```

## LLM Client

The agent uses a flexible LLM client that supports multiple providers and models. You can easily switch between providers and models by modifying the configuration.

### Supported Providers

- **Together AI**: Default provider with models like Mixtral and Llama 2
- **OpenRouter**: Alternative provider with models like DeepSeek R1

### Switching Providers and Models

You can switch providers and models in your code:

```python
from llm import LLMClient

# Use Together AI with Mixtral (default)
llm = LLMClient()

# Use Together AI with Llama 2
llm = LLMClient(provider="together", model="meta-llama/Llama-2-70b-chat")

# Use OpenRouter with DeepSeek R1
llm = LLMClient(provider="openrouter", model="deepseek/deepseek-r1:free")
```

### Example Usage

Try the example script to see how to use different providers and models:

```bash
# Use default provider (Together) and model (Mixtral)
python example_llm.py

# Use Together AI with default model
python example_llm.py together

# Use Together AI with Llama 2 model
python example_llm.py together meta-llama/Llama-2-70b-chat

# Use OpenRouter with default model (DeepSeek R1)
python example_llm.py openrouter

# Use OpenRouter with DeepSeek R1 model
python example_llm.py openrouter deepseek/deepseek-r1:free
```

## LLM-Enhanced Search

The agent uses a sophisticated approach to generate weather-appropriate activity suggestions:

1. **Weather Analysis**: The agent analyzes current weather conditions (temperature and conditions).

2. **LLM-Generated Search Terms**: The LLM generates specific search terms based on the weather conditions.
   - For rainy weather: "indoor museum gallery theater"
   - For hot weather: "air-conditioned indoor aquarium mall"
   - For cold weather: "indoor warm cozy museum"
   - For pleasant weather: "outdoor park garden walking"

3. **Enhanced Search Query**: These terms are combined with the city name to create a targeted search query.

4. **Activity Suggestion**: The LLM analyzes both the weather conditions and search results to suggest a specific activity.

This approach provides more contextually relevant and weather-appropriate suggestions than traditional rule-based methods.

### Operation Settings

The LLM client uses operation-specific settings for optimal performance:

```python
OPERATION_SETTINGS = {
    "verify_city": {
        "temperature": 0.1,  # Low temperature for factual city validation
        "max_tokens": 100    # Short responses needed
    },
    "search_terms": {
        "temperature": 0.3,  # Low temperature for focused search terms
        "max_tokens": 50     # Very short response needed
    },
    "suggest_activity": {
        "temperature": 0.2,  # Low temperature for factual suggestions
        "max_tokens": 250    # Longer response for detailed suggestions
    }
}
```

## Project Structure

```
SampleAgent/
├── agent_eval/            # Agent evaluation files
├── scripts/               # Utility scripts
├── tests/                 # Test files and fixtures
├── tools/                 # API implementations
├── .github/               # GitHub configuration files
├── agent.py              # Main agent implementation
├── cost_tracker.py       # Token usage and cost tracking
├── llm.py               # LLM client implementation
├── tool_registry.py     # Tool registration and management
├── example_llm.py       # Example of using the LLM client
├── weather_agent.db     # SQLite database for interactions
├── requirements.txt     # Dependencies
├── .env                 # API keys (create this)
└── .gitignore          # Git ignore configuration
```

## Features

- Real-time weather information for any city worldwide
- Context-aware activity suggestions based on current weather
- Intelligent handling of different weather conditions
- Rate limit handling and error recovery
- Automated testing and evaluation framework
- Transparent LLM usage with token counts and cost tracking
- Support for multiple LLM providers and models

## Troubleshooting

- If you get API errors, verify your API keys in `.env`
- For rate limit errors, wait a few minutes and try again
- For model errors, try using a different model with `--list-models`

## Token Usage and Cost Tracking

The agent provides transparent information about LLM usage:

- Each LLM call shows token usage and cost: `💰 LLM call: 350 tokens (300 input, 50 output) - Cost: $0.00021`
- The thinking process is indicated with: `🤔 Thinking: Analyzing weather conditions...`
- Final usage statistics are shown when exiting the agent
- Set `VERBOSE_LLM=1` for more detailed logging

## License

MIT License - See LICENSE file for details

## Development and Testing

### 1. Testing Framework

#### Quick Test Commands
```bash
# Run all tests
python scripts/run_tests.py --all

# Run specific types of tests
python scripts/run_tests.py --unit          # Unit tests only
python scripts/run_tests.py --integration   # Integration tests only
python scripts/run_tests.py --unit -v       # Verbose output
```

#### Advanced Testing Options
```bash
# Coverage reports
python scripts/run_tests.py --unit --coverage
coverage run -m pytest
coverage report

# Test discovery
python scripts/run_tests.py --list-tests
python scripts/run_tests.py --list-strategies

# Run specific tests
pytest tests/test_weather_agent.py
python scripts/run_tests.py --unit --pattern "test_activity_suggestion"
```

### 2. Quality Assurance

#### Running the Evaluator
```bash
python -m agent_eval.evaluator
```

#### What Gets Evaluated
- Response quality and specificity
- Weather data accuracy
- Activity suggestion relevance
- Response times and error rates

#### Quality Criteria Examples
- **Specificity**: "Taj Mahal" instead of generic "museum" for Agra
- **Weather Awareness**: Indoor activities during rain in London
- **Context**: Air-conditioned venues like "Dubai Mall" during hot weather
- **Response Time**: Under 3 seconds for standard queries

### 3. Development Workflow

#### Step 1: Evaluate Current State
```bash
# Run full evaluation
python -m agent_eval.evaluator

# Review results
cat agent_eval/latest_report.json
```

The report includes:
- Success rates per test case
- Quality scores for suggestions
- Performance metrics
- Improvement recommendations

#### Step 2: Analyze Issues
Common patterns to look for:
- Generic vs specific suggestions
- Weather-inappropriate activities
- Slow response times
- Error patterns

#### Step 3: Implement Improvements
Example improvement cycle:
```python
# Before: Generic attraction query
query = f"tourist attraction {city}"

# After: Specific landmark query
query = f"most famous landmark monument {city} -tripadvisor -booking"

# Before: Basic pattern matching
r'([^,.]+(?:Museum|Park|Garden))'

# After: Enhanced pattern matching
r'(?:the\s+)?([^,.]+(?:Palace|Fort|Temple|Monument|Museum))'
r'([^,.]+(?:Taj Mahal|Great Wall|Eiffel Tower|Pyramids))'
```

#### Step 4: Verify Improvements
```bash
# Test specific changes
python scripts/run_tests.py --unit --pattern "test_activity_suggestion"

# Run full test suite
python scripts/run_tests.py --all

# Re-run evaluation
python -m agent_eval.evaluator
```

Common areas for improvement:
- **Search & Extraction**
  - Search query construction in `tools/brave_search.py`
  - Attraction extraction patterns

- **LLM Optimizations**
  - Prompt engineering in `agent.py`:
    - Enhance city validation prompt with structured JSON output
    - Add geographic context validation (e.g., state/country)
    - Implement few-shot examples for better city name extraction
    - Add confidence scores to city validation responses
    - Optimize temperature settings per prompt type
  - LLM response parsing and validation
  - Context window optimization
  - Temperature and model parameter tuning
  - Fallback handling for LLM errors

- **Error Handling & Performance**
  - API error recovery and retries
  - Response time optimization
  - Rate limit management

## Token Usage and Cost Tracking

The agent provides transparent information about LLM usage:

- Each LLM call shows token usage and cost: `💰 LLM call: 350 tokens (300 input, 50 output) - Cost: $0.00021`
- The thinking process is indicated with: `🤔 Thinking: Analyzing weather conditions...`
- Final usage statistics are shown when exiting the agent
- Set `VERBOSE_LLM=1` for more detailed logging

## License

MIT License - See LICENSE file for details 