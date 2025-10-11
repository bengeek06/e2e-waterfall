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

class TestAPIRoles:
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

    def test01_api_guardian_authentication(self, api_tester, auth_token):
        """Vérifier que l'API Guardian authentifie correctement les requêtes"""
        assert auth_token is not None, "No auth cookies available for guardian test"
        
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
        
        # Tester l'endpoint de version/health de Guardian avec cookies explicites
        response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/version",
            cookies=cookies_dict
        )
        
        print(f"Guardian version response status: {response.status_code}")
        print(f"Guardian version response headers: {dict(response.headers)}")
        print(f"Guardian version response content: {response.text}")
        
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

    def test02_api_check_get_roles(self, api_tester, auth_token):
        """Tester la vérification de roles avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for roles test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        
        response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/roles",
            cookies=cookies_dict
        )
        
        print(f"Check permission response status: {response.status_code}")
        print(f"Check permission response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")
        
        # L'API peut retourner 200 avec permission granted/denied ou 400 si les paramètres sont incorrects
        assert response.status_code in [200, 400, 403, 404], f"Unexpected status: {response.status_code} - {response.text}"
        assert response.status_code == 200, f"Expected 200 OK for policies check, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            result = response.json()
            print(f"Roles result: {result}")
        else:
            print(f"Roles check response: {response.status_code} - {response.text}")

    def test03_api_check_post_roles(self, api_tester, auth_token):
        """Tester la vérification de roles avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for roles test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        params = {
            "name": "test_role"
        }

        response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            cookies=cookies_dict,
            json=params
        )

        print(f"Check permission response status: {response.status_code}")
        print(f"Check permission response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API peut retourner 201 Created ou 400 si les paramètres sont incorrects
        assert response.status_code == 201, f"Expected 201 Created for roles check, got {response.status_code}: {response.text}"

        if response.status_code == 201:
            result = response.json()
            assert "id" in result, "Expected role ID in response"
            api_tester.created_role_id = result["id"]
            print(f"Role created successfully with ID: {api_tester.created_role_id}")
        else:
            print(f"Role creation failed: {response.status_code} - {response.text}")

    def test04_api_check_patch_roles(self, api_tester, auth_token):
        """Tester la mise à jour de roles avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for roles test"
        assert hasattr(api_tester, 'created_role_id'), "No role ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        params = {
            "name": "patched_test_role"
        }

        print(f"Attempting to update role with ID: {api_tester.created_role_id}")

        response = api_tester.session.patch(
            f"{api_tester.base_url}/api/guardian/roles/{api_tester.created_role_id}",
            cookies=cookies_dict,
            json=params
        )

        print(f"Update role response status: {response.status_code}")
        print(f"Update role response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API devrait retourner 200 OK pour une mise à jour réussie
        assert response.status_code == 200, f"Expected 200 OK for role update, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            result = response.json()
            assert result.get("name") == "patched_test_role", "Role name was not updated correctly"
            print(f"Role updated successfully: {result}")
        else:
            print(f"Role update response: {response.status_code} - {response.text}")

    def test05_api_check_put_roles(self, api_tester, auth_token):
        """Tester la mise à jour de roles avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for roles test"
        assert hasattr(api_tester, 'created_role_id'), "No role ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        params = {
            "name": "updated_test_role"
        }

        print(f"Attempting to update role with ID: {api_tester.created_role_id}")

        response = api_tester.session.put(
            f"{api_tester.base_url}/api/guardian/roles/{api_tester.created_role_id}",
            cookies=cookies_dict,
            json=params
        )

        print(f"Update role response status: {response.status_code}")
        print(f"Update role response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API devrait retourner 200 OK pour une mise à jour réussie
        assert response.status_code == 200, f"Expected 200 OK for role update, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            result = response.json()
            assert result.get("name") == "updated_test_role", "Role name was not updated correctly"
            print(f"Role updated successfully: {result}")
        else:
            print(f"Role update response: {response.status_code} - {response.text}")


    def test06_api_check_post_new_policy_roles(self, api_tester, auth_token):
        """Tester l'ajout d'une policy à un role avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for roles test"
        assert hasattr(api_tester, 'created_role_id'), "No role ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        policy_response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/policies",
            cookies=cookies_dict
        )
        
        params = {
            "policy_id": policy_response.json()[0]['id']
        }
        
        print(f"Attempting to add policy to role with ID: {api_tester.created_role_id}")
        print(f"Using policy ID: {params['policy_id']}")
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles/{api_tester.created_role_id}/policies",
            cookies=cookies_dict,
            json=params
        )
        print(f"Add policy to role response status: {response.status_code}")
        print(f"Add policy to role response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")
        
        # L'API peut retourner 200 OK ou 400 si les paramètres sont incorrects
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        assert response.status_code == 200, f"Expected 200 OK for adding policy to role, got {response.status_code}: {response.text}"
        
        if response.status_code in [200, 201]:
            result = response.json()
            assert "id" in result, "Expected policy ID in response"
            print(f"Policy added to role successfully: {result}")
            api_tester.created_policy_id = result["id"]
        else:
            print(f"Add policy to role response: {response.status_code} - {response.text}")

    def test07_api_check_get_policy_roles(self, api_tester, auth_token):
        assert auth_token is not None, "No auth cookies available for policies test"
        assert hasattr(api_tester, 'created_role_id'), "No role ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })

        response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/roles/{api_tester.created_role_id}/policies",
            cookies=cookies_dict
        )

        print(f"Get policies of role response status: {response.status_code}")
        print(f"Get policies of role response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API devrait retourner 200 OK pour une requête réussie
        assert response.status_code == 200, f"Expected 200 OK for getting policies of role, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, list), "Expected a list of policies"
            print(f"Policies of role retrieved successfully: {result}")
        else:
            print(f"Get policies of role response: {response.status_code} - {response.text}")

    def test08_api_check_delete_policy_roles(self, api_tester, auth_token):
        assert auth_token is not None, "No auth cookies available for policies test"
        assert hasattr(api_tester, 'created_policy_id'), "No policy ID available from previous test"
        assert hasattr(api_tester, 'created_role_id'), "No role ID available from previous test"
        
        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        # Récupérer la liste des politiques du role pour obtenir le permission_id correct
        policies_response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/roles/{api_tester.created_role_id}/policies",
            cookies=cookies_dict
        )

        assert policies_response.status_code == 200, f"Failed to get policies: {policies_response.text}"
        policies = policies_response.json()
        assert len(policies) > 0, "No policies found for role"

        # Utiliser l'ID de la première politique trouvée
        policy_to_delete_id = policies[0]['id']

        print(f"Attempting to delete policy with ID: {policy_to_delete_id} from role ID: {api_tester.created_role_id}")
        response = api_tester.session.delete(
            f"{api_tester.base_url}/api/guardian/roles/{api_tester.created_role_id}/policies/{policy_to_delete_id}",
            cookies=cookies_dict
        )
        print(f"Delete policy from role response status: {response.status_code}")
        print(f"Delete policy from role response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")
        
        # L'API devrait retourner 204 No Content pour une suppression réussie
        assert response.status_code == 204, f"Expected 204 No Content for deleting policy from role, got {response.status_code}: {response.text}"
        if response.status_code == 204:
            print(f"Policy deleted from role successfully: ID {policy_to_delete_id}")
        else:
            print(f"Delete policy from role response: {response.status_code} - {response.text}")


    def test09_api_check_delete_roles(self, api_tester, auth_token):
        """Tester la suppression de roles avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for roles test"
        assert hasattr(api_tester, 'created_role_id'), "No role ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })

        print(f"Attempting to delete role with ID: {api_tester.created_role_id}")

        response = api_tester.session.delete(
            f"{api_tester.base_url}/api/guardian/roles/{api_tester.created_role_id}",
            cookies=cookies_dict
        )

        print(f"Delete role response status: {response.status_code}")
        print(f"Delete role response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API peut retourner 204 No Content pour une suppression réussie ou 404 si le rôle n'existe plus
        assert response.status_code in [204, 404], f"Expected 204 No Content or 404 Not Found for role deletion, got {response.status_code}: {response.text}"

        if response.status_code == 204:
            print(f"Role deleted successfully: ID {api_tester.created_role_id}")
            del api_tester.created_role_id  # Nettoyer l'ID du rôle supprimé
        elif response.status_code == 404:
            print(f"Role not found (already deleted?): ID {api_tester.created_role_id}")
            # Nettoyer l'ID même si le rôle n'existe plus
            if hasattr(api_tester, 'created_role_id'):
                del api_tester.created_role_id
        else:
            print(f"Role deletion response: {response.status_code} - {response.text}")