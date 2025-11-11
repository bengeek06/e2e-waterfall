#!/usr/bin/env python3
"""
Script pour refactoriser automatiquement les tests API pour utiliser les fixtures centralisées
"""
import re
import sys
from pathlib import Path

def refactor_test_file(filepath: Path):
    """Refactoriser un fichier de test pour utiliser les fixtures centralisées"""
    
    print(f"Processing {filepath.name}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Supprimer la classe APITester locale (BasicIOAPITester, StorageAPITester, etc.)
    # Trouver la classe et la supprimer jusqu'à la prochaine classe ou EOF
    pattern = r'class \w*APITester.*?(?=\n@pytest\.mark|nclass Test|\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 2. Supprimer les fixtures locales api_tester et auth_token
    # Supprimer @pytest.fixture(scope="class") def api_tester...
    pattern = r'    @pytest\.fixture\(scope="class"\)\s+def api_tester\(self, app_config\):.*?(?=\n    @pytest\.fixture|\n    def test)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Supprimer @pytest.fixture(scope="class") def auth_token...
    pattern = r'    @pytest\.fixture\(scope="class"\)\s+def auth_token\(.*?\):.*?(?=\n    @pytest\.fixture|\n    def test)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 3. Remplacer auth_token par session_auth_cookies dans les signatures
    content = re.sub(r'def test\d+_\w+\(self, api_tester, auth_token\)',
                     r'def test\d+_\w+(self, api_tester, session_auth_cookies)',
                     content)
    
    # 4. Remplacer cookies=auth_token par cookies=session_auth_cookies
    content = content.replace('cookies=auth_token', 'cookies=session_auth_cookies')
    
    # 5. Remplacer assert auth_token par assert session_auth_cookies
    content = content.replace('assert auth_token', 'assert session_auth_cookies')
    
    # 6. Nettoyer les lignes vides en trop
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    # 7. Vérifier que les imports nécessaires sont présents
    has_requests = 'import requests' in content
    has_time = 'import time' in content
    needs_requests = 'requests.Session()' in content or 'requests.get(' in content or 'requests.post(' in content
    needs_time = 'time.time()' in content or 'time.sleep(' in content
    
    # Ajouter les imports manquants si nécessaire
    import_section = content.split('from conftest import')[0]
    if needs_requests and not has_requests:
        import_section += 'import requests\n'
    if needs_time and not has_time:
        import_section += 'import time\n'
    
    if needs_requests or needs_time:
        content = import_section + 'from conftest import' + content.split('from conftest import')[1]
    
    # Sauvegarder seulement si modifié
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✓ Refactored {filepath.name}")
        return True
    else:
        print(f"  - No changes needed for {filepath.name}")
        return False

def main():
    test_dir = Path(__file__).parent / 'api' / 'basic_io'
    skip_files = {'test_basic_io_health.py', 'test_basic_io_import_tree.py'}
    
    refactored_count = 0
    for test_file in sorted(test_dir.glob('test_basic_io_*.py')):
        if test_file.name in skip_files:
            print(f"Skipping {test_file.name} (already refactored)")
            continue
        
        if refactor_test_file(test_file):
            refactored_count += 1
    
    print(f"\n✓ Refactored {refactored_count} files")

if __name__ == '__main__':
    main()
