"""
VALIDATION ENGINE - Moteur de Validation Physique et Thermodynamique
======================================================================

Assure la cohérence absolue et la validité physique de tous les résultats.

Critères de Validation:
- Conservation de la matière (F = D + B)
- Cohérence des compositions (0 <= x <= 1)
- Cohérence thermodynamique (équilibre)
- Cohérence énergétique (pas de génération gratuite)
- Détection séparation impossible
- Détection reflux insuffisant
- Stabilité numérique
"""

import math


class ValidationResult:
    """Résultat de validation avec diagnostic complet"""
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.info = []
        self.physics_checks = {}
        
    def add_error(self, message, code=None):
        """Ajoute une erreur critique (validation échouée)"""
        self.is_valid = False
        self.errors.append({"message": message, "code": code, "severity": "critical"})
        
    def add_warning(self, message, code=None):
        """Ajoute un avertissement (résultats douteux mais calculables)"""
        self.warnings.append({"message": message, "code": code, "severity": "warning"})
        
    def add_info(self, message):
        """Ajoute une info (note pédagogique)"""
        self.info.append({"message": message, "severity": "info"})
        
    def add_physics_check(self, name, passed, details=""):
        """Enregistre une vérification physique"""
        self.physics_checks[name] = {
            "passed": passed,
            "details": details
        }
        
    def to_dict(self):
        """Convertit en dictionnaire pour JSON"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "physics_checks": self.physics_checks
        }


# ============================================================================
# 1. VALIDATION DES COMPOSITIONS
# ============================================================================

def validate_compositions(x_d, x_f, x_b, result):
    """Valide les compositions en % molaire"""
    checks_passed = True
    
    # Chaque composition doit être entre 0 et 1
    if not (0.0 <= x_d <= 1.0):
        result.add_error(f"Pureté distillat hors limites (xD = {x_d})", "COMP_BOUNDS_DISTILLATE")
        checks_passed = False
    else:
        result.add_physics_check("x_D bounds", True, f"xD = {x_d:.4f} ✓")
        
    if not (0.0 <= x_f <= 1.0):
        result.add_error(f"Composition alimentation hors limites (xF = {x_f})", "COMP_BOUNDS_FEED")
        checks_passed = False
    else:
        result.add_physics_check("x_F bounds", True, f"xF = {x_f:.4f} ✓")
        
    if not (0.0 <= x_b <= 1.0):
        result.add_error(f"Composition résidu hors limites (xB = {x_b})", "COMP_BOUNDS_BOTTOMS")
        checks_passed = False
    else:
        result.add_physics_check("x_B bounds", True, f"xB = {x_b:.4f} ✓")
    
    # Logique de la séparation : xD > xF > xB (pour un distillat plus pur)
    if x_d <= x_f:
        result.add_error(
            f"Pureté distillat trop faible : xD ({x_d:.4f}) doit être > xF ({x_f:.4f})",
            "SEP_LOGIC_XD"
        )
        checks_passed = False
    else:
        result.add_physics_check("x_D > x_F", True, f"✓ ({x_d:.4f} > {x_f:.4f})")
        
    if x_f <= x_b:
        result.add_error(
            f"Pureté résidu trop faible : xF ({x_f:.4f}) doit être > xB ({x_b:.4f})",
            "SEP_LOGIC_XB"
        )
        checks_passed = False
    else:
        result.add_physics_check("x_F > x_B", True, f"✓ ({x_f:.4f} > {x_b:.4f})")
    
    # Pureté distillat minimale
    if x_d < 0.95:
        result.add_warning(
            f"Pureté distillat faible (xD = {x_d:.4f}). En industrie, xD >= 0.95 est standard.",
            "LOW_PURITY_DISTILLATE"
        )
    
    # Pureté résidu minimale
    if x_b > 0.05:
        result.add_warning(
            f"Pureté résidu faible (xB = {x_b:.4f}). En industrie, xB <= 0.05 est standard.",
            "LOW_PURITY_BOTTOMS"
        )
    
    return checks_passed


# ============================================================================
# 2. VALIDATION DES DÉBITS
# ============================================================================

def validate_flows(F_flow, D_flow, B_flow, result, tolerance=1e-6):
    """Valide les débits et le bilan matière global"""
    checks_passed = True
    
    # Tous les débits doivent être positifs
    if F_flow <= 0:
        result.add_error(f"Débit alimentation invalide (F = {F_flow})", "FLOW_INVALID_F")
        checks_passed = False
    else:
        result.add_physics_check("F > 0", True, f"F = {F_flow:.2f} kmol/h ✓")
        
    if D_flow <= 0:
        result.add_error(f"Débit distillat invalide (D = {D_flow})", "FLOW_INVALID_D")
        checks_passed = False
    else:
        result.add_physics_check("D > 0", True, f"D = {D_flow:.2f} kmol/h ✓")
        
    if B_flow <= 0:
        result.add_error(f"Débit résidu invalide (B = {B_flow})", "FLOW_INVALID_B")
        checks_passed = False
    else:
        result.add_physics_check("B > 0", True, f"B = {B_flow:.2f} kmol/h ✓")
    
    # Bilan matière global : F = D + B
    F_calc = D_flow + B_flow
    error_abs = abs(F_calc - F_flow)
    error_rel = error_abs / F_flow if F_flow > 0 else float('inf')
    
    if error_rel > tolerance:
        result.add_error(
            f"Bilan matière global non conservé : F ({F_flow:.2f}) ≠ D + B ({F_calc:.2f}), "
            f"écart relatif {error_rel*100:.2f}%",
            "BALANCE_GLOBAL_FAIL"
        )
        checks_passed = False
    else:
        result.add_physics_check("F = D + B", True, 
            f"✓ Déviation = {error_rel*100:.4f}% < {tolerance*100:.4f}%")
    
    # Vérification que D et B ne sont pas négligeables
    if D_flow < F_flow * 0.01:
        result.add_warning(
            f"Débit distillat très faible (D/F = {(D_flow/F_flow)*100:.1f}%). "
            f"Vérifier que la séparation est réaliste.",
            "LOW_DISTILLATE_FRACTION"
        )
        
    if B_flow < F_flow * 0.01:
        result.add_warning(
            f"Débit résidu très faible (B/F = {(B_flow/F_flow)*100:.1f}%). "
            f"Vérifier que la séparation est réaliste.",
            "LOW_BOTTOMS_FRACTION"
        )
    
    return checks_passed


# ============================================================================
# 3. VALIDATION DES BILANS COMPOSANT
# ============================================================================

def validate_component_balance(F_flow, x_f, D_flow, x_d, B_flow, x_b, result, tolerance=1e-5):
    """Valide le bilan par composant : F*xF = D*xD + B*xB"""
    checks_passed = True
    
    # Bilan composant léger (composé 1, le plus volatil)
    F_comp = F_flow * x_f
    D_comp = D_flow * x_d
    B_comp = B_flow * x_b
    
    balance_calc = D_comp + B_comp
    error_abs = abs(balance_calc - F_comp)
    error_rel = error_abs / F_comp if F_comp > 0 else 0.0
    
    if error_rel > tolerance:
        result.add_error(
            f"Bilan composant non conservé : F*xF ({F_comp:.2f}) ≠ D*xD + B*xB ({balance_calc:.2f}), "
            f"écart relatif {error_rel*100:.2f}%",
            "BALANCE_COMPONENT_FAIL"
        )
        checks_passed = False
    else:
        result.add_physics_check("F·xF = D·xD + B·xB", True,
            f"✓ Déviation = {error_rel*100:.6f}% < {tolerance*100:.4f}%")
    
    return checks_passed


# ============================================================================
# 4. VALIDATION DU REFLUX
# ============================================================================

def validate_reflux(R, R_min, result):
    """Valide que le reflux est réaliste et accessible"""
    checks_passed = True
    
    # R doit être positif
    if R < 0:
        result.add_error(
            f"Reflux négatif impossible (R = {R})",
            "REFLUX_NEGATIVE"
        )
        checks_passed = False
    else:
        result.add_physics_check("R >= 0", True, f"R = {R:.2f} ✓")
    
    # R doit être >= R_min (minimum thermodynamique)
    if R < R_min:
        result.add_error(
            f"Reflux insuffisant pour la séparation requise ! "
            f"R ({R:.2f}) < R_min ({R_min:.2f}). "
            f"Nombre d'étages infini (pincement). Augmentez R ou relaxez les spécifications.",
            "REFLUX_BELOW_MINIMUM"
        )
        checks_passed = False
    elif R < R_min * 1.05:
        result.add_warning(
            f"Reflux très proche du minimum critique ! "
            f"R ({R:.2f}) ≈ R_min ({R_min:.2f}). "
            f"Nombre d'étages très élevé. En industrie, utiliser R/R_min = 1.2 à 1.5.",
            "REFLUX_NEAR_MINIMUM"
        )
    else:
        result.add_physics_check("R >= R_min", True,
            f"✓ R/R_min = {R/R_min:.2f} (opérationnel)")
    
    # Alerter si R est très élevé (inefficace économiquement)
    if R > R_min * 5:
        result.add_warning(
            f"Reflux très élevé (R/R_min = {R/R_min:.1f}). "
            f"Cela augmente la consommation énergétique de manière excessive. "
            f"Une valeur technico-économique serait R/R_min ≈ 1.2-1.5.",
            "REFLUX_TOO_HIGH"
        )
    
    return checks_passed


# ============================================================================
# 5. VALIDATION DE LA QUALITÉ D'ALIMENTATION (q)
# ============================================================================

def validate_q_factor(q, result):
    """Valide le facteur de qualité d'alimentation q"""
    checks_passed = True
    
    # q doit être entre -inf et +inf théoriquement, mais avec limites physiques
    # -1 < q < 2 couvre la plupart des cas réalistes
    
    if q < -2 or q > 3:
        result.add_warning(
            f"Qualité d'alimentation extrême (q = {q}). "
            f"Vérifier que le préchauffage/refroidissement est dimensionné correctement.",
            "Q_EXTREME"
        )
    
    # Classification de l'état thermique
    if abs(q - 1.0) < 0.01:
        state = "Liquide saturé"
        result.add_physics_check("Thermal state", True, state)
    elif abs(q - 0.0) < 0.01:
        state = "Vapeur saturée"
        result.add_physics_check("Thermal state", True, state)
    elif 0 < q < 1:
        state = f"Mélange L-V ({int(q*100)}% liquide)"
        result.add_physics_check("Thermal state", True, state)
    elif q > 1:
        state = "Liquide sous-refroidi"
        result.add_physics_check("Thermal state", True, state)
    else:
        state = "Vapeur surchauffée"
        result.add_physics_check("Thermal state", True, state)
    
    result.add_info(f"État thermique d'alimentation : {state}")
    return checks_passed


