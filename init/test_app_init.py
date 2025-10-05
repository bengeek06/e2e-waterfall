import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

class TestApplicationInit:
    """Parcours complet d'initialisation de l'application"""
    
    @pytest.mark.order(1)
    def test_01_access_index_redirects_to_init(self, driver, app_config, app_session):
        """Étape 1: Accès à l'index redirige vers init-app si l'app n'est pas initialisée"""
        web_url = app_config['web_url']
        
        # Accéder à la page d'accueil
        driver.get(web_url)
        
        # Attendre la redirection automatique vers init-app
        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: "/init-app" in d.current_url)
        
        # Vérifier qu'on est bien sur la page d'initialisation
        assert "/init-app" in driver.current_url
        print(f"✓ Redirection automatique vers {driver.current_url}")
    
    @pytest.mark.order(2)
    def test_02_init_page_contains_form_elements(self, driver, app_config):
        """Étape 2: Vérifier que la page d'initialisation contient tous les éléments du formulaire"""
        # Vérifier la présence de tous les champs du formulaire
        wait = WebDriverWait(driver, 10)
        
        # Vérifier le champ company
        company_field = wait.until(EC.presence_of_element_located((By.ID, "company")))
        assert company_field.is_displayed()
        print("✓ Champ 'company' trouvé et affiché")
        
        # Vérifier le champ user
        user_field = driver.find_element(By.ID, "user")
        assert user_field.is_displayed()
        print("✓ Champ 'user' trouvé et affiché")
        
        # Vérifier le champ password
        password_field = driver.find_element(By.ID, "password")
        assert password_field.is_displayed()
        print("✓ Champ 'password' trouvé et affiché")
        
        # Vérifier le champ passwordConfirm
        password_confirm_field = driver.find_element(By.ID, "passwordConfirm")
        assert password_confirm_field.is_displayed()
        print("✓ Champ 'passwordConfirm' trouvé et affiché")
        
        # Vérifier le bouton submit
        submit_button = driver.find_element(By.ID, "submit")
        assert submit_button.is_displayed()
        print("✓ Bouton 'submit' trouvé et affiché")
    
    @pytest.mark.order(3)
    def test_03_fill_initialization_form(self, driver, app_config, app_session):
        """Étape 3: Remplir et soumettre le formulaire d'initialisation"""
        # Récupérer les données de configuration
        company_name = app_config['company_name']
        login = app_config['login']
        password = app_config['password']
        web_url = app_config['web_url']
        
        # Vérifier qu'on est sur la page d'initialisation, sinon y naviguer
        if "/init-app" not in driver.current_url:
            print(f"Navigation vers la page d'initialisation depuis: {driver.current_url}")
            driver.get(f"{web_url}/init-app")
        
        # Attendre que tous les éléments soient présents
        wait = WebDriverWait(driver, 10)
        
        # Attendre d'être sur la bonne page
        wait.until(lambda d: "/init-app" in d.current_url)
        print(f"✓ Sur la page d'initialisation: {driver.current_url}")
        
        # Attendre que la page soit complètement chargée en vérifiant la présence du formulaire
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
        print("✓ Formulaire d'initialisation chargé")
        
        # Remplir le formulaire - récupérer et utiliser chaque élément immédiatement
        # Champ company
        company_field = wait.until(EC.element_to_be_clickable((By.ID, "company")))
        company_field.clear()
        company_field.send_keys(company_name)
        print(f"✓ Champ 'company' rempli avec: {company_name}")
        
        # Petit délai pour s'assurer que l'action précédente est terminée
        time.sleep(0.5)
        
        # Champ user
        user_field = wait.until(EC.element_to_be_clickable((By.ID, "user")))
        user_field.clear()
        user_field.send_keys(login)
        print(f"✓ Champ 'user' rempli avec: {login}")
        
        # Petit délai pour s'assurer que l'action précédente est terminée
        time.sleep(0.5)
        
        # Champ password
        password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
        password_field.clear()
        password_field.send_keys(password)
        print("✓ Champ 'password' rempli")
        
        # Petit délai pour s'assurer que l'action précédente est terminée  
        time.sleep(0.5)
        
        # Champ passwordConfirm
        password_confirm_field = wait.until(EC.element_to_be_clickable((By.ID, "passwordConfirm")))
        password_confirm_field.clear()
        password_confirm_field.send_keys(password)
        print("✓ Champ 'passwordConfirm' rempli")
        
        # Sauvegarder l'état avant soumission
        app_session.current_user = login
        
        # Petit délai pour s'assurer que tous les champs sont bien remplis
        time.sleep(1)
        
        # Soumettre le formulaire - attendre que le bouton soit cliquable
        submit_button = wait.until(EC.element_to_be_clickable((By.ID, "submit")))
        submit_button.click()
        print("✓ Formulaire soumis")
    
    @pytest.mark.order(4)
    def test_04_verify_redirect_to_auth_after_init(self, driver, app_config, app_session):
        """Étape 4: Vérifier la redirection vers la page d'authentification après initialisation"""
        # Attendre la redirection vers la page d'authentification
        wait = WebDriverWait(driver, 15)  # Délai plus long pour l'initialisation DB
        
        try:
            # Attendre que l'URL contienne /login
            wait.until(lambda d: "/login" in d.current_url)
            print(f"✓ Redirection réussie vers: {driver.current_url}")
            
            # Marquer l'application comme initialisée
            app_session.is_initialized = True
            
            # Vérifier qu'on est bien sur la page de login
            assert "/login" in driver.current_url
            
        except Exception as e:
            print(f"❌ Erreur lors de l'attente de redirection: {e}")
            print(f"URL actuelle: {driver.current_url}")
            # Prendre une capture d'écran pour debug (optionnel)
            # driver.save_screenshot("/tmp/init_error.png")
            raise
    
    @pytest.mark.order(5)
    def test_05_verify_redirect_to_auth_page(self, driver, app_session):
        """Étape 5: Vérifier la redirection vers la page d'authentification après initialisation"""
        # Vérifier qu'on est bien sur la page de login après l'initialisation
        assert "/login" in driver.current_url, f"Attendu /login après initialisation, mais sur {driver.current_url}"
        
        # L'application est maintenant initialisée (company et user créés)
        app_session.is_initialized = True
        
        print(f"✓ Redirection réussie vers la page d'authentification: {driver.current_url}")
        print("✓ Application initialisée avec succès")
        print("✓ Company et user admin créés")
        print("✓ Page d'authentification prête")
        print("Note: Les tests de connexion sont dans login/test_login.py")
    
    @pytest.mark.order(6)
    def test_06_verify_app_initialized_on_index_access(self, driver, app_config, app_session):
        """Étape 6: Vérifier qu'un accès à l'index ne redirige plus vers init-app"""
        web_url = app_config['web_url']
        
        # Accéder à nouveau à la page d'accueil
        driver.get(web_url)
        
        # Attendre un moment pour voir si redirection
        time.sleep(3)
        
        # Vérifier qu'on ne redirige plus vers init-app
        assert "/init-app" not in driver.current_url, "L'application redirige encore vers init-app"
        
        # On devrait maintenant être redirigé vers login (car pas connecté)
        # ou rester sur l'index si l'app permet l'accès sans connexion
        current_url = driver.current_url
        print(f"✓ Accès à l'index réussi, URL actuelle: {current_url}")
        
        if "/login" in current_url:
            print("✓ Redirection vers login (comportement attendu pour app non connectée)")
        else:
            print("✓ Accès direct à l'index autorisé")
        
        # Confirmer que l'application est maintenant initialisée
        assert app_session.is_initialized, "L'état de session devrait indiquer que l'app est initialisée"