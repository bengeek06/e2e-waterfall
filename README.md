# Waterfall E2E Tests

End-to-end test suite for the Waterfall application using Selenium and pytest.

## Overview

This test suite provides comprehensive end-to-end testing for the Waterfall web application, including:
- Application initialization tests
- User authentication and login flows
- API endpoint testing
- Permission and policy management (Guardian)

## Project Structure

```
tests/
├── api/                    # API endpoint tests
│   ├── auth/              # Authentication API tests
│   └── guardian/          # Guardian (permissions/policies) API tests
├── init/                  # Application initialization tests
├── login/                 # Legacy login tests
├── ui/                    # UI/Selenium tests
│   └── test_login.py     # Login flow tests
├── conftest.py           # Pytest fixtures and configuration
└── requirements.txt      # Python dependencies
```

## Prerequisites

- Python 3.13+
- Chrome browser (for Selenium tests)
- ChromeDriver (automatically managed by selenium)
- Running Waterfall application instance

## Installation

1. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate     # On Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Tests use configuration from `conftest.py`. Default configuration:
- Web URL: `http://localhost:3000`
- API URL: `http://localhost:8000`
- Default credentials for testing

You can override these by modifying the `app_config` fixture in `conftest.py`.

## Running Tests

### Run all tests
```bash
pytest -v
```

### Run specific test categories
```bash
# UI tests only
pytest ui/ -v

# API tests only
pytest api/ -v

# Login tests specifically
pytest ui/test_login.py -v

# Initialization tests
pytest init/ -v
```

### Run with specific markers
```bash
# Run tests in order
pytest --order -v

# Run with detailed output
pytest -vv -s

# Run with coverage
pytest --cov=. -v
```

## Test Categories

### 1. UI Tests (`ui/`)
Selenium-based tests for web interface interactions.

**Login Tests** (`ui/test_login.py`):
- Autonomous pattern with automatic app initialization
- Uses `data-testid` selectors for reliability
- Tests login flow, session management, and authentication state

Key features:
- ✅ Auto-initialization if app not ready
- ✅ Self-contained and reproducible
- ✅ No manual setup required

### 2. API Tests (`api/`)
Direct API endpoint testing using requests library.

**Authentication** (`api/auth/`):
- Login/logout endpoints
- Session management
- Token validation

**Guardian** (`api/guardian/`):
- Permission management
- Policy enforcement
- Access control testing

### 3. Initialization Tests (`init/`)
Application setup and database initialization tests.

## Test Patterns

### Autonomous Tests
Tests automatically handle prerequisites:
```python
@pytest.fixture(scope="class", autouse=True)
def ensure_app_initialized(self, app_config, driver):
    """Auto-initialize app if needed"""
    # Check if initialized
    # If not, initialize automatically
    # Then proceed with tests
```

### Element Selection
Uses semantic `data-testid` attributes:
```python
email_field = driver.find_element(
    By.CSS_SELECTOR, 
    '[data-testid="login-email-input"]'
)
```

## Fixtures

Common fixtures available in `conftest.py`:

- `app_config`: Application configuration (URLs, credentials)
- `driver`: Selenium WebDriver instance (auto-managed)
- `check_init_status`: Check if app is initialized
- `ensure_app_initialized`: Auto-initialize for login tests

## Debugging

### Run tests with browser visible
Modify `conftest.py` to disable headless mode:
```python
options.add_argument('--headless=new')  # Comment this line
```

### Capture screenshots on failure
Screenshots are automatically saved on test failures (if configured).

### Verbose output
```bash
pytest -vv -s --tb=short
```

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:
- Headless Chrome for automated environments
- Configurable timeouts and retries
- Clear success/failure reporting

## Best Practices

1. **Use data-testid attributes** for element selection
2. **Keep tests autonomous** - no dependencies between tests
3. **Use explicit waits** instead of sleep() when possible
4. **Clean up after tests** - fixtures handle this automatically
5. **Test one thing at a time** - focused, atomic tests

## Troubleshooting

### Chrome/ChromeDriver issues
- Ensure Chrome is installed
- selenium-manager handles ChromeDriver automatically
- Check Chrome version compatibility

### Connection errors
- Verify Waterfall application is running
- Check URLs in configuration
- Ensure ports 3000 (web) and 8000 (api) are accessible

### Test timeouts
- Increase timeout values in WebDriverWait
- Check application response times
- Verify network connectivity

## Contributing

When adding new tests:
1. Follow the autonomous pattern
2. Use `data-testid` for selectors
3. Add appropriate fixtures if needed
4. Document test purpose clearly
5. Ensure tests are reproducible

## License

See LICENSE file in the root directory.

