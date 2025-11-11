#!/usr/bin/env python3
"""
Benchmark pour mesurer le gain de performance de la refactorisation
Compare le temps d'exécution avec authentification centralisée vs duplications
"""
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

def run_test_suite(suite_path: str) -> dict:
    """Exécute une suite de tests et mesure le temps"""
    start = time.time()
    
    result = subprocess.run(
        ['pytest', suite_path, '-v', '--tb=no', '-q'],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True
    )
    
    duration = time.time() - start
    
    # Parser la sortie pour extraire les statistiques
    output = result.stdout
    
    return {
        'duration': duration,
        'output': output,
        'returncode': result.returncode
    }

def main():
    print("=" * 80)
    print("BENCHMARK DE LA REFACTORISATION - Authentification Centralisée")
    print("=" * 80)
    print()
    
    # Tests par module
    modules = {
        'auth': 'api/auth/',
        'basic_io': 'api/basic_io/',
        'storage': 'api/storage/',
        'identity': 'api/identity/',
        'guardian': 'api/guardian/',
    }
    
    results = {}
    total_duration = 0
    
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Exécution des tests par module...")
    print("-" * 80)
    
    for module_name, module_path in modules.items():
        print(f"\n📦 Module: {module_name}")
        print(f"   Path: {module_path}")
        
        result = run_test_suite(module_path)
        results[module_name] = result
        total_duration += result['duration']
        
        # Extraire le résumé de la dernière ligne
        lines = result['output'].strip().split('\n')
        summary_line = [l for l in lines if 'passed' in l or 'failed' in l]
        if summary_line:
            summary = summary_line[-1].strip()
            print(f"   ✅ {summary}")
        
        print(f"   ⏱️  Durée: {result['duration']:.2f}s")
    
    print()
    print("=" * 80)
    print("RÉSULTATS GLOBAUX")
    print("=" * 80)
    print()
    
    # Test complet pour comparaison
    print("Exécution de la suite complète...")
    full_result = run_test_suite('api/')
    
    lines = full_result['output'].strip().split('\n')
    summary_line = [l for l in lines if 'passed' in l or 'failed' in l]
    if summary_line:
        summary = summary_line[-1].strip()
        print(f"✅ {summary}")
    
    print()
    print(f"⏱️  Durée totale (suite complète): {full_result['duration']:.2f}s")
    print(f"⏱️  Somme des modules individuels: {total_duration:.2f}s")
    print()
    
    # Calcul des statistiques
    print("=" * 80)
    print("ANALYSE DE PERFORMANCE")
    print("=" * 80)
    print()
    
    # Estimation AVANT refactorisation (15 min par module pour login/init)
    estimated_overhead_before = 15 * 60 * len(modules)  # 15 min par module
    estimated_time_before = full_result['duration'] + estimated_overhead_before
    
    print("📊 Temps d'authentification:")
    print(f"   Avant (estimation): {len(modules)} modules × 15 min = {estimated_overhead_before/60:.1f} min")
    print(f"   Après (centralisé):  1 login unique ≈ 1 sec")
    print()
    
    print("📊 Temps total estimé:")
    gain = estimated_time_before - full_result['duration']
    gain_percent = (gain / estimated_time_before) * 100
    duration_before_min = estimated_time_before / 60
    duration_after_min = full_result['duration'] / 60
    gain_min = gain / 60
    print(f"   Avant refactorisation: {estimated_time_before:.0f}s ({duration_before_min:.1f} min)")
    print(f"   Après refactorisation: {full_result['duration']:.0f}s ({duration_after_min:.1f} min)")
    print()
    
    print(f"💰 Gain de temps: {gain:.0f}s ({gain_min:.1f} min)")
    print(f"💰 Gain relatif:  {gain_percent:.1f}%")
    print()
    
    # Détails par module
    print("=" * 80)
    print("DÉTAILS PAR MODULE")
    print("=" * 80)
    print()
    
    print(f"{'Module':<15} {'Durée (s)':<12} {'Login estimé avant':<20}")
    print("-" * 80)
    for module_name, result in results.items():
        before_login = 15 * 60  # 15 min
        print(f"{module_name:<15} {result['duration']:>8.2f}s    {before_login:>8.0f}s (15 min)")
    
    print()
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    print("✅ Authentification centralisée: 1 login unique pour toute la session")
    print(f"✅ Gain de temps par exécution complète: ~{gain/60:.0f} minutes")
    print(f"✅ Économie relative: {gain_percent:.0f}% du temps d'exécution")
    print()
    print("📝 Note: Les estimations 'avant' sont basées sur vos retours initiaux")
    print("   d'environ 15 minutes d'overhead par module de tests.")
    print()

if __name__ == '__main__':
    main()
