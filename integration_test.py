#!/usr/bin/env python
"""
INTEGRATION TEST - Test d'Intégration Complète
===============================================

Teste le pipeline complet: saisie → simulation → validation → énergie
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ajout du répertoire au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("\n" + "="*80)
    print("TEST D'INTÉGRATION - MODULE DISTILLATION AVANCÉE")
    print("="*80 + "\n")
    
    # 1. Test des imports
    print("[1/5] Import des modules...")
    import distillation_engine as dist_eng
    import validation_engine as val_eng
    import energy_engine as en_eng
    from models import Component
    print("✓ Imports réussis\n")
    
    # 2. Création de composants test (sans BD)
    print("[2/5] Création de composants de test...")
    class MockComponent:
        def __init__(self, name, antoine_A, antoine_B, antoine_C, polarity):
            self.name = name
            self.antoine_A = antoine_A
            self.antoine_B = antoine_B
            self.antoine_C = antoine_C
            self.polarity = polarity
    
    # Eau et Éthanol (système classique)
    water = MockComponent("Eau", 8.07131, 1730.63, 233.426, "polar")
    ethanol = MockComponent("Éthanol", 8.11572, 1425.26, 230.932, "polar")
    print(f"✓ Composants créés: {water.name}, {ethanol.name}\n")
    
    # 3. Test de simulation
    print("[3/5] Exécution simulation distillation...")
    sim_result = dist_eng.calculate_distillation_advanced(
        F_flow=100.0,        # kmol/h
        x_f=0.40,            # 40% éthanol
        x_d=0.85,            # 85% éthanol distillat
        x_b=0.05,            # 5% éthanol résidu
        R=2.0,               # Reflux = 2
        q=1.0,               # Liquide saturé
        P_kpa=101.325,       # Pression atmosphérique
        comp1=ethanol,       # Plus volatil
        comp2=water,         # Moins volatil
        model_type="NRTL",
        tray_eff=0.75
    )
    
    if sim_result.get("success"):
        print(f"✓ Simulation réussie")
        print(f"  - N_min: {sim_result['N_min']:.2f} étages")
        print(f"  - R_min: {sim_result['R_min']:.2f}")
        print(f"  - N_théo: {sim_result['N_stages']} étages")
        print(f"  - Débit D: {sim_result['flows']['D']:.1f} kmol/h")
        print(f"  - Débit B: {sim_result['flows']['B']:.1f} kmol/h\n")
    else:
        print(f"✗ Simulation échouée: {sim_result.get('error')}\n")
        sys.exit(1)
    
    # 4. Test de validation
    print("[4/5] Validation physique et thermodynamique...")
    validation = val_eng.validate_distillation_complete(
        F_flow=100.0,
        x_f=0.40,
        x_d=0.85,
        x_b=0.05,
        D_flow=sim_result['flows']['D'],
        B_flow=sim_result['flows']['B'],
        R=sim_result.get('R_used', 2.0),
        R_min=sim_result['R_min'],
        q=1.0,
        P_kpa=101.325,
        N_min=sim_result['N_min'],
        N_theo=sim_result['N_stages'],
        N_reel=sim_result['N_real'],
        Q_cond=sim_result['energy']['Q_condenser'],
        Q_reboil=sim_result['energy']['Q_reboiler'],
        V_flow=sim_result['energy'].get('V_flow', sim_result['flows'].get('V_rect', 0.0)),
        xy_curve=sim_result.get('xy_curve'),
        tray_eff=0.75
    )
    
    if validation.is_valid:
        print("✓ Validation réussie")
        print(f"  - Vérifications physiques: {len(validation.physics_checks)}")
        print(f"  - Avertissements: {len(validation.warnings)}")
        print(f"  - Notes: {len(validation.info)}\n")
    else:
        print(f"✗ Validation échouée:")
        for err in validation.errors:
            print(f"  - {err['message']}")
        print()
        sys.exit(1)
    
    # 5. Test d'analyse énergétique
    print("[5/5] Analyse énergétique...")
    
    # Calcul charge minimum
    Q_min = en_eng.calculate_minimum_energy(
        R_min=sim_result['R_min'],
        D_flow=sim_result['flows']['D'],
        x_d=0.85,
        h_vap=en_eng.get_latent_heat(ethanol.name)
    )
    
    # Efficacité thermique deja fournie par le moteur avance.
    eta = sim_result['energy'].get('thermal_efficiency', 0.0)
    
    # Rapports
    ratio_to_min = sim_result['energy']['Q_reboiler'] / Q_min if Q_min > 0 else 1.0
    
    print(f"✓ Analyse énergétique")
    print(f"  - Q_condenseur: {sim_result['energy']['Q_condenser']:.1f} kW")
    print(f"  - Q_rebouilleur: {sim_result['energy']['Q_reboiler']:.1f} kW")
    print(f"  - Q_minimum: {Q_min:.1f} kW")
    print(f"  - Ratio Q/Q_min: {ratio_to_min:.2f}")
    print(f"  - Efficacité thermique: {eta:.1f}%\n")
    
    # Résumé final
    print("="*80)
    print("✓ TOUS LES TESTS PASSÉS AVEC SUCCÈS")
    print("="*80)
    print()
    print("RÉSULTATS SYNTHÉTIQUES:")
    print(f"  Composants testés: {ethanol.name} / {water.name}")
    print(f"  Spécifications: xF={0.40}, xD={0.85}, xB={0.05}")
    print(f"  Nombre d'étages: {sim_result['N_stages']:.1f} théoriques, {sim_result['N_real']:.1f} réels")
    print(f"  Consommation énergétique: {sim_result['energy']['Q_reboiler']:.1f} kW")
    print(f"  Faisabilité: {'✓ OUI' if validation.is_valid else '✗ NON'}")
    print()
    print("MESSAGE SYSTÈME:")
    print('  "Tous les résultats sont calculés sur la base de modèles scientifiques')
    print('   reconnus en génie des procédés et vérifiés par cohérence physique')
    print('   et thermodynamique."')
    print()
    
    sys.exit(0)

except Exception as e:
    print(f"\n✗ ERREUR FATALE: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
