# TODO - Project Service Tests

**Date de création**: 2025-11-12  
**Service**: Project Service  
**Spec**: `.spec/project_api.yml`

---

## Progression Globale

**Tests implémentés**: 3/100+ (3%)  
**Statut**: 🚀 Démarrage - Tests système créés

---

## 1. Endpoints Système ✅ (3/3)

- [x] `test01_health_check` - GET /health
- [x] `test02_version_endpoint` - GET /version
- [x] `test03_config_endpoint` - GET /config

**Fichier**: `test_api_system.py`  
**Statut**: ✅ Implémenté (en attente du service)

---

## 2. Endpoints Projets 🚧 (0/10)

### CRUD de base
- [ ] `test01_list_projects` - GET /projects
- [ ] `test02_create_project` - POST /projects
- [ ] `test03_get_project` - GET /projects/{id}
- [ ] `test04_update_project_put` - PUT /projects/{id}
- [ ] `test05_update_project_patch` - PATCH /projects/{id}
- [ ] `test06_delete_project` - DELETE /projects/{id}

### Métadonnées et historique
- [ ] `test07_get_project_metadata` - GET /projects/{id}/metadata
- [ ] `test08_get_project_history` - GET /projects/{id}/history

### Cycle de vie
- [ ] `test09_archive_project` - POST /projects/{id}/archive
- [ ] `test10_restore_project` - POST /projects/{id}/restore

**Fichier à créer**: `test_api_projects.py`

---

## 3. Endpoints Membres 🚧 (0/6)

- [ ] `test01_list_members` - GET /projects/{id}/members
- [ ] `test02_add_member` - POST /projects/{id}/members
- [ ] `test03_get_member` - GET /projects/{id}/members/{user_id}
- [ ] `test04_update_member_put` - PUT /projects/{id}/members/{user_id}
- [ ] `test05_update_member_patch` - PATCH /projects/{id}/members/{user_id}
- [ ] `test06_remove_member` - DELETE /projects/{id}/members/{user_id}

**Fichier à créer**: `test_api_members.py`

---

## 4. Endpoints Milestones 🚧 (0/5)

- [ ] `test01_list_milestones` - GET /projects/{id}/milestones
- [ ] `test02_create_milestone` - POST /projects/{id}/milestones
- [ ] `test03_get_milestone` - GET /projects/{id}/milestones/{mid}
- [ ] `test04_update_milestone` - PUT /projects/{id}/milestones/{mid}
- [ ] `test05_delete_milestone` - DELETE /projects/{id}/milestones/{mid}

**Fichier à créer**: `test_api_milestones.py`

---

## 5. Endpoints Deliverables 🚧 (0/5)

- [ ] `test01_list_deliverables` - GET /projects/{id}/deliverables
- [ ] `test02_create_deliverable` - POST /projects/{id}/deliverables
- [ ] `test03_get_deliverable` - GET /projects/{id}/deliverables/{did}
- [ ] `test04_update_deliverable` - PUT /projects/{id}/deliverables/{did}
- [ ] `test05_delete_deliverable` - DELETE /projects/{id}/deliverables/{did}

**Fichier à créer**: `test_api_deliverables.py`

---

## 6. Associations Milestone-Deliverable 🚧 (0/3)

- [ ] `test01_list_milestone_deliverables` - GET /projects/{id}/milestones/{mid}/deliverables
- [ ] `test02_associate_deliverable` - POST /projects/{id}/milestones/{mid}/deliverables
- [ ] `test03_dissociate_deliverable` - DELETE /projects/{id}/milestones/{mid}/deliverables/{did}

**Fichier à créer**: `test_api_milestone_deliverables.py`

---

## 7. RBAC - Rôles 🚧 (0/6)

- [ ] `test01_list_roles` - GET /projects/{id}/roles
- [ ] `test02_create_role` - POST /projects/{id}/roles
- [ ] `test03_get_role` - GET /projects/{id}/roles/{rid}
- [ ] `test04_update_role` - PUT /projects/{id}/roles/{rid}
- [ ] `test05_delete_role` - DELETE /projects/{id}/roles/{rid}
- [ ] `test06_verify_default_roles` - Vérifier owner/validator/contributor/viewer

**Fichier à créer**: `test_api_roles.py`

---

## 8. RBAC - Politiques 🚧 (0/5)

- [ ] `test01_list_policies` - GET /projects/{id}/policies
- [ ] `test02_create_policy` - POST /projects/{id}/policies
- [ ] `test03_get_policy` - GET /projects/{id}/policies/{pid}
- [ ] `test04_update_policy` - PUT /projects/{id}/policies/{pid}
- [ ] `test05_delete_policy` - DELETE /projects/{id}/policies/{pid}

**Fichier à créer**: `test_api_policies.py`

---

## 9. RBAC - Permissions 🚧 (0/2)

- [ ] `test01_list_permissions` - GET /projects/{id}/permissions
- [ ] `test02_verify_predefined_permissions` - Vérifier read_files, write_files, etc.

**Fichier à créer**: `test_api_permissions.py`

---

## 10. RBAC - Associations 🚧 (0/6)

