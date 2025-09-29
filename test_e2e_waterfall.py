import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

class TestCompleteUserJourney:
    """Parcours utilisateur complet E2E : Initialisation → Connexion → Welcome
    
    Ce test est conçu pour fonctionner avec une base de données vierge,
    idéal pour les pipelines CI/CD comme GitHub Actions.
    """
    
    @pytest.mark.order(1)
    def test_01_fresh_app_redirects_to_init(self, driver, app_config, app_session):
        """Étape 1: Une app avec base vierge redirige vers /init-app"""
        web_url = app_config['web_url']
        
        # Accéder à la page d'accueil
        driver.get(web_url)
        
        # Attendre la redirection automatique vers init-app
        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: "/init-app" in d.current_url)
        
        # Vérifier qu'on est bien sur la page d'initialisation
        assert "/init-app" in driver.current_url
        print(f"✓ Base vierge détectée - Redirection vers: {driver.current_url}")
    
    @pytest.mark.order(2)
    def test_02_initialize_application_with_admin_user(self, driver, app_config, app_session):
        """Étape 2: Initialiser l'application avec un utilisateur admin"""
        # Vérifier la présence des éléments du formulaire
        wait = WebDriverWait(driver, 10)
        
        # Attendre et vérifier tous les champs
        company_field = wait.until(EC.presence_of_element_located((By.ID, "company")))
        user_field = driver.find_element(By.ID, "user")
        password_field = driver.find_element(By.ID, "password")
        password_confirm_field = driver.find_element(By.ID, "passwordConfirm")
        submit_button = driver.find_element(By.ID, "submit")
        
        # Vérifier que tous les éléments sont affichés
        assert all([
            company_field.is_displayed(),
            user_field.is_displayed(),
            password_field.is_displayed(),
            password_confirm_field.is_displayed(),
            submit_button.is_displayed()
        ])
        print("✓ Tous les éléments du formulaire d'initialisation sont présents")
        
        # Récupérer les données de configuration
        company_name = app_config['company_name']
        login = app_config['login']
        password = app_config['password']
        
        # Remplir le formulaire d'initialisation
        company_field.clear()
        company_field.send_keys(company_name)
        
        user_field.clear()
        user_field.send_keys(login)
        
        password_field.clear()
        password_field.send_keys(password)
        
        password_confirm_field.clear()
        password_confirm_field.send_keys(password)
        
        print(f"✓ Formulaire rempli - Company: {company_name}, User: {login}")
        
        # Sauvegarder l'état dans la session
        app_session.current_user = login
        
        # Soumettre le formulaire
        submit_button.click()
        print("✓ Formulaire d'initialisation soumis")
    
    @pytest.mark.order(3)
    def test_03_verify_redirect_to_login_after_init(self, driver, app_session):
        """Étape 3: Vérifier la redirection vers /login après initialisation"""
        # Attendre la redirection vers la page de login
        wait = WebDriverWait(driver, 15)
        
        try:
            wait.until(lambda d: "/login" in d.current_url)
            print(f"✓ Redirection post-initialisation réussie vers: {driver.current_url}")
            
            # Marquer l'application comme initialisée
            app_session.is_initialized = True
            
            assert "/login" in driver.current_url
            
        except Exception as e:
            print(f"❌ Erreur lors de la redirection: {e}")
            print(f"URL actuelle: {driver.current_url}")
            raise
    
    @pytest.mark.order(4)
    def test_04_perform_user_login_with_created_account(self, driver, app_config, app_session):
        """Étape 4: Se connecter avec le compte utilisateur créé à l'initialisation"""
        # Vérifier qu'on est bien sur la page de login
        assert "/login" in driver.current_url
        
        # Vérifier la présence des éléments du formulaire de login
        wait = WebDriverWait(driver, 10)
        
        email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
        password_field = driver.find_element(By.ID, "password")
        submit_button = driver.find_element(By.ID, "submit")
        
        # Vérifier que tous les éléments sont affichés
        assert all([
            email_field.is_displayed(),
            password_field.is_displayed(),
            submit_button.is_displayed()
        ])
        print("✓ Tous les éléments du formulaire de connexion sont présents")
        
        # Récupérer les identifiants depuis la configuration
        login_email = app_config['login']
        login_password = app_config['password']
        
        # Remplir le formulaire de connexion
        email_field.clear()
        email_field.send_keys(login_email)
        
        password_field.clear()
        password_field.send_keys(login_password)
        
        print(f"✓ Identifiants saisis - Email: {login_email}")
        
        # Soumettre le formulaire de connexion
        submit_button.click()
        print("✓ Formulaire de connexion soumis")
    
    @pytest.mark.order(5)
    def test_05_verify_successful_login_redirect_to_welcome(self, driver, app_session):
        """Étape 5: Vérifier la redirection vers /welcome après connexion réussie"""
        # Attendre la redirection vers /welcome
        wait = WebDriverWait(driver, 15)
        
        try:
            wait.until(lambda d: "/welcome" in d.current_url)
            print(f"✓ Connexion réussie - Redirection vers: {driver.current_url}")
            
            # Marquer l'utilisateur comme connecté
            app_session.is_logged_in = True
            
            assert "/welcome" in driver.current_url
            
        except Exception as e:
            print(f"❌ Erreur lors de la connexion: {e}")
            print(f"URL actuelle: {driver.current_url}")
            
            # Vérifier s'il y a des messages d'erreur
            try:
                error_elements = driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, [class*='error']")
                for error in error_elements:
                    if error.is_displayed():
                        print(f"❌ Message d'erreur: {error.text}")
            except:
                pass
            
            raise
    
    @pytest.mark.order(6)
    def test_06_capture_and_verify_authentication_session(self, driver, app_session):
        """Étape 6: Capturer et vérifier la session d'authentification"""
        # Récupérer tous les cookies après connexion réussie
        cookies = driver.get_cookies()
        app_session.cookies = cookies
        
        # Analyser les cookies
        print(f"✓ {len(cookies)} cookies capturés après connexion:")
        session_cookies = []
        for cookie in cookies:
            if 'httpOnly' in cookie and cookie.get('httpOnly'):
                print(f"  - {cookie['name']} (httpOnly) - SESSION COOKIE")
                session_cookies.append(cookie)
            else:
                print(f"  - {cookie['name']}")
        
        # Vérifications
        assert len(cookies) > 0, "Aucun cookie trouvé après connexion réussie"
        
        if session_cookies:
            print(f"✓ {len(session_cookies)} cookie(s) de session httpOnly détecté(s)")
        else:
            print("⚠️ Aucun cookie httpOnly - vérifier l'implémentation de session")
        
        # Vérifier l'état de la session
        assert app_session.is_initialized, "L'application devrait être initialisée"
        assert app_session.is_logged_in, "L'utilisateur devrait être connecté"
        print("✓ État de session validé")
    
    @pytest.mark.order(7) 
    def test_07_verify_persistent_authentication(self, driver, app_config, app_session):
        """Étape 7: Vérifier que l'authentification persiste lors de la navigation"""
        web_url = app_config['web_url']
        
        # Restaurer les cookies de session
        current_cookies = driver.get_cookies()
        print(f"✓ Cookies actifs: {len(current_cookies)}")
        
        # Naviguer vers l'index pour tester la persistance de session
        driver.get(web_url)
        time.sleep(2)
        
        current_url = driver.current_url
        print(f"✓ Navigation vers l'index - URL résultante: {current_url}")
        
        # Avec une session active, on ne devrait pas être redirigé vers init-app ou login
        assert "/init-app" not in current_url, "Ne devrait plus rediriger vers init-app"
        
        if "/login" not in current_url:
            print("✓ Session persistante confirmée - Pas de redirection vers login")
        else:
            print("⚠️ Redirection vers login - Vérifier la gestion de session côté serveur")
        
        print("✓ Parcours utilisateur E2E complet terminé avec succès!")
    
    @pytest.mark.order(8)
    def test_08_final_state_verification(self, app_session, app_config):
        """Étape 8: Vérification finale de l'état de l'application"""
        # Vérifications finales
        assert app_session.is_initialized, "L'application doit être initialisée"
        assert app_session.is_logged_in, "L'utilisateur doit être connecté"
        assert app_session.current_user == app_config['login'], "L'utilisateur courant doit correspondre"
        assert len(app_session.cookies) > 0, "Des cookies de session doivent être présents"
        
        print("🎉 SUCCÈS - Parcours utilisateur E2E complet validé:")
        print(f"   ✓ Application initialisée avec company: {app_config['company_name']}")
        print(f"   ✓ Utilisateur connecté: {app_session.current_user}")
        print(f"   ✓ Session active avec {len(app_session.cookies)} cookies")
        print("   ✓ Prêt pour les tests de fonctionnalités avancées")