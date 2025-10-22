# 🔴 RAPPORT DE SÉCURITÉ CRITIQUE - ISOLATION MULTI-TENANT

**Date:** 20 Octobre 2025  
**Criticité:** 🔴 HAUTE  
**Service affecté:** Guardian  
**Endpoint vulnérable:** `POST /api/guardian/check-access`  
**Statut:** 🚨 OUVERT - Correction requise immédiatement  

---

## 📋 RÉSUMÉ EXÉCUTIF

Une vulnérabilité critique d'isolation multi-tenant a été identifiée dans le service Guardian. L'endpoint `/check-access` ne valide pas que le `company_id` fourni dans la requête correspond au `company_id` de l'utilisateur authentifié. Cela permet à un utilisateur malveillant d'accéder aux ressources d'autres entreprises en modifiant simplement le paramètre `company_id` dans ses requêtes.

**Impact:** Un utilisateur de l'entreprise A peut potentiellement voir, modifier ou supprimer des ressources de l'entreprise B, violant complètement l'isolation des données entre tenants.

---

## 🔍 DESCRIPTION TECHNIQUE DU PROBLÈME

### Comportement Actuel (Vulnérable)

L'endpoint `POST /api/guardian/check-access` accepte les paramètres suivants :
```json
{
  "user_id": "uuid-de-l-utilisateur",
  "company_id": "uuid-de-l-entreprise",
  "service": "nom-du-service",
  "resource_name": "nom-de-la-ressource",
  "operation": "read|write|delete|..."
}
```

**Problème:** Le backend ne vérifie PAS que le `company_id` fourni correspond au `company_id` de l'utilisateur authentifié (extrait du JWT token).

### Scénario de Test Reproductible

**Configuration du test:**
- Utilisateur authentifié: `16fa770f-acee-4c7b-b4c5-f733be05ccc7`
- Company ID légitime de l'utilisateur: `a3fe82a9-52e1-4e1e-9a1c-2e3add6d00bd`
- Company ID falsifié dans la requête: `00000000-0000-0000-0000-000000000000`

**Requête envoyée:**
```json
POST /api/guardian/check-access
Authorization: Bearer <valid-jwt-token>

{
  "user_id": "16fa770f-acee-4c7b-b4c5-f733be05ccc7",
  "company_id": "00000000-0000-0000-0000-000000000000",
  "service": "guardian",
  "resource_name": "role",
  "operation": "read"
}
```

**Réponse actuelle de l'API:**
```json
HTTP 200 OK

{
  "access_granted": true,
  "reason": "Access granted by user role and policy."
}
```

**❌ Résultat:** L'accès est accordé malgré le `company_id` différent !

### Preuve de Concept

Le test `test05_check_access_different_company` dans le fichier `tests/api/guardian/test_api_access_control.py` démontre cette vulnérabilité :

```python
def test05_check_access_different_company(self, auth_token, setup_test_data, test_permission):
    """Test check-access with different company_id (security test)"""
    user_id, company_id = setup_test_data
    
    # Use a fake company_id different from the user's actual company
    fake_company_id = "00000000-0000-0000-0000-000000000000"
    
    logger.info(f"Test setup - User ID: {user_id}, Company ID: {company_id}")
    logger.warning(f">>> Using FAKE company_id: {fake_company_id} (real: {company_id})")
    
    operation = test_permission['operation'].split('.')[-1].lower()
    
    body = {
        "user_id": user_id,
        "company_id": fake_company_id,  # ← Company ID FALSIFIÉ
        "service": "guardian",
        "resource_name": "role",
        "operation": operation
    }
    
    response = requests.post(f"{BASE_URL}/check-access", json=body, headers={"Authorization": f"Bearer {auth_token}"})
    
    # L'API ACCORDE L'ACCÈS alors qu'elle devrait le REFUSER
    assert response.json()['access_granted'] == True  # ← VULNÉRABILITÉ
```

**Localisation du test:** `tests/api/guardian/test_api_access_control.py::TestAPIAccessControl::test05_check_access_different_company`

**Logs de test:** `logs/test_api_guardian.log`

---

## ⚠️ IMPACT SÉCURITÉ

### Criticité: 🔴 HAUTE

### Impacts Identifiés

#### 1. **Contournement Total de l'Isolation Multi-Tenant**
- Un utilisateur de la Company A peut accéder aux ressources de la Company B, C, D, etc.
- Violation du principe fondamental d'isolation des données entre clients
- Compromission de l'architecture SaaS multi-tenant

#### 2. **Escalade de Privilèges Cross-Tenant**
Un attaquant pourrait :
- **Lire** des données confidentielles d'autres entreprises (rôles, permissions, policies, utilisateurs)
- **Modifier** des configurations de sécurité d'autres entreprises
- **Supprimer** des ressources critiques d'autres entreprises
- **Créer** des backdoors dans d'autres tenants