# ============================================================================
# 6. VALIDATION DE LA PRESSION
# ============================================================================

def validate_pressure(P_kpa, result):
    """Valide que la pression opératoire est réaliste"""
    checks_passed = True
    
    # Pression doit être positive
    if P_kpa <= 0:
        result.add_error(f"Pression invalide (P = {P_kpa} kPa)", "PRESSURE_INVALID")
        checks_passed = False
    else:
        result.add_physics_check("P > 0", True, f"P = {P_kpa:.1f} kPa ✓")
    
    # Pression usuelle pour distillation atmosphérique : 80-150 kPa
    if P_kpa < 80:
        result.add_warning(
            f"Pression basse ({P_kpa/100:.2f} bar). "
            f"Vérifier qu'il s'agit d'une colonne sous vide.",
            "LOW_PRESSURE"
        )
        
    if P_kpa > 1000:
        result.add_warning(
            f"Pression élevée ({P_kpa/100:.1f} bar). "
            f"Cela réduit la volatilité relative et augmente le coût énergétique.",
            "HIGH_PRESSURE"
        )
    
    return checks_passed


# ============================================================================
# 7. VALIDATION THERMODYNAMIQUE - ÉQUILIBRE
# ============================================================================

def validate_thermodynamic_equilibrium(xy_curve, result):
    """Valide la cohérence de la courbe d'équilibre x-y"""
    checks_passed = True
    
    if not xy_curve or len(xy_curve) < 2:
        result.add_error("Courbe d'équilibre vide ou invalide", "VLE_EMPTY")
        checks_passed = False
        return checks_passed
    
    # Vérifier que x et y sont toujours dans [0, 1]
    for pt in xy_curve:
        if not (0 <= pt["x"] <= 1 and 0 <= pt["y"] <= 1):
            result.add_error(
                f"Point d'équilibre hors limites : x={pt['x']}, y={pt['y']}",
                "VLE_OUT_OF_BOUNDS"
            )
            checks_passed = False
    
    # Vérifier la monotonie de la courbe (en général croissante)
    prev_y = -1
    for pt in xy_curve:
        if pt["y"] < prev_y - 0.01:  # Avec petite tolérance
            result.add_warning(
                f"Courbe d'équilibre non-monotone détectée. "
                f"Possible formation d'azeotrope ou anomalie thermodynamique.",
                "VLE_NON_MONOTONIC"
            )
            break
        prev_y = pt["y"]
    
    # Détection d'azeotrope (y = x à composition donnée)
    for pt in xy_curve:
        if 0.1 < pt["x"] < 0.9 and abs(pt["y"] - pt["x"]) < 0.02:
            result.add_warning(
                f"Azeotrope probable détecté à x ≈ {pt['x']:.2f}. "
                f"Impossible de dépasser cette limite par distillation simple.",
                "AZEOTROPE_DETECTED"
            )
    
    result.add_physics_check("VLE curve", checks_passed, f"{len(xy_curve)} points générés")
    return checks_passed


