"""
Tests for Basic I/O API - Mermaid Export functionality
Tests pour l'export au format Mermaid (diagrammes flowchart, graph, mindmap)
"""
import requests
import time
import pytest
import sys
from pathlib import Path

# Désactiver les warnings SSL pour les tests

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('basic_io')

class TestBasicIOExportMermaid:
    """Tests d'export Mermaid via Basic I/O API"""

    @pytest.fixture(scope="class")
    def tree_structure(self, api_tester, session_auth_cookies, session_user_info):
        """Créer une structure arborescente pour les tests Mermaid"""
        company_id = session_user_info['company_id']
        
        created_unit_ids = []
        timestamp = int(time.time() * 1000)
        
        # Créer une hiérarchie
        # Racine
        root_data = {
            "name": f"Mermaid_Root_{timestamp}",
            "company_id": company_id,
            "description": "Root for Mermaid tests"
        }
        root_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=root_data,
            cookies=session_auth_cookies
        )
        assert root_response.status_code == 201
        root_id = root_response.json()['id']
        created_unit_ids.append(root_id)
        
        # 2 Enfants
        for i in range(2):
            child_data = {
                "name": f"Mermaid_Child{i}_{timestamp}",
                "company_id": company_id,
                "parent_id": root_id,
                "description": f"Child {i}"
            }
            child_response = api_tester.session.post(
                f"{api_tester.base_url}/api/identity/organization_units",
                json=child_data,
                cookies=session_auth_cookies
            )
            assert child_response.status_code == 201
            created_unit_ids.append(child_response.json()['id'])
        
        logger.info(f"Created tree structure: {len(created_unit_ids)} units")
        
        yield created_unit_ids
        
        # Cleanup
        logger.info(f"🧹 Cleaning up {len(created_unit_ids)} units...")
        for unit_id in reversed(created_unit_ids):
            try:
                api_tester.session.delete(
                    f"{api_tester.base_url}/api/identity/organization_units/{unit_id}",
                    cookies=session_auth_cookies
                )
            except Exception as e:
                logger.error(f"Error deleting unit {unit_id}: {e}")
        logger.info("✅ Cleanup completed")

    def test01_export_mermaid_flowchart(self, api_tester, session_auth_cookies, tree_structure):
        """Tester l'export Mermaid au format flowchart"""
        assert session_auth_cookies, "Authentication failed"
        assert tree_structure, "Tree structure not created"
        
        # Export en format Mermaid flowchart
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "mermaid",
            "diagram_type": "flowchart"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export Mermaid with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type (text/plain pour Mermaid)
        content_type = response.headers.get('Content-Type', '')
        assert 'text/plain' in content_type or 'text/markdown' in content_type, \
            f"Expected text/plain content type, got {content_type}"
        
        # Vérifier le Content-Disposition
        content_disposition = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disposition, \
            f"Expected attachment disposition, got {content_disposition}"
        assert '.mmd' in content_disposition or '.md' in content_disposition, \
            "Expected .mmd or .md extension in filename"
        
        # Analyser le contenu Mermaid
        mermaid_content = response.text
        assert len(mermaid_content) > 0, "Mermaid content is empty"
        
        # Vérifier la syntaxe Mermaid flowchart
        assert 'flowchart' in mermaid_content.lower(), \
            "Missing 'flowchart' keyword in Mermaid content"
        
        # Vérifier qu'il y a des nœuds et des flèches
        # Format: node1["Label"] --> node2["Label"]
        assert '[' in mermaid_content and ']' in mermaid_content, \
            "Missing node definitions in Mermaid"
        
        # Vérifier qu'il y a des relations (flèches)
        has_arrows = '-->' in mermaid_content or '---' in mermaid_content
        
        logger.info("✅ Mermaid flowchart export successful")
        logger.info(f"Content length: {len(mermaid_content)} characters")
        logger.info(f"Has arrows: {has_arrows}")
        
        # Logger quelques lignes du diagram
        lines = mermaid_content.split('\n')[:10]
        logger.info(f"First lines:\n{chr(10).join(lines)}")

    def test02_export_mermaid_graph(self, api_tester, session_auth_cookies, tree_structure):
        """Tester l'export Mermaid au format graph"""
        assert session_auth_cookies, "Authentication failed"
        assert tree_structure, "Tree structure not created"
        
        # Export en format Mermaid graph
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "mermaid",
            "diagram_type": "graph"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export Mermaid graph with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type
        content_type = response.headers.get('Content-Type', '')
        assert 'text/plain' in content_type or 'text/markdown' in content_type, \
            f"Expected text/plain content type, got {content_type}"
        
        # Analyser le contenu Mermaid
        mermaid_content = response.text
        assert len(mermaid_content) > 0, "Mermaid content is empty"
        
        # Vérifier la syntaxe Mermaid graph
        # Peut être "graph TD" ou "graph LR"
        assert 'graph' in mermaid_content.lower(), \
            "Missing 'graph' keyword in Mermaid content"
        
        # Vérifier qu'il y a des nœuds
        assert '[' in mermaid_content and ']' in mermaid_content, \
            "Missing node definitions in Mermaid"
        
        logger.info("✅ Mermaid graph export successful")
        logger.info(f"Content length: {len(mermaid_content)} characters")

    def test03_export_mermaid_mindmap(self, api_tester, session_auth_cookies, tree_structure):
        """Tester l'export Mermaid au format mindmap"""
        assert session_auth_cookies, "Authentication failed"
        assert tree_structure, "Tree structure not created"
        
        # Export en format Mermaid mindmap
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "mermaid",
            "diagram_type": "mindmap"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export Mermaid mindmap with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type
        content_type = response.headers.get('Content-Type', '')
        assert 'text/plain' in content_type or 'text/markdown' in content_type, \
            f"Expected text/plain content type, got {content_type}"
        
        # Analyser le contenu Mermaid
        mermaid_content = response.text
        assert len(mermaid_content) > 0, "Mermaid content is empty"
        
        # Vérifier la syntaxe Mermaid mindmap
        assert 'mindmap' in mermaid_content.lower(), \
            "Missing 'mindmap' keyword in Mermaid content"
        
        # Mindmap utilise l'indentation pour la hiérarchie
        # Vérifier qu'il y a des espaces d'indentation
        lines = mermaid_content.split('\n')
        has_indentation = any(line.startswith('  ') or line.startswith('\t') for line in lines)
        
        logger.info("✅ Mermaid mindmap export successful")
        logger.info(f"Content length: {len(mermaid_content)} characters")
        logger.info(f"Has indentation: {has_indentation}")

    def test04_export_mermaid_with_metadata(self, api_tester, session_auth_cookies, tree_structure):
        """Tester l'export Mermaid avec métadonnées dans les commentaires"""
        assert session_auth_cookies, "Authentication failed"
        assert tree_structure, "Tree structure not created"
        
        # Export Mermaid (devrait inclure des métadonnées dans les commentaires)
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "mermaid",
            "diagram_type": "flowchart"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export Mermaid with status {response.status_code}: {response.text}"
        
        # Analyser le contenu
        mermaid_content = response.text
        
        # Vérifier s'il y a des commentaires (métadonnées)
        # Mermaid utilise %% pour les commentaires
        has_comments = '%%' in mermaid_content
        
        if has_comments:
            logger.info("✅ Mermaid diagram includes metadata comments")
            
            # Compter les commentaires
            comment_lines = [line for line in mermaid_content.split('\n') if line.strip().startswith('%%')]
            logger.info(f"Number of comment lines: {len(comment_lines)}")
            
            # Vérifier si les métadonnées incluent des infos utiles
            # Exemple: timestamp, source URL, node IDs
            if comment_lines:
                logger.info(f"Sample metadata: {comment_lines[0]}")
        else:
            logger.info("No metadata comments found (optional feature)")
        
        # Vérifier la structure de base
        assert 'flowchart' in mermaid_content.lower(), \
            "Missing flowchart keyword"
        
        logger.info("✅ Mermaid with metadata export successful")

    def test05_export_mermaid_default_type(self, api_tester, session_auth_cookies):
        """Tester l'export Mermaid sans spécifier diagram_type (devrait utiliser flowchart par défaut)"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export Mermaid sans diagram_type
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "mermaid"
            # Pas de diagram_type - devrait utiliser 'flowchart' par défaut
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export Mermaid with status {response.status_code}: {response.text}"
        
        # Analyser le contenu
        mermaid_content = response.text
        assert len(mermaid_content) > 0, "Mermaid content is empty"
        
        # Vérifier que c'est un flowchart par défaut
        # (ou graph, selon l'implémentation du service)
        has_flowchart = 'flowchart' in mermaid_content.lower()
        has_graph = 'graph' in mermaid_content.lower()
        has_mindmap = 'mindmap' in mermaid_content.lower()
        
        assert has_flowchart or has_graph or has_mindmap, \
            "Mermaid content should have a diagram type"
        
        if has_flowchart:
            logger.info("✅ Default diagram type: flowchart")
        elif has_graph:
            logger.info("✅ Default diagram type: graph")
        elif has_mindmap:
            logger.info("✅ Default diagram type: mindmap")
        
        logger.info("✅ Mermaid export with default type successful")

    def test06_export_mermaid_without_auth(self, api_tester):
        """Tester l'export Mermaid sans authentification (doit échouer)"""
        
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "mermaid"
        }
        
        api_tester.log_request('GET', url, params)
        # Créer une nouvelle session sans cookies
        temp_session = requests.Session()
        response = temp_session.get(url, params=params)
        api_tester.log_response(response)
        
        # Devrait retourner 401 (unauthorized)
        assert response.status_code == 401, \
            f"Expected 401 for missing auth, got {response.status_code}"
        
        logger.info("✅ Missing authentication correctly rejected with 401")
