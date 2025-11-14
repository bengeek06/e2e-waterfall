# TODO - Tests pour API Storage et Basic I/O

## 📋 Statut Global

- **API Storage**: 30/53 tests implémentés (57%)
- **API Basic I/O**: 55/60 tests implémentés (92%)
  - ✅ Tests système: 3/3
  - ✅ Export simple: 6/6
  - ✅ Export tree: 8/8
  - ✅ Export enriched: 5/5
  - ✅ Import simple: 5/5
  - ✅ Import FK: 6/6
  - ✅ Import tree: 6/6
  - ⚠️ Import Mermaid: 4/4 (xfail - bug serveur)
  - ⏳ Import reports: 0/6
  - ⏳ Edge cases: 0/11
- **Total**: 85/113 tests (75%)

---

## 🗄️ API Storage - 53 tests

### ✅ 1. Tests système de base (3 tests)
- [ ] `test01_health_check` - Vérifier `/health`
- [ ] `test02_version` - Vérifier `/version`
- [ ] `test03_config` - Vérifier `/config`

### ✅ 2. Tests Upload/Download (14 tests)

#### Upload presign
- [ ] `test04_upload_presign_users_bucket`
- [ ] `test05_upload_presign_companies_bucket`
- [ ] `test06_upload_presign_projects_bucket`
- [ ] `test07_upload_presign_invalid_bucket`
- [ ] `test08_upload_presign_unauthorized`

#### Upload proxy
- [ ] `test09_upload_proxy_small_file`
- [ ] `test10_upload_proxy_large_file`
- [ ] `test11_upload_proxy_invalid_content_type`
- [ ] `test12_upload_proxy_payload_too_large` (413)

#### Download presign
- [ ] `test13_download_presign_existing_file`
- [ ] `test14_download_presign_missing_file`
- [ ] `test15_download_presign_expired_url`

#### Download proxy
- [ ] `test16_download_proxy_stream_file`
- [ ] `test17_download_proxy_missing_file`

### ✅ 3. Tests Métadonnées et Listing (6 tests)
- [ ] `test18_list_files_users_bucket`
- [ ] `test19_list_files_with_pagination`
- [ ] `test20_list_files_empty_directory`
- [ ] `test21_get_metadata_existing_file`
- [ ] `test22_update_metadata_tags`
- [ ] `test23_update_metadata_description`

### ✅ 4. Tests Versioning (6 tests)
- [ ] `test24_list_versions_new_file` - devrait être vide
- [ ] `test25_commit_new_version`
- [ ] `test26_list_versions_after_commit`
- [ ] `test27_approve_pending_version`
- [ ] `test28_reject_pending_version`
- [ ] `test29_download_specific_version`

### ✅ 5. Tests Locks - workflow collaboratif (7 tests)
- [ ] `test30_lock_file_explicit`
- [ ] `test31_lock_already_locked_file` (409)
- [ ] `test32_list_locks_in_bucket`
- [ ] `test33_unlock_own_lock`
- [ ] `test34_unlock_force_others_lock` (admin)
- [ ] `test35_unlock_without_permission` (403)
- [ ] `test36_copy_file_auto_lock` - copy de project → user

### ✅ 6. Tests Copy - workflow collaboratif (4 tests)
- [ ] `test37_copy_project_to_user_workspace`
- [ ] `test38_copy_creates_lock_on_source`
- [ ] `test39_copy_without_read_permission` (403)
- [ ] `test40_copy_already_locked_file` (409)

### ✅ 7. Tests Delete (5 tests)
- [ ] `test41_delete_logical_archive`
- [ ] `test42_delete_physical_permanent`
- [ ] `test43_delete_locked_file_no_force` (403)
- [ ] `test44_delete_locked_file_with_force`
- [ ] `test45_delete_missing_file` (404)

### ✅ 8. Tests Permissions - délégation (5 tests)
- [ ] `test46_access_project_file_as_member`
- [ ] `test47_access_project_file_unauthorized` (403)
- [ ] `test48_project_service_unavailable` (503)
- [ ] `test49_access_users_bucket_wrong_user_id` (403)
- [ ] `test50_access_companies_bucket_wrong_company_id` (403)

### ✅ 9. Tests Edge Cases (3 tests)
- [ ] `test51_upload_concurrent_same_file`
- [ ] `test52_download_while_locked`
- [ ] `test53_metadata_special_characters_in_path`