#### 3. **Violation de Conformité Réglementaire**
- **RGPD (Article 32):** Violation de l'obligation de sécurité des données personnelles
- **ISO 27001:** Non-respect des contrôles d'accès logique
- **SOC 2:** Compromission des contrôles de ségrégation des données
- **PCI DSS:** Si données de paiement, violation des exigences d'isolation

#### 4. **Risque de Réputation et Légal**
- Perte de confiance des clients
- Potentiel de litiges et amendes réglementaires
- Obligation de notification de violation de données (RGPD Art. 33-34)

### Scénarios d'Attaque Possibles

**Scénario 1: Vol de Données Cross-Tenant**
```
1. Attaquant authentifié dans Company A
2. Énumère les company_id via fuzzing ou fuite d'information
3. Modifie company_id dans requêtes /check-access
4. Obtient accès aux ressources de Company B
5. Exfiltre données sensibles
```

**Scénario 2: Sabotage de Configuration**
```
1. Attaquant identifie un concurrent (Company B)
2. Utilise company_id de Company B dans ses requêtes
3. Modifie/supprime rôles et permissions critiques
4. Compromet la sécurité et les opérations du concurrent
```

**Scénario 3: Escalade via Injection de Policies**
```
1. Attaquant crée des policies malveillantes
2. Les associe à d'autres company_id
3. Obtient des privilèges élevés dans d'autres tenants
4. Contrôle total du système multi-tenant
```

---

## 🔧 COMPORTEMENT ATTENDU

### Solution de Sécurité Requise

L'endpoint `/check-access` DOIT implémenter la validation suivante :

#### 1. Extraction du Company ID du JWT Token
```python
# Le JWT token contient le company_id de l'utilisateur authentifié
token_data = decode_jwt(request.headers['Authorization'])
token_company_id = token_data['company_id']  # Company légitime de l'user
```

#### 2. Validation Stricte de l'Isolation
```python
request_company_id = request.json.get('company_id')

# VALIDATION CRITIQUE
if token_company_id != request_company_id:
    # Loguer la tentative suspecte
    logger.warning(
        f"Multi-tenant isolation violation attempt: "
        f"user {token_data['user_id']} from company {token_company_id} "
        f"tried to access company {request_company_id}"
    )
    
    # REJETER la requête
    return {
        "access_granted": False,
        "reason": "Company ID mismatch - multi-tenant isolation violation"
    }, 403
```

#### 3. Réponse Sécurisée

**Cas 1: Company ID invalide (différent du token)**
```json
HTTP 403 Forbidden

{
  "access_granted": false,
  "reason": "Company ID mismatch - access denied"
}
```

**Alternative (plus stricte):**
```json
HTTP 403 Forbidden

{
  "error": "Forbidden",
  "message": "Cannot check access for different company"
}
```

**Cas 2: Company ID valide**
```json
HTTP 200 OK

{
  "access_granted": true/false,
  "reason": "Access granted/denied based on RBAC rules"
}
```

---

## 🛠️ RECOMMANDATIONS DE CORRECTION

### Actions Immédiates (0-24h) ⚠️ URGENT

#### 1. **Correction du Backend Guardian**
**Fichier concerné:** `services/guardian/routes/check_access.py` (ou équivalent)

```python
@router.post("/check-access")
async def check_access(
    request: CheckAccessRequest,
    token: dict = Depends(verify_jwt_token)
):
    # 1. VALIDATION MULTI-TENANT CRITIQUE
    token_company_id = token.get('company_id')
    request_company_id = request.company_id
    
    if token_company_id != request_company_id:
        logger.warning(
            f"Multi-tenant violation: user={token.get('user_id')} "
            f"token_company={token_company_id} != request_company={request_company_id}",
            extra={
                "security_event": "multi_tenant_violation",
                "user_id": token.get('user_id'),
                "token_company_id": token_company_id,
                "request_company_id": request_company_id,
                "ip_address": request.client.host
            }
        )
        return JSONResponse(
            status_code=403,
            content={
                "access_granted": False,
                "reason": "Company ID mismatch - multi-tenant isolation violation"
            }
        )
    
    # 2. Continuer avec la logique RBAC normale seulement si validation OK
    # ... reste de la logique check-access
```

#### 2. **Mise à Jour du Test de Sécurité**
**Fichier:** `tests/api/guardian/test_api_access_control.py`

Modifier `test05_check_access_different_company` pour qu'il **FAIL** après correction :

