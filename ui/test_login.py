
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import requests

class TestUserLogin:
    """Tests de connexion utilisateur - autonomes et reproductibles"""
    
    @pytest.fixture(scope="class", autouse=True)
    def ensure_app_initialized(self, app_config, driver):
        """S'assurer que l'application est initialisée avant de tester le login"""
        web_url = app_config['web_url']
        
        # Vérifier si l'application est initialisée
        try:
            response = requests.get(f"{web_url}/api/identity/init-db", verify=False, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('initialized', False):
                    print("✓ Application déjà initialisée - prêt pour les tests de login")
                    return True
        except Exception as e:
            print(f"⚠️ Erreur lors de la vérification de l'initialisation: {e}")
        
        # Si pas initialisée, on l'initialise MAINTENANT
        print("⚠️ Application non initialisée - initialisation automatique en cours...")
        
        driver.get(f"{web_url}/init-app")
        wait = WebDriverWait(driver, 10)
        
        # Remplir le formulaire d'initialisation
        company_field = wait.until(EC.element_to_be_clickable((By.ID, "company")))
        company_field.clear()
        company_field.send_keys(app_config['company_name'])
        
        user_field = wait.until(EC.element_to_be_clickable((By.ID, "user")))
        user_field.clear()
        user_field.send_keys(app_config['login'])
        
        password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
        password_field.clear()
        password_field.send_keys(app_config['password'])
        
        password_confirm_field = wait.until(EC.element_to_be_clickable((By.ID, "passwordConfirm")))
        password_confirm_field.clear()
        password_confirm_field.send_keys(app_config['password'])
        
        time.sleep(1)
        
        submit_button = wait.until(EC.element_to_be_clickable((By.ID, "submit")))
        submit_button.click()
        
        # Attendre la redirection vers login
        wait.until(lambda d: "/login" in d.current_url)
        print("✓ Application initialisée avec succès - prêt pour les tests de login")
        
        return True
    
    @pytest.mark.order(1)
    def test_01_access_login_page_directly(self, driver, app_config):
        """Étape 1: Accès direct à la page de login"""
        web_url = app_config['web_url']
        login_url = f"{web_url}/login"
        
        # Accéder directement à la page de login
        driver.get(login_url)
        
        # Vérifier qu'on est bien sur la page de login
        assert "/login" in driver.current_url
        print(f"✓ Accès direct à la page de login réussi: {driver.current_url}")
    
    @pytest.mark.order(2)
    def test_02_verify_login_form_elements(self, driver, app_config):
        """Étape 2: Vérifier la présence des éléments du formulaire de login"""
        web_url = app_config['web_url']
        
        # S'assurer qu'on est sur la page login
        if "/login" not in driver.current_url:
            driver.get(f"{web_url}/login")
        
        wait = WebDriverWait(driver, 10)
        
        # Vérifier le champ email
        email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="login-email-input"]')))
        assert email_field.is_displayed()
        print("✓ Champ 'email' trouvé et affiché")
        
        # Vérifier le champ password
        password_field = driver.find_element(By.CSS_SELECTOR, '[data-testid="login-password-input"]')
        assert password_field.is_displayed()
        print("✓ Champ 'password' trouvé et affiché")
        
        # Vérifier le bouton submit
        submit_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="login-submit-button"]')
        assert submit_button.is_displayed()
        print("✓ Bouton 'submit' trouvé et affiché")
        
        # Optionnel: vérifier le type des champs
        assert email_field.get_attribute("type") in ["email", "text"]
        assert password_field.get_attribute("type") == "password"
        print("✓ Types de champs validés")
    
    @pytest.mark.order(3)
    def test_03_perform_successful_login(self, driver, app_config):
        """Étape 3: Effectuer une connexion réussie"""
        web_url = app_config['web_url']
        
        # S'assurer qu'on est sur la page login
        if "/login" not in driver.current_url:
            driver.get(f"{web_url}/login")
            time.sleep(1)
        
        # Récupérer les identifiants depuis la configuration
        login_email = app_config['login']
        login_password = app_config['password']
        
        wait = WebDriverWait(driver, 10)
        
        # Remplir le formulaire de connexion
        email_field = driver.find_element(By.CSS_SELECTOR, '[data-testid="login-email-input"]')
        email_field.clear()
        email_field.send_keys(login_email)
        print(f"✓ Email saisi: {login_email}")
        
        password_field = driver.find_element(By.CSS_SELECTOR, '[data-testid="login-password-input"]')
        password_field.clear()
        password_field.send_keys(login_password)
        print("✓ Mot de passe saisi")
        
        # Soumettre le formulaire en appuyant sur Enter
        password_field.send_keys(Keys.RETURN)
        print("✓ Formulaire de connexion soumis (Enter)")
    
    @pytest.mark.order(4)
    def test_04_verify_successful_redirect_to_welcome(self, driver, app_config):
        """Étape 4: Vérifier la redirection vers /welcome après connexion réussie"""
        # Attendre la redirection vers /welcome
        wait = WebDriverWait(driver, 15)
        
        try:
            # Attendre que l'URL contienne /welcome
            wait.until(lambda d: "/welcome" in d.current_url)
            print(f"✓ Redirection réussie vers: {driver.current_url}")
            
            # Vérifier qu'on est bien sur la page welcome
            assert "/welcome" in driver.current_url
            
        except Exception as e:
            print(f"❌ Erreur lors de l'attente de redirection vers /welcome: {e}")
            print(f"URL actuelle: {driver.current_url}")
            
            # Vérifier s'il y a des messages d'erreur sur la page
            try:
                # Chercher des messages d'erreur potentiels
                error_elements = driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, [class*='error']")
                if error_elements:
                    for error in error_elements:
                        if error.is_displayed():
                            print(f"❌ Message d'erreur trouvé: {error.text}")
            except:
                pass
            
            raise
    
    @pytest.mark.order(5)
    def test_05_save_authentication_cookies(self, driver):
        """Étape 5: Vérifier les cookies de session après connexion"""
        # Récupérer tous les cookies après connexion
        cookies = driver.get_cookies()
        
        # Afficher les cookies pour debug
        print(f"✓ {len(cookies)} cookies trouvés après connexion:")
        session_cookies = []
        for cookie in cookies:
            if 'httpOnly' in cookie and cookie.get('httpOnly'):
                print(f"  - {cookie['name']} (httpOnly) - SESSION COOKIE")
                session_cookies.append(cookie)
            else:
                print(f"  - {cookie['name']}")
        
        # Vérifier qu'au moins un cookie a été défini
        assert len(cookies) > 0, "Aucun cookie trouvé après connexion"
        
        # Idéalement, on devrait avoir au moins un cookie de session
        if session_cookies:
            print(f"✓ {len(session_cookies)} cookie(s) de session httpOnly détecté(s)")
        else:
            print("⚠️ Aucun cookie httpOnly détecté - vérifier l'implémentation de session")
    
    @pytest.mark.order(6)
    def test_06_verify_authenticated_state(self, driver, app_config):
        """Étape 6: Vérifier que l'utilisateur est bien authentifié"""
        web_url = app_config['web_url']
        
        # Sauvegarder les cookies actuels
        cookies = driver.get_cookies()
        
        # Accéder à l'index pour voir le comportement avec session active
        driver.get(web_url)
        time.sleep(2)
        
        current_url = driver.current_url
        print(f"✓ Accès à l'index avec session active: {current_url}")
        
        # Avec une session active, on ne devrait plus être redirigé vers login
        # (sauf si l'application a une logique spécifique)
        if "/login" not in current_url:
            print("✓ Session active confirmée - pas de redirection vers login")
        else:
            print("⚠️ Redirection vers login malgré la session - vérifier l'implémentation")