---

## 📦 API Basic I/O - 60 tests

### ✅ 1. Tests système de base (3 tests)
- [ ] `test01_health_check`
- [ ] `test02_version`
- [ ] `test03_config`

### ✅ 2. Tests Export - Formats simples (6 tests)

#### JSON export
- [ ] `test04_export_json_flat_list`
- [ ] `test05_export_json_with_enrichment`
- [ ] `test06_export_json_empty_result`

#### CSV export
- [ ] `test07_export_csv_simple`
- [ ] `test08_export_csv_with_special_chars`
- [ ] `test09_export_csv_large_dataset`

### ✅ 3. Tests Export - Structures arborescentes (5 tests)

#### Tree structures
- [ ] `test10_export_json_tree_structure` - tree=true
- [ ] `test11_export_json_flat_with_parent_id` - tree=false
- [ ] `test12_detect_tree_structure_parent_id`
- [ ] `test13_detect_tree_structure_parent_uuid`

#### Mermaid diagrams
- [ ] `test14_export_mermaid_flowchart`
- [ ] `test15_export_mermaid_graph`
- [ ] `test16_export_mermaid_mindmap`
- [ ] `test17_export_mermaid_with_metadata`

### ✅ 4. Tests Export - Enrichissement FK (5 tests)
- [ ] `test18_export_enriched_detect_fk_fields`
- [ ] `test19_export_enriched_users_lookup_email`
- [ ] `test20_export_enriched_projects_lookup_name`
- [ ] `test21_export_enriched_parent_id_special_handling`
- [ ] `test22_export_enriched_custom_lookup_config`

### ✅ 5. Tests Import - Basiques (5 tests)

#### Simple imports
- [ ] `test23_import_json_simple_records`
- [ ] `test24_import_csv_simple_records`
- [ ] `test25_import_json_empty_array` (400)
- [ ] `test26_import_csv_malformed` (400)
- [ ] `test27_import_csv_encoding_error` (400)

### ✅ 6. Tests Import - Résolution de références (6 tests)

#### FK resolution
- [ ] `test28_import_auto_resolve_single_match`
- [ ] `test29_import_ambiguous_reference_skip`
- [ ] `test30_import_ambiguous_reference_fail`
- [ ] `test31_import_missing_reference_skip`
- [ ] `test32_import_missing_reference_fail`
- [ ] `test33_import_no_import_order_required` - tasks avant users!

### ✅ 7. Tests Import - Structures arborescentes (6 tests) ✅ COMPLET

#### Tree imports
- [x] `test34_import_tree_json_nested` ✅
- [x] `test35_import_tree_json_flat_with_parent_id` ✅
- [x] `test36_import_tree_topological_sort` ✅
- [x] `test37_import_tree_circular_reference_detection` (400) ✅
- [x] `test38_import_tree_orphaned_nodes` ✅
- [x] `test39_import_tree_session_parent_mapping` ✅

**Résultat**: 6/6 tests passent - parent_id correctement remappé, tri topologique fonctionne, détection de cycles OK

### ✅ 8. Tests Import - Mermaid (4 tests) ⚠️ XFAIL - Bug serveur
- [x] `test40_import_mermaid_flowchart` ⚠️ xfail - parser retourne 0 records
- [x] `test41_import_mermaid_mindmap` ⚠️ xfail - parser incomplet
- [x] `test42_import_mermaid_parse_error` ⚠️ xfail - pas de validation syntaxe
- [x] `test43_import_mermaid_reconstruct_parent_id` ⚠️ xfail - parser retourne 0 records

**Résultat**: 4/4 tests implémentés mais marqués xfail - Bug serveur documenté dans `.bugs/bug_mermaid_parser_returns_zero_records.md`  
**Cause**: Parser Mermaid utilise regex non-standard - ne reconnaît pas syntaxe officielle Mermaid (arrows `-->`, brackets `[]`)  
**Tests passeront automatiquement** quand le bug sera corrigé côté serveur

### ✅ 9. Tests Import - Rapports détaillés (6 tests)
- [ ] `test44_import_report_id_mapping`
- [ ] `test45_import_report_reference_resolutions`
- [ ] `test46_import_report_errors_list`
- [ ] `test47_import_report_warnings`
- [ ] `test48_import_report_timing`
- [ ] `test49_import_partial_success` - 45/50 réussis