```python
def test05_check_access_different_company(self, auth_token, setup_test_data, test_permission):
    """Test check-access rejects different company_id (security test)"""
    user_id, company_id = setup_test_data
    fake_company_id = "00000000-0000-0000-0000-000000000000"
    
    operation = test_permission['operation'].split('.')[-1].lower()
    body = {
        "user_id": user_id,
        "company_id": fake_company_id,
        "service": "guardian",
        "resource_name": "role",
        "operation": operation
    }
    
    response = requests.post(
        f"{BASE_URL}/check-access",
        json=body,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # APRÈS CORRECTION: doit retourner access_granted=False ou 403
    assert response.status_code in [200, 403], f"Expected 200/403, got {response.status_code}"
    
    if response.status_code == 200:
        response_data = response.json()
        assert response_data['access_granted'] == False, \
            "Security violation: access granted with different company_id"
        assert "mismatch" in response_data.get('reason', '').lower(), \
            "Expected company mismatch reason"
    else:  # 403
        response_data = response.json()
        assert 'error' in response_data or 'access_granted' in response_data
```

#### 3. **Audit de Sécurité Complet**
Vérifier TOUS les endpoints qui acceptent `company_id` en paramètre :

**Guardian Service:**
- ✅ `POST /check-access` ← Confirmé vulnérable
- ⚠️ `GET /user-roles?company_id=X` ← À vérifier
- ⚠️ `GET /roles?company_id=X` ← À vérifier  
- ⚠️ `POST /roles` (body: company_id) ← À vérifier
- ⚠️ `GET /policies?company_id=X` ← À vérifier
- ⚠️ `POST /policies` (body: company_id) ← À vérifier
- ⚠️ `GET /permissions?company_id=X` ← À vérifier
- ⚠️ `POST /permissions` (body: company_id) ← À vérifier

**Identity Service:**
- ⚠️ `GET /users?company_id=X` ← À vérifier
- ⚠️ `GET /companies/{id}` ← À vérifier
- ⚠️ `POST /users` (body: company_id) ← À vérifier
- ⚠️ Tous les endpoints avec filtrage company_id ← À vérifier

#### 4. **Logging de Sécurité**
Implémenter un logging spécifique pour détecter les tentatives de violation :

```python
# Format de log de sécurité
{
  "timestamp": "2025-10-20T14:30:00Z",
  "event_type": "multi_tenant_violation_attempt",
  "severity": "HIGH",
  "user_id": "uuid",
  "user_company_id": "uuid",
  "requested_company_id": "uuid",
  "endpoint": "/api/guardian/check-access",
  "ip_address": "xxx.xxx.xxx.xxx",
  "user_agent": "...",
  "action_taken": "access_denied"
}
```

### Actions Court Terme (24-48h)

#### 5. **Middleware Centralisé de Validation**
Créer un middleware réutilisable pour tous les services :

```python
# middleware/multi_tenant_validator.py
class MultiTenantValidator:
    """Middleware to enforce multi-tenant isolation"""
    
    @staticmethod
    def validate_company_access(token: dict, requested_company_id: str) -> bool:
        """
        Validate that user can only access their own company's data
        
        Args:
            token: Decoded JWT token containing user's company_id
            requested_company_id: Company ID from request (query/body)
        
        Returns:
            bool: True if valid, raises HTTPException(403) if invalid
        """
        token_company_id = token.get('company_id')
        
        if not token_company_id:
            logger.error("JWT token missing company_id")
            raise HTTPException(status_code=401, detail="Invalid token")
        
        if token_company_id != requested_company_id:
            logger.warning(
                f"Multi-tenant violation blocked",
                extra={
                    "user_id": token.get('user_id'),
                    "token_company": token_company_id,
                    "requested_company": requested_company_id
                }
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot access resources of different company"
            )
        
        return True
```

Utilisation dans les endpoints :
```python
@router.get("/roles")
async def get_roles(
    company_id: str,
    token: dict = Depends(verify_jwt_token)
):
    # Validation automatique multi-tenant
    MultiTenantValidator.validate_company_access(token, company_id)
    
    # Logique métier...
```

#### 6. **Tests de Sécurité Automatisés**
Créer une suite de tests de sécurité multi-tenant pour tous les endpoints :

```python
# tests/security/test_multi_tenant_isolation.py
class TestMultiTenantIsolation:
    """Security tests for multi-tenant isolation across all services"""
    
    @pytest.mark.parametrize("endpoint,method,param_location", [
        ("/api/guardian/check-access", "POST", "body"),
        ("/api/guardian/roles", "GET", "query"),
        ("/api/identity/users", "GET", "query"),
        # ... tous les endpoints avec company_id
    ])
    def test_reject_different_company_id(self, endpoint, method, param_location):
        """Test that all endpoints reject requests with different company_id"""
        # Test systématique de l'isolation
        pass
```

### Actions Moyen Terme (1 semaine)