### Role-Policy
- [ ] `test01_list_role_policies` - GET /projects/{id}/roles/{rid}/policies
- [ ] `test02_assign_policy_to_role` - POST /projects/{id}/roles/{rid}/policies
- [ ] `test03_remove_policy_from_role` - DELETE /projects/{id}/roles/{rid}/policies/{pid}

### Policy-Permission
- [ ] `test04_list_policy_permissions` - GET /projects/{id}/policies/{pid}/permissions
- [ ] `test05_assign_permission` - POST /projects/{id}/policies/{pid}/permissions
- [ ] `test06_remove_permission` - DELETE /projects/{id}/policies/{pid}/permissions/{perm_id}

**Fichier à créer**: `test_api_rbac_associations.py`

---

## 11. Contrôle d'accès - Fichiers 🚧 (0/4)

- [ ] `test01_check_file_access_allowed` - POST /check-file-access (allowed)
- [ ] `test02_check_file_access_denied` - POST /check-file-access (denied)
- [ ] `test03_check_file_access_batch` - POST /check-file-access-batch
- [ ] `test04_check_file_access_not_member` - Utilisateur non membre

**Fichier à créer**: `test_api_file_access.py`

---

## 12. Contrôle d'accès - Projets 🚧 (0/4)

- [ ] `test01_check_project_access_read` - POST /check-project-access (read)
- [ ] `test02_check_project_access_write` - POST /check-project-access (write)
- [ ] `test03_check_project_access_manage` - POST /check-project-access (manage)
- [ ] `test04_check_project_access_batch` - POST /check-project-access-batch

**Fichier à créer**: `test_api_project_access.py`

---

## 13. Intégration WBS 🚧 (0/2)

- [ ] `test01_get_wbs_structure` - GET /projects/{id}/wbs-structure
- [ ] `test02_wbs_with_milestones` - Structure avec jalons et livrables

**Fichier à créer**: `test_api_wbs.py`

---

## 14. Tests de Sécurité 🚧 (0/8)

### Multi-tenancy
- [ ] `test01_isolation_company_id` - Vérifier isolation par company_id
- [ ] `test02_jwt_company_extraction` - Extraction automatique du JWT

### Authority of Sources
- [ ] `test03_create_project_company_override` - Tentative override company_id
- [ ] `test04_create_milestone_project_override` - Tentative override project_id
- [ ] `test05_tampering_detection_logged` - Vérifier logs de tampering

### Permissions
- [ ] `test06_owner_full_access` - Owner a tous les droits
- [ ] `test07_viewer_read_only` - Viewer lecture seule
- [ ] `test08_contributor_no_delete` - Contributor ne peut pas supprimer

**Fichier à créer**: `test_api_security.py`

---

## 15. Tests de Cycle de Vie 🚧 (0/6)

- [ ] `test01_project_lifecycle_complete` - Cycle complet consultation → archived
- [ ] `test02_status_transitions` - Transitions valides de statut
- [ ] `test03_invalid_transitions` - Transitions interdites
- [ ] `test04_suspend_resume` - Suspension et reprise
- [ ] `test05_archive_restore` - Archivage et restauration
- [ ] `test06_delete_constraints` - Contraintes de suppression

**Fichier à créer**: `test_api_lifecycle.py`

---

## 16. Tests Edge Cases 🚧 (0/10)

- [ ] `test01_create_project_missing_name` - Champ requis manquant
- [ ] `test02_create_project_invalid_uuid` - UUID malformé
- [ ] `test03_update_nonexistent_project` - 404
- [ ] `test04_delete_project_with_milestones` - 409
- [ ] `test05_add_member_twice` - 409
- [ ] `test06_remove_last_owner` - 409
- [ ] `test07_delete_default_role` - 403
- [ ] `test08_invalid_date_format` - Validation dates
- [ ] `test09_negative_contract_amount` - Validation montant
- [ ] `test10_invalid_currency_code` - Code devise invalide

**Fichier à créer**: `test_api_edge_cases.py`

---

## Notes de Développement

### Priorité 1 (Fondations)
1. ✅ Tests système (health, version, config)
2. 🚧 Tests projets CRUD
3. 🚧 Tests membres
4. 🚧 Tests sécurité multi-tenant

### Priorité 2 (Fonctionnalités)
1. Tests milestones et deliverables
2. Tests RBAC (rôles, politiques, permissions)
3. Tests cycle de vie

### Priorité 3 (Intégration)
1. Tests contrôle d'accès (Storage/Task services)
2. Tests WBS structure
3. Tests edge cases

### Modèle de Test

```python
def test01_example(self, api_tester, session_auth_cookies, session_user_info):
    """Description du test
    
    Selon RESPONSES_SPECIFICATION.md:
    - 200 OK: ...
    - 400 Bad Request: ...
    """
    company_id = session_user_info["company_id"]
    
    # Setup
    # ...
    
    # Action
    response = api_tester.session.get(
        f"{api_tester.base_url}/api/project/...",
        cookies=session_auth_cookies
    )
    
    # Assertions
    assert response.status_code == 200
    
    # Cleanup
    # ...
```

---

**Dernière mise à jour**: 2025-11-12  
**Prochaine étape**: Implémenter `test_api_projects.py` (CRUD de base)