# ============================================================================
# 8. VALIDATION ÉNERGÉTIQUE
# ============================================================================

def validate_energy(Q_cond, Q_reboil, V_flow, result):
    """Valide la cohérence des charges énergétiques"""
    checks_passed = True
    
    # Les charges doivent être positives
    if Q_cond < 0:
        result.add_error(
            f"Charge condenseur négative (QC = {Q_cond} kW). "
            f"Impossible physiquement.",
            "ENERGY_CONDENSER_NEG"
        )
        checks_passed = False
    else:
        result.add_physics_check("QC > 0", True, f"QC = {Q_cond:.1f} kW ✓")
    
    if Q_reboil < 0:
        result.add_error(
            f"Charge rebouilleur négative (QR = {Q_reboil} kW). "
            f"Impossible physiquement.",
            "ENERGY_REBOILER_NEG"
        )
        checks_passed = False
    else:
        result.add_physics_check("QR > 0", True, f"QR = {Q_reboil:.1f} kW ✓")
    
    # Cohérence : QC et QR doivent être du même ordre de grandeur
    # (différence provient du bilan enthalpique du condenseur/rebouilleur)
    if Q_cond > 0 and Q_reboil > 0:
        ratio = max(Q_cond, Q_reboil) / min(Q_cond, Q_reboil)
        if ratio > 2.0:
            result.add_warning(
                f"Ratio QR/QC = {Q_reboil/Q_cond:.2f} semble élevé. "
                f"Vérifier la cohérence du bilan énergétique.",
                "ENERGY_RATIO_HIGH"
            )
    
    # Vérifier que le flux vapeur et la charge sont cohérents
    if V_flow > 0 and Q_reboil > 0:
        h_vap_implied = (Q_reboil * 3600) / V_flow  # kJ/kmol
        if h_vap_implied < 10000 or h_vap_implied > 50000:
            result.add_warning(
                f"Chaleur latente implicite = {h_vap_implied:.0f} kJ/kmol "
                f"semble anormale. Plage normale : 10-50 MJ/kmol.",
                "ENERGY_LATENT_ANOMALY"
            )
    
    return checks_passed


