import requests
import time
import pytest

class APITester:
    def __init__(self, app_config):
        self.session = requests.Session()
        self.base_url = app_config['web_url']
        # Ignorer les certificats auto-signés pour les tests
        self.session.verify = False
        self.auth_cookies = None
        
    def set_auth_cookies(self, cookies):
        """Définir les cookies d'authentification"""
        self.auth_cookies = cookies
        # Forcer l'ajout des cookies à la session
        for cookie in cookies:
            self.session.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
        
    def wait_for_api(self, endpoint: str, timeout: int = 10) -> bool:
        """Attendre qu'une API soit disponible"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                print(f"wait_for_api - Status: {response.status_code}, Response: {response.text[:100]}...")
                if response.status_code == 200:
                    return True
                elif response.status_code in [401, 403]:
                    print(f"Authentication issue detected: {response.status_code}")
                    return False  # Ne pas continuer si c'est un problème d'auth
            except requests.exceptions.RequestException as e:
                print(f"Request exception: {e}")
                pass
            time.sleep(2)
        return False

class TestAPIUsers:
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return APITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification"""
        # Attendre que l'API auth soit prête
        assert api_tester.wait_for_api("/api/auth/version"), "API Auth not ready"
        
        # Créer un utilisateur de test et s'authentifier
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            # Retourner les cookies de réponse pour avoir accès aux deux tokens
            return response.cookies
        return None

    def test01_api_identity_authentication(self, api_tester, auth_token):
        """Vérifier que l'API Identity authentifie correctement les requêtes"""
        assert auth_token is not None, "No auth cookies available for identity test"

        # Utiliser la nouvelle méthode pour définir les cookies
        api_tester.set_auth_cookies(auth_token)
        
        print(f"Available auth cookies: {list(auth_token.keys())}")
        
        # Diagnostiquer les cookies
        access_token = auth_token.get('access_token')
        refresh_token = auth_token.get('refresh_token')
        print(f"Access token: {access_token[:50] if access_token else None}...")
        print(f"Refresh token: {refresh_token[:50] if refresh_token else None}...")
        
        # Méthode alternative : envoyer les cookies explicitement dans la requête
        cookies_dict = {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        
        # Tester l'endpoint de version/health de Identity avec cookies explicites
        response = api_tester.session.get(
            f"{api_tester.base_url}/api/identity/version",
            cookies=cookies_dict
        )

        print(f"Identity version response status: {response.status_code}")
        print(f"Identity version response headers: {dict(response.headers)}")
        print(f"Identity version response content: {response.text}")

        # Vérifier les cookies envoyés dans la requête
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")
        
        # L'authentification fonctionne si on obtient une réponse de permissions (404) 
        # plutôt qu'une erreur d'authentification (401)
        assert response.status_code in [200, 404], f"Expected 200 or 404 (permission denied), got {response.status_code}: {response.text}"
        
        if response.status_code == 404:
            error_response = response.json()
            assert "Access denied" in error_response.get("error", ""), "Expected permission error"
            print("✅ Authentication successful - Permission system is working")
        else:
            version_info = response.json()
            assert "version" in version_info, "Version info missing in response"
            print(f"✅ Guardian API Version: {version_info['version']}")
            
        # Sauvegarder la méthode de cookies pour les autres tests
        api_tester.cookies_dict = cookies_dict

    def test02_api_identity_get_user(self, api_tester):
        """Vérifier l'accès aux informations utilisateur via l'API Identity"""
        assert hasattr(api_tester, 'cookies_dict'), "Authentication cookies not set from previous test"
        
        response = api_tester.session.get(
            f"{api_tester.base_url}/api/identity/users",
            cookies=api_tester.cookies_dict
        )
        
        print(f"User info response status: {response.status_code}")
        print(f"User info response content: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        user_info = response.json()[0]  # Supposons que la réponse est une liste d'utilisateurs
        assert "email" in user_info, "Email not found in user info"
        print(f"✅ User email: {user_info['email']}")
        api_tester.user_id = user_info['id']
    
    def test03_api_get_user_roles(self, api_tester):
        """Vérifier l'accès aux rôles utilisateur via l'API Identity"""
        assert hasattr(api_tester, 'cookies_dict'), "Authentication cookies not set from previous test"
        assert hasattr(api_tester, 'user_id'), "User ID not set from previous test"
        
        response = api_tester.session.get(
            f"{api_tester.base_url}/api/identity/users/{api_tester.user_id}/roles",
            cookies=api_tester.cookies_dict
        )
        
        print(f"User roles response status: {response.status_code}")
        print(f"User roles response content: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        roles_response = response.json()
        assert isinstance(roles_response, dict), "Roles response is not a dictionary"
        assert "roles" in roles_response, "No 'roles' key found in response"
        
        roles_list = roles_response["roles"]
        assert isinstance(roles_list, list), "Roles is not a list"
        
        if len(roles_list) > 0:
            # Vérifier la structure du premier rôle
            first_role = roles_list[0]
            required_fields = ['id', 'user_id', 'role_id', 'company_id', 'created_at', 'updated_at']
            for field in required_fields:
                assert field in first_role, f"Missing field '{field}' in role data"
            
            print(f"✅ User roles retrieved successfully: {len(roles_list)} role(s)")
            print(f"   First role ID: {first_role['id']}")
        else:
            print("✅ User has no roles assigned")
        
        # Sauvegarder les rôles pour d'éventuels tests ultérieurs
        api_tester.user_roles = roles_list
        