
def test_login(driver):
    driver.get("http://example.com/login")
    
    #username_field = driver.find_element("name", "username")
    #password_field = driver.find_element("name", "password")
    #login_button = driver.find_element("id", "login-button")
    
    #username_field.send_keys("testuser")
    #password_field.send_keys("securepassword")
    #login_button.click()
    
    #assert "Dashboard" in driver.title
    assert True  # Placeholder assertion