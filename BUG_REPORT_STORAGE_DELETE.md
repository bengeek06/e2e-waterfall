# Bug Report: Incohérence MinIO/Database après suppression physique

**Date:** 2025-11-10  
**Service:** Storage API  
**Sévérité:** 🔴 **CRITIQUE** - Perte d'intégrité des données  
**Status:** 🐛 **CONFIRMED**

---

## Résumé

Après une suppression physique (`DELETE /api/storage/delete` avec `physical=true`), l'objet est bien supprimé dans MinIO mais **les métadonnées restent en base de données**. Cela crée une **incohérence critique** entre le stockage objet et la base de données.

---

## Impact

### 🚨 Conséquences

1. **Données orphelines** : Métadonnées pointant vers des objets inexistants
2. **Erreurs de téléchargement** : Les utilisateurs voient le fichier dans les listings mais ne peuvent pas le télécharger (404 de MinIO)
3. **Confusion utilisateur** : Le fichier apparaît comme existant alors qu'il est physiquement supprimé
4. **Problèmes de quota** : La taille du fichier est comptée dans les statistiques mais l'espace n'est pas libéré
5. **Impossibilité de recréer** : Si on tente de recréer un fichier au même `logical_path`, conflit potentiel avec les métadonnées orphelines

---

## Reproduction

### Test automatisé
```bash
pytest api/storage/test_storage_delete.py::TestStorageDelete::test02_delete_physical_permanent -v
```

### Étapes manuelles

1. **Upload d'un fichier**
   ```bash
   POST /api/storage/upload/proxy
   {
     "bucket_type": "users",
     "bucket_id": "5d766b9a-3373-4c2b-b31d-897df5428bde",
     "logical_path": "test/file.txt"
   }
   # Retourne: file_id = "88e242fd-2d68-4299-83e0-e5ca5a7481d6"
   ```

2. **Suppression physique**
   ```bash
   DELETE /api/storage/delete
   {
     "file_id": "88e242fd-2d68-4299-83e0-e5ca5a7481d6",
     "physical": true
   }
   # Retourne: 200 OK
   # {
   #   "success": true,
   #   "data": {
   #     "logical_delete": true,
   #     "physical_delete": true
   #   }
   # }
   ```

3. **Vérification des métadonnées**
   ```bash
   GET /api/storage/metadata?bucket=users&id=5d766b9a-3373-4c2b-b31d-897df5428bde&logical_path=test/file.txt
   # 🐛 BUG: Retourne 200 avec métadonnées complètes
   # ATTENDU: 404 Not Found
   ```

4. **Tentative de téléchargement**
   ```bash
   GET /api/storage/download/proxy?bucket_type=users&bucket_id=...&logical_path=test/file.txt
   # RÉSULTAT: Erreur MinIO (objet n'existe pas) ou 404
   ```

---

## Comportement attendu

Après `DELETE` avec `physical=true`, **TOUTES** les traces du fichier doivent être supprimées :

```
✅ Objet MinIO → SUPPRIMÉ
✅ Métadonnées DB → SUPPRIMÉES (404 sur /metadata)
✅ Versions → SUPPRIMÉES
✅ Locks → LIBÉRÉS et supprimés
```

### Réponse attendue après suppression physique

```bash
GET /api/storage/metadata?bucket=users&id=...&logical_path=test/file.txt
→ 404 Not Found
{
  "error": "FILE_NOT_FOUND",
  "message": "File not found or has been deleted"
}
```

---

## Comportement actuel (bug)

```
✅ Objet MinIO → SUPPRIMÉ
❌ Métadonnées DB → PERSISTENT (200 sur /metadata)
❌ État incohérent → Métadonnées orphelines
```

### Réponse actuelle (incorrecte)

```bash
GET /api/storage/metadata?bucket=users&id=...&logical_path=test/file.txt
→ 200 OK ❌
{
  "file": {
    "id": "88e242fd-2d68-4299-83e0-e5ca5a7481d6",
    "bucket_type": "users",
    "logical_path": "test/file.txt",
    "is_deleted": false,  # ❌ Devrait être supprimé
    "size": 200,
    ...
  },
  "current_version": { ... }
}
```

---

## Code source suspect

### Endpoint DELETE probable
```python
# storage_api/routes/delete.py (hypothétique)

@app.route('/delete', methods=['DELETE'])
def delete_file():
    data = request.json
    file_id = data['file_id']
    physical = data.get('physical', False)
    
    file = db.query(File).filter_by(id=file_id).first()
    
    if physical:
        # ✅ Suppression MinIO
        minio_client.remove_object(file.bucket, file.object_key)
        
        # ❌ BUG: Métadonnées non supprimées !
        file.is_deleted = True
        db.commit()
        # Au lieu de: db.delete(file); db.commit()
    
    return {"success": True, "data": {"physical_delete": physical}}
```

