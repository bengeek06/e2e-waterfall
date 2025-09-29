import os
from dotenv import load_dotenv
from pytest import fixture
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.', '.env.test'))

@fixture(scope="session")
def driver():
    # Set up Chrome WebDriver using webdriver-manager with version for Chromium 140
    chrome_service = ChromeService(ChromeDriverManager(chrome_type="chromium").install())
    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"  # Specify Chromium path
    options.add_argument("--headless")  # Run in headless mode for testing
    options.add_argument("--no-sandbox")  # Required for some CI environments
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    options.add_argument("--disable-gpu")  # Disable GPU for headless mode
    driver = webdriver.Chrome(service=chrome_service, options=options)
    
    yield driver
    
    # Teardown
    driver.quit()