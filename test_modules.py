#!/usr/bin/env python
"""
Test Script - Vérification de l'intégrité des modules de distillation
"""

import sys
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def test_module(name, module_path):
    """Test l'import d'un module"""
    try:
        __import__(module_path)
        print(f"[OK] {name:30s} - OK")
        return True
    except Exception as e:
        print(f"[ERREUR] {name:30s} - ERREUR: {str(e)[:80]}")
        traceback.print_exc()
        return False

def main():
    print("=" * 80)
    print("TEST D'INTÉGRITÉ DES MODULES DE DISTILLATION")
    print("=" * 80)
    print()

    modules = [
        ("Moteur de Validation", "validation_engine"),
        ("Moteur d'Énergie", "energy_engine"),
        ("Moteur de Distillation", "distillation_engine"),
        ("Moteur Thermodynamique", "thermo_engine"),
        ("Optimisation", "optimization_engine"),
        ("Diagnostic", "diagnostic_engine"),
        ("Modèles ORM", "models"),
        ("Application Flask", "app"),
    ]

    results = []
    for name, path in modules:
        results.append(test_module(name, path))

    print()
    print("=" * 80)
    success_count = sum(results)
    total_count = len(results)
    
    if success_count == total_count:
        print(f"[OK] SUCCES : {success_count}/{total_count} modules importes avec succes")
        print()
        print("PRÊT POUR LA PRODUCTION !")
        return 0
    else:
        print(f"[ERREUR] AVERTISSEMENT : {success_count}/{total_count} modules OK, {total_count - success_count} erreur(s)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