---

## Solution proposée

### Option 1: Suppression complète (recommandée)

```python
if physical:
    # 1. Supprimer l'objet MinIO
    minio_client.remove_object(file.bucket, file.object_key)
    
    # 2. Supprimer toutes les versions
    versions = db.query(Version).filter_by(file_id=file_id).all()
    for version in versions:
        minio_client.remove_object(version.bucket, version.object_key)
        db.delete(version)
    
    # 3. Supprimer les locks
    db.query(Lock).filter_by(file_id=file_id).delete()
    
    # 4. Supprimer les métadonnées
    db.delete(file)
    db.commit()
```

### Option 2: Flag is_deleted + cleanup périodique

Si on veut garder une trace pour audit :

```python
if physical:
    # Suppression MinIO
    minio_client.remove_object(file.bucket, file.object_key)
    
    # Marquer comme physiquement supprimé
    file.is_deleted = True
    file.physically_deleted = True
    file.deleted_at = datetime.utcnow()
    db.commit()
    
    # IMPORTANT: Endpoint /metadata doit retourner 404 si physically_deleted=True
```

Puis modifier l'endpoint `/metadata` :

```python
@app.route('/metadata', methods=['GET'])
def get_metadata():
    file = get_file_by_path(...)
    
    if not file or file.physically_deleted:  # ← AJOUT
        return {"error": "FILE_NOT_FOUND"}, 404
    
    return file.to_dict()
```

---

## Tests à ajouter/corriger

### Test actuel qui détecte le bug

```python
def test02_delete_physical_permanent():
    # Upload file
    file = upload_test_file()
    
    # Delete with physical=true
    response = delete(file_id=file['file_id'], physical=True)
    assert response['success'] is True
    assert response['data']['physical_delete'] is True
    
    # ✅ Vérifier que les métadonnées sont supprimées
    metadata_response = get_metadata(file['logical_path'])
    assert metadata_response.status_code == 404, \
        "BUG: Metadata still exists after physical deletion"
```

### Tests de régression à ajouter

1. **test_cannot_download_after_physical_delete** : Téléchargement impossible
2. **test_can_recreate_after_physical_delete** : Peut recréer fichier au même path
3. **test_listing_excludes_physically_deleted** : Listing n'inclut pas fichiers supprimés
4. **test_quota_freed_after_physical_delete** : Quota libéré correctement

---

## Priorité et urgence

| Critère | Évaluation |
|---------|------------|
| **Sévérité** | 🔴 CRITIQUE |
| **Fréquence** | Chaque suppression physique |
| **Impact utilisateur** | Élevé (confusion, erreurs) |
| **Impact données** | Très élevé (perte d'intégrité) |
| **Facilité de correction** | Moyenne |
| **Priorité** | **P0 - À corriger immédiatement** |

---

## Checklist de correction

- [ ] Modifier endpoint DELETE pour supprimer métadonnées si `physical=true`
- [ ] Supprimer aussi les versions associées dans MinIO
- [ ] Libérer les locks associés
- [ ] Vérifier que GET /metadata retourne 404
- [ ] Vérifier que GET /list n'inclut pas le fichier
- [ ] Vérifier que download retourne 404
- [ ] Tester qu'on peut recréer un fichier au même path
- [ ] Ajouter tests de régression
- [ ] Documenter le comportement dans la spec OpenAPI
- [ ] Migration de données si besoin (nettoyer métadonnées orphelines existantes)

---

## Notes supplémentaires

### Distinction logical vs physical delete

| Type | Objet MinIO | Métadonnées DB | Use case |
|------|-------------|----------------|----------|
| **Logical** (`physical=false`) | ✅ Conservé | ✅ Conservées (`is_deleted=true`) | Soft delete, récupérable |
| **Physical** (`physical=true`) | ❌ Supprimé | ❌ **DOIT être supprimé** | Hard delete, définitif |

### Cas d'usage legitimate de physical delete

- Suppression RGPD (droit à l'oubli)
- Nettoyage de fichiers temporaires
- Libération d'espace disque
- Suppression définitive de données sensibles

Dans **TOUS** ces cas, les métadonnées DOIVENT être supprimées pour éviter les fuites d'information et maintenir la cohérence.

---

**Rapporté par:** Tests automatisés E2E  
**Fichier de test:** `tests/api/storage/test_storage_delete.py::test02_delete_physical_permanent`  
**Commit:** À spécifier après correction
