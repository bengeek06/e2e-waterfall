# Contributing to Waterfall E2E Tests

Thank you for your interest in contributing to the **Waterfall E2E Test Suite**!

> **Note**: This test suite is part of the larger [Waterfall](../README.md) project. For the overall development workflow, branch strategy, and contribution guidelines, please refer to the [main CONTRIBUTING.md](../CONTRIBUTING.md) in the root repository.

## Table of Contents

- [Test Suite Overview](#test-suite-overview)
- [Development Setup](#development-setup)
- [Writing Tests](#writing-tests)
- [Testing Conventions](#testing-conventions)
- [Running Tests](#running-tests)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Test Suite Overview

The **E2E Test Suite** provides comprehensive end-to-end testing for the Waterfall application:

- **Technology Stack**: Python 3.13+, Pytest, Selenium WebDriver
- **Coverage**:
  - API endpoint testing (Auth, Identity, Guardian services)
  - UI flow testing with Selenium
  - Application initialization tests
  - Integration tests across services
- **Test Count**: 100+ tests covering API and UI

**Test Categories:**
- `api/` - Direct API endpoint tests using requests library
- `ui/` - Browser-based UI tests using Selenium
- `init/` - Application initialization tests
- `helpers/` - Shared test utilities and fixtures

## Development Setup

### Prerequisites

- Python 3.13+
- Chrome browser (for Selenium tests)
- ChromeDriver (automatically managed by selenium-manager)
- Running Waterfall application instance

### Local Setup

```bash
# Navigate to tests directory
cd tests

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Environment Configuration

Tests use configuration from `conftest.py`. You can override defaults:

```python
# conftest.py
@pytest.fixture(scope="session")
def app_config():
    return {
        'web_url': os.getenv('WEB_URL', 'http://localhost:3000'),
        'api_url': os.getenv('API_URL', 'http://localhost:8000'),
        'default_email': os.getenv('LOGIN', 'admin@example.com'),
        'default_password': os.getenv('PASSWORD', 'admin123')
    }
```

## Writing Tests

### API Tests

**Structure:**
```python
# tests/api/identity/test_users.py
import pytest
import requests

class TestUserEndpoints:
    """Test suite for user management endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self, app_config, auth_headers):
        """Setup for each test."""
        self.api_url = app_config['api_url']
        self.headers = auth_headers
        
    def test_get_users(self):
        """Test retrieving list of users."""
        response = requests.get(
            f"{self.api_url}/api/identity/users",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
    def test_create_user(self):
        """Test creating a new user."""
        payload = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'company_id': 1
        }
        
        response = requests.post(
            f"{self.api_url}/api/identity/users",
            json=payload,
            headers=self.headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data['email'] == payload['email']
        assert 'id' in data
        
        # Cleanup
        user_id = data['id']
        requests.delete(
            f"{self.api_url}/api/identity/users/{user_id}",
            headers=self.headers
        )
```

### UI Tests

**Structure:**
```python
# tests/ui/test_login.py
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestLoginFlow:
    """Test suite for login functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self, driver, app_config):
        """Setup for each test."""
        self.driver = driver
        self.web_url = app_config['web_url']
        
    def test_successful_login(self, app_config):
        """Test successful user login."""
        # Navigate to login page
        self.driver.get(f"{self.web_url}/login")
        
        # Wait for page load
        wait = WebDriverWait(self.driver, 10)
        email_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="login-email-input"]')
            )
        )
        
        # Fill login form
        email_input.send_keys(app_config['default_email'])
        
        password_input = self.driver.find_element(
            By.CSS_SELECTOR,
            '[data-testid="login-password-input"]'
        )
        password_input.send_keys(app_config['default_password'])
        
        # Submit form
        submit_button = self.driver.find_element(
            By.CSS_SELECTOR,
            '[data-testid="login-submit-button"]'
        )
        submit_button.click()
        
        # Verify redirect to welcome page
        wait.until(EC.url_contains('/welcome'))
        assert '/welcome' in self.driver.current_url
        
    def test_invalid_credentials(self):
        """Test login with invalid credentials."""
        self.driver.get(f"{self.web_url}/login")
        
        wait = WebDriverWait(self.driver, 10)
        email_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="login-email-input"]')
            )
        )
        
        email_input.send_keys('invalid@example.com')
        
        password_input = self.driver.find_element(
            By.CSS_SELECTOR,
            '[data-testid="login-password-input"]'
        )
        password_input.send_keys('wrongpassword')
        
        submit_button = self.driver.find_element(
            By.CSS_SELECTOR,
            '[data-testid="login-submit-button"]'
        )
        submit_button.click()
        
        # Verify error message
        error_message = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="login-error-message"]')
            )
        )
        assert error_message.is_displayed()
```

## Testing Conventions

### Test Naming

```python
# ✅ Good: Descriptive test names
def test_create_user_with_valid_data():
    pass

def test_create_user_with_duplicate_email_returns_400():
    pass

def test_login_redirects_to_welcome_page():
    pass