### ✅ 10. Tests Edge Cases (11 tests)

#### Error handling
- [ ] `test50_export_target_unreachable` (502)
- [ ] `test51_export_auth_failure_on_target` (401/403)
- [ ] `test52_import_target_unreachable` (502)
- [ ] `test53_import_file_too_large` (413)
- [ ] `test54_export_unsupported_format` (400)
- [ ] `test55_import_unsupported_format` (400)

#### Complex scenarios
- [ ] `test56_export_import_roundtrip` - export puis import
- [ ] `test57_export_import_cross_environment`
- [ ] `test58_import_with_custom_lookup_config`
- [ ] `test59_batch_import_multiple_resources`
- [ ] `test60_export_large_dataset_no_timeout`

---

## 🎯 Structure de fichiers proposée

```
tests/
├── api/
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── test_storage_health.py       # 3 tests ✅
│   │   ├── test_storage_upload.py       # 12 tests
│   │   ├── test_storage_download.py     # 5 tests
│   │   ├── test_storage_metadata.py     # 6 tests
│   │   ├── test_storage_versioning.py   # 6 tests
│   │   ├── test_storage_locks.py        # 7 tests
│   │   ├── test_storage_copy.py         # 4 tests
│   │   ├── test_storage_delete.py       # 5 tests
│   │   └── test_storage_permissions.py  # 5 tests
│   │
│   └── basic_io/
│       ├── __init__.py
│       ├── test_basic_io_health.py       # 3 tests ✅
│       ├── test_basic_io_export_simple.py    # 6 tests
│       ├── test_basic_io_export_tree.py      # 8 tests
│       ├── test_basic_io_export_enriched.py  # 5 tests
│       ├── test_basic_io_import_simple.py    # 5 tests
│       ├── test_basic_io_import_fk.py        # 6 tests
│       ├── test_basic_io_import_tree.py      # 6 tests
│       ├── test_basic_io_import_mermaid.py   # 4 tests
│       ├── test_basic_io_import_reports.py   # 6 tests
│       └── test_basic_io_edge_cases.py       # 11 tests
```

---

## 💡 Helpers et Fixtures à créer

### Dans conftest.py
```python
@pytest.fixture(scope="class")
def storage_tester(app_config):
    """Helper pour tests Storage API"""
    return StorageAPITester(app_config)

@pytest.fixture(scope="class")
def basic_io_tester(app_config):
    """Helper pour tests Basic I/O API"""
    return BasicIOAPITester(app_config)

@pytest.fixture(scope="function")
def temp_minio_file(storage_tester):
    """Crée un fichier temporaire dans MinIO pour tests"""
    # Upload, yield file_id, cleanup

@pytest.fixture(scope="function")
def sample_json_export():
    """Données JSON exemple pour tests import"""
    return [{...}, {...}]

@pytest.fixture(scope="function")
def sample_csv_export():
    """Données CSV exemple pour tests import"""
    return "id,name,email\n..."
```

---

## 📝 Notes

- **URL Storage API**: À déterminer (ex: `http://localhost:5003` ou `https://localhost/api/storage`)
- **URL Basic I/O API**: À déterminer (ex: `http://localhost:5004` ou `https://localhost/api/basic-io`)
- **MinIO**: Tests nécessiteront un environnement MinIO configuré
- **Services dépendants**: 
  - Storage → Project service (pour permissions bucket projects)
  - Basic I/O → Tous les services Waterfall (pour export/import)

---

## 🚀 Ordre de développement recommandé

### Phase 1 - Fondations (En cours ✅)
1. ✅ Tests Health pour Storage
2. ✅ Tests Health pour Basic I/O
3. Tests Upload/Download Storage (basiques)
4. Tests Export/Import Basic I/O (basiques)

### Phase 2 - Fonctionnalités avancées
5. Tests Versioning Storage
6. Tests Locks Storage
7. Tests Tree structures Basic I/O
8. Tests FK resolution Basic I/O

### Phase 3 - Edge Cases
9. Tests Permissions Storage
10. Tests Mermaid Basic I/O
11. Tous les edge cases

---

**Date de création**: 2025-11-10
**Dernière mise à jour**: 2025-11-10