#### 7. **Revue de Code Axée Sécurité**
- Audit complet du code par une équipe sécurité
- Checklist de validation multi-tenant
- Documentation des patterns de sécurité

#### 8. **Documentation Architecture**
Créer `docs/architecture/multi-tenant-security.md` :
- Principes d'isolation multi-tenant
- Règles de validation company_id
- Exemples de code sécurisé
- Anti-patterns à éviter

#### 9. **Monitoring et Alerting**
Implémenter des alertes pour tentatives de violation :
- Dashboard de sécurité temps réel
- Alertes automatiques si > X tentatives/heure
- Blocage automatique d'IP suspectes

#### 10. **Formation Équipe**
- Session sur la sécurité multi-tenant
- Code review guidelines
- Threat modeling workshops

---

## 📊 PLAN D'ACTION RÉCAPITULATIF

| Priorité | Action | Responsable | Délai | Statut |
|----------|--------|-------------|-------|--------|
| 🔴 P0 | Corriger `/check-access` endpoint | Backend Guardian | 4h | ⏳ À faire |
| 🔴 P0 | Tester la correction | QA/Security | 2h | ⏳ À faire |
| 🔴 P0 | Déployer le fix en production | DevOps | 2h | ⏳ À faire |
| 🟠 P1 | Audit autres endpoints Guardian | Backend Guardian | 8h | ⏳ À faire |
| 🟠 P1 | Audit endpoints Identity | Backend Identity | 8h | ⏳ À faire |
| 🟠 P1 | Implémenter logging sécurité | Backend | 4h | ⏳ À faire |
| 🟡 P2 | Créer middleware centralisé | Backend | 16h | ⏳ À faire |
| 🟡 P2 | Suite tests sécurité auto | QA | 16h | ⏳ À faire |
| 🟢 P3 | Documentation architecture | Tech Lead | 1 semaine | ⏳ À faire |
| 🟢 P3 | Monitoring & alerting | DevOps | 1 semaine | ⏳ À faire |

**Timeline global estimé:** 
- **Fix critique:** 8 heures
- **Audit complet:** 48 heures
- **Sécurisation totale:** 2 semaines

---

## 📞 RÉFÉRENCES ET CONTACT

### Fichiers Concernés

**Tests:**
- `tests/api/guardian/test_api_access_control.py` (ligne 280-330)
- Test spécifique: `test05_check_access_different_company`

**Logs:**
- `logs/test_api_guardian.log`

**Backend (à identifier):**
- `services/guardian/routes/check_access.py` (ou équivalent)
- `services/guardian/middleware/auth.py`

### Commandes de Vérification

**Exécuter le test de sécurité:**
```bash
pytest tests/api/guardian/test_api_access_control.py::TestAPIAccessControl::test05_check_access_different_company -v -s
```

**Vérifier les logs:**
```bash
tail -f logs/test_api_guardian.log | grep -i "company"
```

**Audit rapide:**
```bash
# Rechercher tous les endpoints avec company_id
grep -r "company_id" services/ --include="*.py"
```

### Ressources Complémentaires

**Standards de Sécurité:**
- OWASP Top 10: A01:2021 – Broken Access Control
- NIST 800-53: AC-3 Access Enforcement
- CWE-639: Authorization Bypass Through User-Controlled Key

**Documentation Interne:**
- Architecture multi-tenant: `docs/architecture/multi-tenant.md`
- Standards de sécurité: `docs/security/guidelines.md`

---

## 📝 HISTORIQUE DES RÉVISIONS

| Version | Date | Auteur | Modifications |
|---------|------|--------|---------------|
| 1.0 | 2025-10-20 | GitHub Copilot | Création initiale du rapport |

---

## ✅ VALIDATION POST-CORRECTION

**Checklist de validation avant fermeture:**

- [ ] Fix déployé en production
- [ ] Test `test05_check_access_different_company` PASSE (access_granted=False)
- [ ] Tous les endpoints Guardian audités
- [ ] Tous les endpoints Identity audités
- [ ] Middleware de validation implémenté
- [ ] Logging de sécurité actif
- [ ] Tests de régression OK
- [ ] Documentation mise à jour
- [ ] Équipe formée
- [ ] Monitoring en place

**Critères de fermeture:**
- ✅ Aucun endpoint ne permet l'accès cross-tenant
- ✅ Tous les tests de sécurité passent
- ✅ Logs de sécurité opérationnels
- ✅ Revue de code sécurité validée

---

**🔴 RAPPEL: Ce problème nécessite une action IMMÉDIATE. L'isolation multi-tenant est un pilier fondamental de la sécurité SaaS.**

**Contact Security Team:** security@waterfall.com  
**Escalation:** CTO / CISO

---

*Rapport généré automatiquement le 20 Octobre 2025*
*Repository: e2e-waterfall | Branch: guardian_staging*