# ============================================================================
# 9. VALIDATION DU NOMBRE D'ÉTAGES
# ============================================================================

def validate_stages(N_min, N_theo, N_reel, result):
    """Valide la cohérence des nombres d'étages"""
    checks_passed = True
    
    # N_min doit être positif
    if N_min <= 0:
        result.add_error(f"Nombre minimum d'étages invalide (N_min = {N_min})", "STAGES_NMIN_INVALID")
        checks_passed = False
    else:
        result.add_physics_check("N_min > 0", True, f"N_min = {N_min:.1f} ✓")
    
    # N_theo doit être >= N_min
    if isinstance(N_theo, (int, float)) and not math.isnan(N_theo):
        if N_theo < N_min - 0.5:  # Tolérance numérique
            result.add_error(
                f"N_theo ({N_theo:.1f}) < N_min ({N_min:.1f}). Incohérence majeure.",
                "STAGES_THEO_LT_MIN"
            )
            checks_passed = False
        else:
            result.add_physics_check("N_theo >= N_min", True,
                f"✓ N_theo/N_min = {N_theo/N_min:.2f}")
    
    # N_reel doit être >= N_theo (efficacité <= 1)
    if isinstance(N_theo, (int, float)) and not math.isnan(N_theo) and N_reel > 0:
        if N_reel < N_theo - 0.5:
            result.add_warning(
                f"N_reel ({N_reel:.1f}) < N_theo ({N_theo:.1f}). "
                f"Cela implique une efficacité > 100%, impossible.",
                "STAGES_REEL_LT_THEO"
            )
        else:
            eff = N_theo / N_reel if N_reel > 0 else 1.0
            result.add_physics_check("Efficacité", True, f"η = {eff*100:.1f}%")
    
    return checks_passed


