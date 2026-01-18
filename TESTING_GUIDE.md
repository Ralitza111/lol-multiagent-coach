# 🧪 Testing Guide - LoL Coach Multi-Agent System

## Overview
This project includes comprehensive unit tests for the multi-agent system using pytest.

## Test Coverage

### 17 Tests Across 5 Test Classes:

1. **TestRouting** (7 tests) - Validates routing logic
   - Pregame agent routing
   - Match analyzer routing
   - Build advisor routing
   - Video guide routing
   - Knowledge base routing
   - Orchestrator routing

2. **TestAgents** (3 tests) - Agent functionality
   - Coach creation
   - Agent information retrieval
   - System information

3. **TestErrorHandling** (3 tests) - Error handling
   - Error handler responses
   - Fallback responses
   - Invalid thread handling

4. **TestRouteQueryModel** (2 tests) - Data validation
   - Model creation
   - Model validation

5. **TestIntegration** (2 tests) - End-to-end
   - Simple query flow
   - Pregame query flow

## Running Tests

### Install pytest (if not already installed):
```bash
pip install pytest
```

### Run all tests:
```bash
pytest tests/test_multi_agent.py -v
```

### Run specific test class:
```bash
pytest tests/test_multi_agent.py::TestRouting -v
```

### Run specific test:
```bash
pytest tests/test_multi_agent.py::TestRouting::test_pregame_agent_routing -v
```

### Run with detailed output:
```bash
pytest tests/ -v --tb=short
```

### Run with coverage (requires pytest-cov):
```bash
pip install pytest-cov
pytest tests/ --cov=. --cov-report=html
```

## Test Results

Expected output:
```
============================= test session starts ==============================
platform darwin -- Python 3.13.7, pytest-9.0.2, pluggy-1.6.0
collected 17 items

tests/test_multi_agent.py::TestRouting::test_pregame_agent_routing PASSED [  5%]
tests/test_multi_agent.py::TestRouting::test_pregame_agent_pick_routing PASSED [ 11%]
tests/test_multi_agent.py::TestRouting::test_match_analyzer_routing PASSED [ 17%]
tests/test_multi_agent.py::TestRouting::test_build_advisor_routing PASSED [ 23%]
tests/test_multi_agent.py::TestRouting::test_video_guide_routing PASSED [ 29%]
tests/test_multi_agent.py::TestRouting::test_knowledge_base_routing PASSED [ 35%]
tests/test_multi_agent.py::TestRouting::test_orchestrator_routing PASSED [ 41%]
tests/test_multi_agent.py::TestAgents::test_coach_creation PASSED [ 47%]
tests/test_multi_agent.py::TestAgents::test_agent_info PASSED [ 52%]
tests/test_multi_agent.py::TestAgents::test_system_info PASSED [ 58%]
tests/test_multi_agent.py::TestErrorHandling::test_error_handler PASSED [ 64%]
tests/test_multi_agent.py::TestErrorHandling::test_fallback_response PASSED [ 70%]
tests/test_multi_agent.py::TestErrorHandling::test_chat_with_invalid_thread PASSED [ 76%]
tests/test_multi_agent.py::TestRouteQueryModel::test_route_query_creation PASSED [ 82%]
tests/test_multi_agent.py::TestRouteQueryModel::test_route_query_validation PASSED [ 88%]
tests/test_multi_agent.py::TestIntegration::test_simple_query_flow PASSED [ 94%]
tests/test_multi_agent.py::TestIntegration::test_pregame_query_flow PASSED [100%]

======================= 17 passed, 40 warnings in 26.15s =======================
```

## Configuration

Tests are configured via `pytest.ini`:
- Verbose output enabled
- Short tracebacks for cleaner output
- Test discovery patterns defined
- Coverage settings (if using pytest-cov)

## CI/CD Integration

To integrate with CI/CD pipelines:

### GitHub Actions:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.13
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      - name: Run tests
        run: pytest tests/ -v
```

## Adding New Tests

To add new tests:

1. Create test functions starting with `test_`
2. Use pytest fixtures for setup
3. Use assert statements for validation
4. Organize into test classes for clarity

Example:
```python
def test_new_feature(coach):
    """Test a new feature"""
    result = coach.some_new_method()
    assert result is not None
    assert isinstance(result, str)
```

## Troubleshooting

### Import Errors
If you get import errors, ensure you're in the project root:
```bash
cd /Users/ralitzamondal/Documents/lol-coach-agent
pytest tests/
```

### API Key Errors
Tests require valid API keys in `.env` file:
```
OPENAI_API_KEY=your_key_here
RIOT_API_KEY=your_key_here
```

### Slow Tests
Some tests make API calls. Use markers to skip slow tests:
```bash
pytest tests/ -v -m "not slow"
```

## Test Metrics

- **Total Tests**: 17
- **Pass Rate**: 100%
- **Coverage**: Core routing, agents, and error handling
- **Average Run Time**: ~26 seconds

---

**Last Updated**: January 17, 2026  
**Status**: All tests passing ✅
