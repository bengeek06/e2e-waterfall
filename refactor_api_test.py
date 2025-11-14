#!/usr/bin/env python3
"""
Refactor individual API test file to use centralized fixtures
"""
import sys
import re

def refactor_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # 1. Supprimer les imports inutiles (mais garder ceux nécessaires)
    # Note: on garde requests et time s'ils sont utilisés ailleurs dans le code
    content = re.sub(r'^import urllib3\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'^urllib3\.disable_warnings.*\n', '', content, flags=re.MULTILINE)
    
    # 2. Supprimer la classe BasicIOAPITester/StorageAPITester/etc.
    # Pattern: depuis "class XxxAPITester:" jusqu'à la prochaine classe
    pattern = r'\n\nclass \w*APITester:.*?(?=\n\nclass Test|\n\n@pytest\.mark|\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 3. Supprimer les fixtures class-scoped api_tester
    pattern = r'    @pytest\.fixture\(scope="class"\)\s+def api_tester\(self, app_config\):\s+return \w*APITester\(app_config\)\s*\n'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 4. Supprimer les fixtures class-scoped auth_token (plus complexe car multi-lignes)
    pattern = r'    @pytest\.fixture\(scope="class"\)\s+def auth_token\(.*?\n(?:.*?\n)*?        return .*?\n\s*\n'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 5. Supprimer les fixtures class-scoped company_id
    pattern = r'    @pytest\.fixture\(scope="class"\)\s+def company_id\(.*?\n(?:.*?\n)*?        return .*?\n\s*\n'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 6. Remplacer auth_token par session_auth_cookies dans les signatures
    content = re.sub(r'\(self, api_tester, auth_token\)', 
                     '(self, api_tester, session_auth_cookies)', content)
    content = re.sub(r'\(self, api_tester, auth_token, company_id\)', 
                     '(self, api_tester, session_auth_cookies, session_user_info)', content)
    content = re.sub(r'\(self, api_tester, company_id\)', 
                     '(self, api_tester, session_user_info)', content)
    
    # 7. Remplacer cookies=auth_token par cookies=session_auth_cookies
    content = content.replace('cookies=auth_token', 'cookies=session_auth_cookies')
    
    # 8. Ajouter extraction de company_id au début des tests qui en ont besoin
    # Pattern: trouve les tests qui utilisent company_id mais n'ont pas session_user_info
    if 'session_user_info' in content and 'company_id' in content:
        # Remplacer les utilisations de company_id directement
        # On cherche les méthodes qui ont session_user_info en paramètre
        def add_company_id_extraction(match):
            method = match.group(0)
            if 'session_user_info' in method and 'company_id =' not in method:
                # Insérer extraction après la docstring
                lines = method.split('\n')
                # Trouver la fin de la docstring
                in_docstring = False
                insert_index = 1
                for i, line in enumerate(lines):
                    if '"""' in line:
                        if not in_docstring:
                            in_docstring = True
                        else:
                            insert_index = i + 1
                            break
                
                # Insérer extraction
                lines.insert(insert_index, '        company_id = session_user_info[\"company_id\"]')
                return '\n'.join(lines)
            return method
        
        content = re.sub(r'    def test\d+_.*?(?=\n    def test|\n\nclass |\Z)', 
                        add_company_id_extraction, content, flags=re.DOTALL)
    
    # 9. Nettoyer les lignes vides multiples
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✓ Refactored {filepath}")
        return True
    else:
        print(f"- No changes for {filepath}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python refactor_api_test.py <test_file.py>")
        sys.exit(1)
    
    refactor_file(sys.argv[1])
