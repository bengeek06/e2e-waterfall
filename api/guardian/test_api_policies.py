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

class TestAPIPolicies:
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

    def test02_api_check_get_policies(self, api_tester, auth_token):
        """Tester la vérification de policies avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for policies test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        
        response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/policies",
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
            print(f"Policies result: {result}")
        else:
            print(f"Policies check response: {response.status_code} - {response.text}")

    def test03_api_check_post_policies(self, api_tester, auth_token):
        """Tester la vérification de policies avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for policies test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        params = {
            "name": "test_policy"
        }

        response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            cookies=cookies_dict,
            json=params
        )

        print(f"Check permission response status: {response.status_code}")
        print(f"Check permission response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API peut retourner 201 Created ou 400 si les paramètres sont incorrects
        assert response.status_code == 201, f"Expected 201 Created for policies check, got {response.status_code}: {response.text}"

        if response.status_code == 201:
            result = response.json()
            assert "id" in result, "Expected policy ID in response"
            api_tester.created_policy_id = result["id"]
            print(f"Policy created successfully with ID: {api_tester.created_policy_id}")
        else:
            print(f"Policy creation failed: {response.status_code} - {response.text}")

    def test04_api_check_patch_policies(self, api_tester, auth_token):
        """Tester la mise à jour de policies avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for policies test"
        assert hasattr(api_tester, 'created_policy_id'), "No policy ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        params = {
            "name": "patched_test_policy"
        }

        print(f"Attempting to update policy with ID: {api_tester.created_policy_id}")

        response = api_tester.session.patch(
            f"{api_tester.base_url}/api/guardian/policies/{api_tester.created_policy_id}",
            cookies=cookies_dict,
            json=params
        )

        print(f"Update policy response status: {response.status_code}")
        print(f"Update policy response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API devrait retourner 200 OK pour une mise à jour réussie
        assert response.status_code == 200, f"Expected 200 OK for policy update, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            result = response.json()
            assert result.get("name") == "patched_test_policy", "Policy name was not updated correctly"
            print(f"Policy updated successfully: {result}")
        else:
            print(f"Policy update response: {response.status_code} - {response.text}")

    def test05_api_check_put_policies(self, api_tester, auth_token):
        """Tester la mise à jour de policies avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for policies test"
        assert hasattr(api_tester, 'created_policy_id'), "No policy ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        params = {
            "name": "updated_test_policy"
        }

        print(f"Attempting to update policy with ID: {api_tester.created_policy_id}")

        response = api_tester.session.put(
            f"{api_tester.base_url}/api/guardian/policies/{api_tester.created_policy_id}",
            cookies=cookies_dict,
            json=params
        )

        print(f"Update policy response status: {response.status_code}")
        print(f"Update policy response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API devrait retourner 200 OK pour une mise à jour réussie
        assert response.status_code == 200, f"Expected 200 OK for policy update, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            result = response.json()
            assert result.get("name") == "updated_test_policy", "Policy name was not updated correctly"
            print(f"Policy updated successfully: {result}")
        else:
            print(f"Policy update response: {response.status_code} - {response.text}")


    def test06_api_check_post_new_permissions_policy(self, api_tester, auth_token):
        assert auth_token is not None, "No auth cookies available for policies test"
        assert hasattr(api_tester, 'created_policy_id'), "No policy ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })

        permissions_response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/permissions",
            cookies=cookies_dict
        )
        
        params = {
            "permission_id": permissions_response.json()[0]['id']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies/{api_tester.created_policy_id}/permissions",
            cookies=cookies_dict,
            json=params
        )
        
        print(f"Add permission to policy response status: {response.status_code}")
        print(f"Add permission to policy response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API devrait retourner 200 OK ou 201 Created pour une mise à jour réussie
        assert response.status_code in [200, 201], f"Expected 200 OK or 201 Created for adding permission to policy, got {response.status_code}: {response.text}"
        if response.status_code in [200, 201]:
            result = response.json()
            assert "id" in result, "Expected permission relation ID in response"
            assert "permission_id" in result, "Expected permission_id in response"
            print(f"Permission added to policy successfully: {result}")
            # Stocker l'ID de la relation pour référence, mais on utilisera permission_id pour la suppression
            api_tester.created_permission_relation_id = result["id"]
            api_tester.added_permission_id = result["permission_id"]
        else:
            print(f"Add permission to policy response: {response.status_code} - {response.text}")


    def test07_api_check_get_permissions_policy(self, api_tester, auth_token):
        assert auth_token is not None, "No auth cookies available for policies test"
        assert hasattr(api_tester, 'created_policy_id'), "No policy ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })

        response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/policies/{api_tester.created_policy_id}/permissions",
            cookies=cookies_dict
        )

        print(f"Get permissions of policy response status: {response.status_code}")
        print(f"Get permissions of policy response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API devrait retourner 200 OK pour une requête réussie
        assert response.status_code == 200, f"Expected 200 OK for getting permissions of policy, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, list), "Expected a list of permissions"
            print(f"Permissions of policy retrieved successfully: {result}")
        else:
            print(f"Get permissions of policy response: {response.status_code} - {response.text}")

    def test08_api_check_delete_permissions_policy(self, api_tester, auth_token):
        assert auth_token is not None, "No auth cookies available for policies test"
        assert hasattr(api_tester, 'created_policy_id'), "No policy ID available from previous test"
        
        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        # Récupérer la liste des permissions de la politique pour obtenir le permission_id correct
        permissions_response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/policies/{api_tester.created_policy_id}/permissions",
            cookies=cookies_dict
        )
        
        assert permissions_response.status_code == 200, f"Failed to get permissions: {permissions_response.text}"
        permissions = permissions_response.json()
        assert len(permissions) > 0, "No permissions found in policy"
        
        # Utiliser l'ID de la première permission trouvée
        permission_to_delete_id = permissions[0]['id']
        
        print(f"Attempting to delete permission with ID: {permission_to_delete_id} from policy ID: {api_tester.created_policy_id}")
        response = api_tester.session.delete(
            f"{api_tester.base_url}/api/guardian/policies/{api_tester.created_policy_id}/permissions/{permission_to_delete_id}",
            cookies=cookies_dict
        )
        print(f"Delete permission from policy response status: {response.status_code}")
        print(f"Delete permission from policy response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")
        
        # L'API devrait retourner 204 No Content pour une suppression réussie
        assert response.status_code == 204, f"Expected 204 No Content for deleting permission from policy, got {response.status_code}: {response.text}"
        if response.status_code == 204:
            print(f"Permission deleted from policy successfully: ID {permission_to_delete_id}")
        else:
            print(f"Delete permission from policy response: {response.status_code} - {response.text}")

    def test09_api_check_delete_policies(self, api_tester, auth_token):
        """Tester la suppression de policies avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for policies test"
        assert hasattr(api_tester, 'created_policy_id'), "No policy ID available from previous test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })

        print(f"Attempting to delete policy with ID: {api_tester.created_policy_id}")

        response = api_tester.session.delete(
            f"{api_tester.base_url}/api/guardian/policies/{api_tester.created_policy_id}",
            cookies=cookies_dict
        )

        print(f"Delete policy response status: {response.status_code}")
        print(f"Delete policy response content: {response.text}")
        print(f"Request URL: {response.url}")
        print(f"Request cookies sent: {response.request.headers.get('Cookie', 'No cookies')}")

        # L'API peut retourner 204 No Content pour une suppression réussie ou 404 si la policy n'existe plus
        assert response.status_code in [204, 404], f"Expected 204 No Content or 404 Not Found for policy deletion, got {response.status_code}: {response.text}"

        if response.status_code == 204:
            print(f"Policy deleted successfully: ID {api_tester.created_policy_id}")
            del api_tester.created_policy_id  # Nettoyer l'ID de la politique supprimée
        elif response.status_code == 404:
            print(f"Policy not found (already deleted?): ID {api_tester.created_policy_id}")
            # Nettoyer l'ID même si la policy n'existe plus
            if hasattr(api_tester, 'created_policy_id'):
                del api_tester.created_policy_id
        else:
            print(f"Policy deletion response: {response.status_code} - {response.text}")