# ❌ Bad: Vague test names
def test_user():
    pass

def test_login():
    pass
```

### Element Selection

**Use `data-testid` attributes** for reliable element selection:

```python
# ✅ Good: Semantic test IDs
email_input = driver.find_element(
    By.CSS_SELECTOR,
    '[data-testid="login-email-input"]'
)

# ❌ Bad: Fragile selectors
email_input = driver.find_element(
    By.CSS_SELECTOR,
    'input[type="email"]'  # Could match multiple elements
)

email_input = driver.find_element(
    By.XPATH,
    '//div[@class="form-group"]/input[1]'  # Breaks with layout changes
)
```

### Assertions

```python
# ✅ Good: Specific assertions with clear messages
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
assert 'id' in data, "Response missing 'id' field"
assert len(users) > 0, "Expected at least one user"

# ❌ Bad: Generic assertions
assert response.status_code
assert data
```

### Test Independence

```python
# ✅ Good: Self-contained tests with cleanup
def test_create_and_delete_user(self):
    # Create
    response = requests.post(url, json=user_data)
    user_id = response.json()['id']
    
    # Test
    assert response.status_code == 201
    
    # Cleanup
    requests.delete(f"{url}/{user_id}")

# ❌ Bad: Dependent on other tests
def test_create_user(self):
    # Creates user with id=123
    pass

def test_get_user(self):
    # Assumes user 123 exists from previous test
    response = requests.get(f"{url}/123")
```

## Running Tests

### Run All Tests

```bash
# All tests
pytest -v

# Specific category
pytest api/ -v
pytest ui/ -v

# Specific file
pytest tests/api/auth/test_login.py -v

# Specific test
pytest tests/api/auth/test_login.py::TestLoginEndpoint::test_successful_login -v
```

### With Coverage

```bash
pytest --cov=. --cov-report=html -v
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto -v
```

### Verbose Output

```bash
# Show print statements
pytest -v -s

# Short traceback
pytest -v --tb=short

# Full traceback
pytest -v --tb=long
```

## Common Patterns

### Authentication Fixture

```python
# conftest.py
@pytest.fixture(scope="session")
def auth_headers(app_config):
    """Get authentication headers for API requests."""
    # Login
    response = requests.post(
        f"{app_config['api_url']}/api/auth/login",
        json={
            'email': app_config['default_email'],
            'password': app_config['default_password']
        }
    )
    
    access_token = response.json()['access_token']
    
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
```

### Auto-initialization Fixture

```python
@pytest.fixture(scope="class", autouse=True)
def ensure_app_initialized(app_config, driver):
    """Ensure app is initialized before running tests."""
    # Check init status
    response = requests.get(f"{app_config['web_url']}/api/init-status")
    
    if response.json().get('initialized') == False:
        # Initialize app
        driver.get(f"{app_config['web_url']}/init-app")
        # ... complete initialization flow
```

### Explicit Waits

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Wait for element
wait = WebDriverWait(driver, 10)
element = wait.until(
    EC.presence_of_element_located((By.ID, "my-element"))
)

# Wait for element to be clickable
button = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit"))
)
button.click()

# Wait for URL change
wait.until(EC.url_contains('/success'))
```

## Troubleshooting

### Chrome/ChromeDriver Issues

```bash
# Check Chrome version
google-chrome --version

# selenium-manager handles ChromeDriver automatically
# If issues persist, set explicit path:
export CHROMEDRIVER_PATH=/path/to/chromedriver
```

### Headless Mode

```python
# conftest.py - Disable headless for debugging
options = webdriver.ChromeOptions()
# options.add_argument('--headless=new')  # Comment out
options.add_argument('--no-sandbox')
```

### Connection Timeouts

```python
# Increase timeout
wait = WebDriverWait(driver, 30)  # 30 seconds

# Check services are running
curl http://localhost:3000
curl http://localhost:5001/health
```

### Test Data Cleanup

```python
@pytest.fixture(autouse=True)
def cleanup(request):
    """Cleanup after each test."""
    yield  # Test runs here
    
    # Cleanup code
    # Delete test users, projects, etc.
```

## Best Practices

1. **Use `data-testid`** for element selection
2. **Keep tests independent** - no dependencies between tests
3. **Use explicit waits** instead of `sleep()`
4. **Clean up test data** in fixtures
5. **Test one thing** per test function
6. **Use descriptive names** for tests and fixtures
7. **Mock external dependencies** when appropriate
8. **Run tests locally** before committing

## Getting Help

- **Main Project**: See [root CONTRIBUTING.md](../CONTRIBUTING.md)
- **Issues**: Use GitHub issues with `component:tests` label
- **Code of Conduct**: [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)
- **Documentation**: [README.md](README.md)

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [Selenium Python Bindings](https://selenium-python.readthedocs.io/)
- [Requests Documentation](https://requests.readthedocs.io/)

---

**Remember**: Always refer to the [main CONTRIBUTING.md](../CONTRIBUTING.md) for branch strategy, commit conventions, and pull request process!
