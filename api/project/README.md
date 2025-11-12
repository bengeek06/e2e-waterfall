# Tests du Project Service

Ce répertoire contient les tests E2E pour le **Project Service** de la plateforme Waterfall.

## Structure des tests

### Tests système (`test_api_system.py`)
Tests des endpoints de base du service:
- ✅ `test01_health_check` - GET /health (sans auth)
- ✅ `test02_version_endpoint` - GET /version 
- ✅ `test03_config_endpoint` - GET /config

## Spécifications

Les tests sont basés sur les spécifications OpenAPI v3 du Project Service:
- **Spec complète**: `.spec/project_api.yml`
- **Endpoints**: `.spec/ENDPOINTS_SPECIFICATION.md`
- **Schémas**: `.spec/SCHEMAS_SPECIFICATION.md`
- **Réponses**: `.spec/RESPONSES_SPECIFICATION.md`

## Lancer les tests

```bash
# Tous les tests du Project Service
pytest api/project/ -v

# Tests système uniquement
pytest api/project/test_api_system.py -v

# Test spécifique
pytest api/project/test_api_system.py::TestProjectSystemEndpoints::test01_health_check -v

# Avec logs détaillés
pytest api/project/ -v -s
```

## Prérequis

- Services Waterfall démarrés (Next.js proxy sur port 3000)
- Project Service en ligne et accessible via `/api/project/*`
- Base de données initialisée

## Endpoints testés

### Endpoints système ✅
- `GET /health` - État du service (200/503)
- `GET /version` - Version du service (200/401)
- `GET /config` - Configuration (200/401)

### Endpoints à implémenter 🚧
- `GET /projects` - Liste des projets
- `POST /projects` - Créer un projet
- `GET /projects/{id}` - Détails d'un projet
- `PUT/PATCH /projects/{id}` - Modifier un projet
- `DELETE /projects/{id}` - Supprimer un projet
- `POST /projects/{id}/archive` - Archiver un projet
- `POST /projects/{id}/restore` - Restaurer un projet
- ... (voir ENDPOINTS_SPECIFICATION.md pour la liste complète)

## Structure du Project Service

### Cycle de vie des projets
```
created → initialized → consultation → [active | lost]
                                          ↓
                                      suspended ↔ completed → archived
```

### Composants principaux
- **Projects**: Entités projet avec informations contractuelles
- **Milestones**: Jalons du projet avec dates de livraison
- **Deliverables**: Livrables associés aux jalons
- **Members**: Membres de l'équipe avec rôles

### RBAC (Role-Based Access Control)
- **Rôles par défaut**: owner, validator, contributor, viewer
- **Politiques**: Groupes de permissions
- **Permissions**: Contrôle granulaire (read_files, write_files, validate_files, etc.)

### Intégration
- **Storage Service**: Validation des permissions fichiers via `/check-file-access`
- **Task Service**: Structure WBS via `/projects/{id}/wbs-structure`
- **Identity Service**: Gestion des utilisateurs et clients
- **Guardian Service**: RBAC niveau endpoint

## Multi-tenancy

Toutes les ressources sont isolées par `company_id` extrait automatiquement du JWT.

## Sécurité - Authority of Sources

Les endpoints de création suivent le principe de **validation avec autorité des sources**:

**Sources autoritaires:**
- **JWT**: `company_id`, `user_id` (créateur)
- **URL**: `project_id`, `milestone_id` (hiérarchie)

**Détection de tampering:**
Si un client tente d'envoyer ces champs dans le payload:
1. Tentative détectée et loguée (audit trail)
2. Valeur client ignorée
3. Valeur autoritaire toujours utilisée

**Bénéfices:**
- ✅ Prévention de l'escalade de privilèges
- ✅ Traçabilité des tentatives de manipulation
- ✅ Isolation multi-tenant garantie

---

**Version**: 0.0.1  
**Date**: 2025-11-12  
**Service**: Project Service
