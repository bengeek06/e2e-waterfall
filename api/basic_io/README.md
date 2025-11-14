# Tests Basic I/O API

Suite de tests pour le service Basic I/O (Import/Export).

## Structure

```
api/basic_io/
├── test_basic_io_import_simple.py       # Tests d'import basiques (JSON/CSV)
├── test_basic_io_import_fk.py           # Tests de résolution FK lors de l'import
└── test_basic_io_export_import.py       # Tests d'intégration Export → Import
```

## Tests disponibles

### 1. Import Simple (`test_basic_io_import_simple.py`)

Tests des fonctionnalités d'import basiques:

- **test01_import_json**: Import JSON basique
- **test02_import_csv**: Import CSV basique
- **test03_import_empty_array**: Import d'un tableau vide
- **test04_import_malformed_csv**: Gestion CSV malformé
- **test05_import_invalid_json**: Gestion JSON invalide
- **test06_import_no_auth**: Rejet sans authentification
- **test07_import_partial_success**: Import partiel avec erreurs

**Commande:**
```bash
pytest api/basic_io/test_basic_io_import_simple.py -v
```

### 2. Résolution FK (`test_basic_io_import_fk.py`)

Tests de résolution automatique des Foreign Keys avec `_references`:

- **test01_import_auto_resolve_single_match**: Résolution FK avec match unique ✅
- **test02_import_ambiguous_reference_skip**: Mode skip si référence ambiguë ⚠️
- **test03_import_ambiguous_reference_fail**: Mode fail si référence ambiguë ⚠️
- **test04_import_missing_reference_skip**: Mode skip si référence manquante ⚠️
- **test05_import_missing_reference_fail**: Mode fail si référence manquante ⚠️
- **test06_import_no_import_order_required**: (Skipped) Import indépendant de l'ordre

**Commande:**
```bash
pytest api/basic_io/test_basic_io_import_fk.py -v
```

**Note:** Ces tests valident que le service résout correctement les FK en utilisant les métadonnées `_references` présentes dans les données exportées.

**✅ GitHub Issue #4 - FIXED:**

Les modes `on_ambiguous` et `on_missing` sont maintenant **correctement implémentés**:

1. **Mode `on_ambiguous=skip`**: Le service détecte l'ambiguïté. Si le champ FK est **optionnel**, il sera mis à NULL. Si le champ est **requis** (comme `position_id` pour users), l'import échoue avec 400.
2. **Mode `on_ambiguous=fail`**: ✅ **Implémenté** - le service retourne 400 avec un message d'erreur explicite quand une référence est ambiguë
3. **Mode `on_missing=skip`**: Le service détecte les références manquantes. Si le champ FK est **optionnel**, il sera mis à NULL. Si le champ est **requis**, l'import échoue avec 400.
4. **Mode `on_missing=fail`**: ✅ **Implémenté** - le service retourne 400 avec un message d'erreur explicite quand une référence est manquante

### 3. Intégration Export/Import (`test_basic_io_export_import.py`)

Test du cycle complet Export → Delete → Import:

- **test01_export_import_cycle_with_fk_resolution**: 
  - Créer 3 positions
  - Créer 9 users (3 par position)
  - Exporter les users
  - Supprimer les users
  - Importer depuis l'export
  - Vérifier que chaque user retrouve sa position d'origine

**Commande:**
```bash
pytest api/basic_io/test_basic_io_export_import.py -v
```

**Validations effectuées:**
- Export contient les `_references` correctes (lookup_field="title", lookup_value rempli)
- Import réussit avec résolution FK (9/9 users)
- Chaque user retrouve exactement sa position d'origine

## Lancer toute la suite Basic I/O

```bash
pytest api/basic_io/ -v
```

## Lancer un test spécifique

```bash
pytest api/basic_io/test_basic_io_import_fk.py::TestBasicIOImportFK::test01_import_auto_resolve_single_match -v
```

## Lancer avec logs détaillés

```bash
pytest api/basic_io/ -v -s
```

Les logs sont sauvegardés dans `logs/test_api_basic_io.log`.

## Prérequis

- Services lancés (Next.js proxy, Identity service, Basic I/O service)
- Base de données initialisée
- Credentials de test dans `.env.test`:
  ```bash
  WEB_URL="http://localhost:3000"
  COMPANY_NAME="Test Company"
  LOGIN="testuser@example.com"
  PASSWORD="securepassword"
  ```

## Endpoints testés

- **Import**: `POST http://localhost:3000/api/basic-io/import`
- **Export**: `GET http://localhost:3000/api/basic-io/export`

**Resource cible:** `http://identity_service:5000/users` (Identity Service)

## Format des données

### Import avec résolution FK

Les données importées peuvent contenir des `_references` pour résoudre automatiquement les Foreign Keys:

```json
{
  "_original_id": "temp-user-1",
  "email": "user@example.com",
  "password": "password123",
  "company_id": "uuid-company",
  "position_id": "Position Title",  // Titre au lieu d'UUID
  "_references": {
    "position_id": {
      "resource_type": "positions",
      "original_id": "uuid-position-original",
      "lookup_field": "title",
      "lookup_value": "Position Title"
    }
  }
}
```

Le service Basic I/O:
1. Détecte la présence de `_references.position_id`
2. Recherche une position avec `title = "Position Title"`
3. Si trouvée: remplace `position_id` par l'UUID trouvé
4. Si plusieurs trouvées: applique `on_ambiguous` (skip/fail)
5. Si aucune trouvée: applique `on_missing` (skip/fail)

### Export enrichi

L'export génère automatiquement les `_references`:

```json
{
  "id": "uuid-user",
  "email": "user@example.com",
  "position_id": "uuid-position",
  "_original_id": "uuid-user",
  "_references": {
    "position_id": {
      "resource_type": "positions",
      "original_id": "uuid-position",
      "lookup_field": "title",
      "lookup_value": "Software Engineer"
    }
  }
}
```

## Résolution de problèmes

### Test échoue avec "ambiguous: 1, candidates: 2"

**Cause:** DB polluée avec des records similaires des tests précédents.

**Solution:** Nettoyer la DB ou utiliser des noms plus uniques (UUID/timestamp dans les titres).

### Export ne contient pas de `_references`

**Vérifier:**
1. Le service Export est à jour
2. La resource a des FK (ex: users.position_id)
3. Les FK pointent vers des records existants

### Import échoue avec 400 "password required"

**Cause:** L'export ne contient pas le champ `password` (normal pour sécurité).

**Solution:** Ajouter un password fictif aux données avant import (fait automatiquement dans le test d'intégration).

## Rapports de bugs

Les bugs identifiés et corrigés sont documentés dans:
- `.spec/bug_report_basic_io_fk_resolution.md` - Résolution FK (CORRIGÉ)
- `.spec/bug_report_basic_io_export_references.md` - Export _references (CORRIGÉ)

## Scripts utilitaires

- `manual_test_export_import_fk.py`: Script manuel interactif pour tester le cycle export/import (utilisé pour créer le test pytest)