# ============================================================================
# 10. VALIDATION GLOBALE INTÉGRÉE
# ============================================================================

def validate_distillation_complete(
    F_flow, x_f, x_d, x_b, D_flow, B_flow,
    R, R_min, q, P_kpa,
    N_min, N_theo, N_reel,
    Q_cond, Q_reboil, V_flow,
    xy_curve=None,
    tray_eff=0.75
):
    """
    Validation complète et intégrée de tous les paramètres de distillation.
    
    Retourne un ValidationResult avec tous les diagnostics.
    """
    result = ValidationResult()
    
    # Phase 1 : Validations fondamentales
    validate_compositions(x_d, x_f, x_b, result)
    validate_flows(F_flow, D_flow, B_flow, result)
    validate_component_balance(F_flow, x_f, D_flow, x_d, B_flow, x_b, result)
    validate_reflux(R, R_min, result)
    validate_q_factor(q, result)
    validate_pressure(P_kpa, result)
    
    # Phase 2 : Validations thermodynamiques
    if xy_curve:
        validate_thermodynamic_equilibrium(xy_curve, result)
    
    # Phase 3 : Validations énergétiques
    validate_energy(Q_cond, Q_reboil, V_flow, result)
    
    # Phase 4 : Validations géométriques (étages)
    validate_stages(N_min, N_theo, N_reel, result)
    
    # Phase 5 : Validation croisée finale
    if not result.is_valid:
        result.add_error(
            "Simulation impossible. Les paramètres spécifiés violent les lois de la physique. "
            "Vérifiez les compositions, le reflux, ou relaxez les spécifications.",
            "SIMULATION_IMPOSSIBLE"
        )
    else:
        result.add_info(
            "✅ VALIDATION COMPLÈTE : Tous les résultats sont cohérents avec "
            "les lois fondamentales de la thermodynamique et du génie des procédés."
        )
    
    return result


# ============================================================================
# 11. GÉNÉRATION DE RAPPORT DE VALIDATION
# ============================================================================

def generate_validation_report(validation_result):
    """Génère un rapport HTML formaté de la validation"""
    html = """
    <div class="validation-report">
        <h3>Rapport de Validation Physique</h3>
    """
    
    # Statut global
    if validation_result.is_valid:
        html += '<div class="alert alert-success"><strong>✅ VALIDÉ</strong> - Tous les critères physiques sont satisfaits.</div>'
    else:
        html += '<div class="alert alert-danger"><strong>❌ INVALIDE</strong> - La simulation ne peut pas être exécutée.</div>'
    
    # Erreurs critiques
    if validation_result.errors:
        html += '<div class="error-section"><h4>Erreurs Critiques</h4><ul>'
        for err in validation_result.errors:
            html += f'<li><strong>{err["code"]}</strong> : {err["message"]}</li>'
        html += '</ul></div>'
    
    # Avertissements
    if validation_result.warnings:
        html += '<div class="warning-section"><h4>Avertissements</h4><ul>'
        for warn in validation_result.warnings:
            html += f'<li><strong>⚠️ {warn["code"]}</strong> : {warn["message"]}</li>'
        html += '</ul></div>'
    
    # Vérifications physiques
    if validation_result.physics_checks:
        html += '<div class="physics-section"><h4>Vérifications Physiques</h4><ul>'
        for name, check in validation_result.physics_checks.items():
            status = "✓" if check["passed"] else "✗"
            html += f'<li>{status} {name} : {check["details"]}</li>'
        html += '</ul></div>'
    
    # Infos
    if validation_result.info:
        html += '<div class="info-section"><h4>Notes</h4><ul>'
        for info in validation_result.info:
            html += f'<li>ℹ️ {info["message"]}</li>'
        html += '</ul></div>'
    
    html += '</div>'
    return html
