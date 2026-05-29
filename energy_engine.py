"""
ENERGY ENGINE - Moteur d'Analyse Énergétique Avancée
=====================================================

Calculs détaillés de l'énergie, efficacité, consommation et optimisation.
"""

import math


# ============================================================================
# 1. PROPRIÉTÉS THERMODYNAMIQUES ESTIMÉES
# ============================================================================

LATENT_HEATS_DB = {
    # Chaleurs latentes de vaporisation (kJ/kmol) à T_ebullition atm
    "Eau": 40660,
    "Éthanol": 38570,
    "Méthanol": 35270,
    "Propanol": 41940,
    "Butanol": 43290,
    "Acétone": 29100,
    "Benzène": 30800,
    "Toluène": 33500,
    "Chloroforme": 29700,
    "n-Hexane": 28900,
    "n-Heptane": 31800,
    "Cyclohexane": 30100,
    "Styrène": 37700,
    "Acide Acétique": 23700,
    "Dimethyl Ether": 21500,
}

BOILING_POINTS_DB = {
    # Points d'ébullition à P atm (°C)
    "Eau": 100.0,
    "Éthanol": 78.4,
    "Méthanol": 64.7,
    "Propanol": 97.0,
    "Butanol": 117.7,
    "Acétone": 56.5,
    "Benzène": 80.1,
    "Toluène": 110.6,
    "Chloroforme": 61.2,
    "n-Hexane": 68.7,
    "n-Heptane": 98.4,
    "Cyclohexane": 80.7,
    "Styrène": 145.2,
    "Acide Acétique": 118.1,
    "Dimethyl Ether": -24.8,
}

SPECIFIC_HEATS_DB = {
    # Capacités calorifiques molaires liquides (J/mol·K) à 25°C
    "Eau": 75.0,
    "Éthanol": 112.0,
    "Méthanol": 81.0,
    "Propanol": 142.0,
    "Butanol": 172.0,
    "Acétone": 125.0,
    "Benzène": 136.0,
    "Toluène": 167.0,
    "Chloroforme": 115.0,
    "n-Hexane": 183.0,
    "n-Heptane": 214.0,
    "Cyclohexane": 194.0,
}


def get_latent_heat(component_name):
    """Récupère la chaleur latente (kJ/kmol) d'un composé"""
    return LATENT_HEATS_DB.get(component_name, 32000.0)


def get_boiling_point(component_name):
    """Récupère le point d'ébullition (°C) à 1 atm"""
    return BOILING_POINTS_DB.get(component_name, 100.0)


def get_specific_heat(component_name):
    """Récupère la capacité calorifique (J/mol·K) du liquide"""
    return SPECIFIC_HEATS_DB.get(component_name, 100.0)


# ============================================================================
# 2. CALCUL DES CHARGES ÉNERGÉTIQUES
# ============================================================================

def calculate_condenser_duty(V_distillate, h_vap, conversion_factor=3600.0):
    """
    Calcule la charge du condenseur.
    
    Args:
        V_distillate: Flux de vapeur au condenseur (kmol/h)
        h_vap: Chaleur latente de vaporisation (kJ/kmol)
        conversion_factor: Conversion de kJ/h à kW (3600)
    
    Returns:
        Charge en kW
    """
    if V_distillate <= 0 or h_vap <= 0:
        return 0.0
    
    Q_cond = (V_distillate * h_vap) / conversion_factor
    return Q_cond


def calculate_reboiler_duty(V_boilup, h_vap, conversion_factor=3600.0):
    """
    Calcule la charge du rebouilleur.
    
    Args:
        V_boilup: Flux de vapeur généré (kmol/h)
        h_vap: Chaleur latente (kJ/kmol)
        conversion_factor: Conversion de kJ/h à kW
    
    Returns:
        Charge en kW
    """
    if V_boilup <= 0 or h_vap <= 0:
        return 0.0
    
    Q_reboil = (V_boilup * h_vap) / conversion_factor
    return Q_reboil


def calculate_energy_balance(Q_cond, Q_reboil, D_flow, B_flow, h_d, h_b, h_f, conversion=3600.0):
    """
    Bilan énergétique global : Q_reboil - Q_cond = enthalpy(D) + enthalpy(B) - enthalpy(F)
    
    Args:
        Q_cond, Q_reboil: Charges (kW)
        D_flow, B_flow, F_flow: Débits (kmol/h) - utilisés pour cohérence
        h_d, h_b, h_f: Enthalpies spécifiques (kJ/kmol)
        conversion: Facteur de conversion (3600 s/h)
    
    Returns:
        dict avec les détails du bilan
    """
    # Bilan enthalpe : Q_reboil - Q_cond = enthalpy_out - enthalpy_in
    # Enthalpy_out = D*h_d + B*h_b (kJ/h)
    # Enthalpy_in = F*h_f (kJ/h)
    
    # Les charges énergétiques sont en kW, donc on multiplie par 3600 pour revenir à kJ/h
    Q_net = (Q_reboil - Q_cond) * conversion
    
    # Vérification de cohérence (simplement pour diagnostics)
    return {
        "Q_net": Q_net,
        "Q_cond": Q_cond,
        "Q_reboil": Q_reboil

    }


# ============================================================================
# 3. ÉNERGIE MINIMALE (UNDERWOOD / SOREL)
# ============================================================================

def calculate_minimum_energy(R_min, D_flow, x_d, h_vap):
    """
    Calcule la consommation énergétique minimale théorique (au reflux minimum).
    
    Args:
        R_min: Reflux minimum (théorique)
        D_flow: Débit distillat (kmol/h)
        x_d: Composition du distillat
        h_vap: Chaleur latente (kJ/kmol)
    
    Returns:
        Charge minimale (kW)
    """
    V_min = (R_min + 1.0) * D_flow
    Q_min = calculate_reboiler_duty(V_min, h_vap)
    
    return Q_min


# ============================================================================
# 4. CONSOMMATION ÉNERGÉTIQUE SPÉCIFIQUE
# ============================================================================

def calculate_specific_energy(Q_total, F_flow):
    """
    Consommation énergétique spécifique (kWh/kmol alimenté).
    
    Args:
        Q_total: Charge totale rebouilleur (kW)
        F_flow: Débit alimentation (kmol/h)
    
    Returns:
        Consommation spécifique (kWh/kmol)
    """
    if F_flow <= 0:
        return 0.0
    return Q_total / F_flow


def calculate_specific_energy_product(Q_total, D_flow):
    """
    Consommation énergétique par unité de distillat produit (kWh/kmol).
    """
    if D_flow <= 0:
        return 0.0
    return Q_total / D_flow


# ============================================================================
# 5. EFFICACITÉ THERMIQUE (CARNOT-LIKE)
# ============================================================================

def calculate_thermal_efficiency(T_cond_c, T_reboil_c):
    """
    Efficacité thermique théorique basée sur Carnot.
    
    Args:
        T_cond_c: Température condenseur (°C)
        T_reboil_c: Température rebouilleur (°C)
    
    Returns:
        Efficacité (%) entre 0 et 100
    """
    if T_reboil_c <= T_cond_c:
        return 0.0
    
    T_c_k = T_cond_c + 273.15
    T_h_k = T_reboil_c + 273.15
    
    if T_h_k <= 0:
        return 0.0
    
    eta_carnot = (1.0 - T_c_k / T_h_k) * 100.0
    return max(0.0, min(100.0, eta_carnot))


def calculate_separation_energy_requirement(alpha, x_d, x_b, D_flow, h_vap):
    """
    Estimation de l'énergie théorique minimale pour la séparation.
    Basée sur l'entropie de mélange et la volatilité.
    
    Cette formule estime le travail thermodynamique minimal requis.
    
    Args:
        alpha: Volatilité relative moyenne
        x_d, x_b: Compositions
        D_flow: Débit distillat
        h_vap: Chaleur latente
    
    Returns:
        Énergie théorique minimale (kW)
    """
    R = 8.314  # J/(mol·K)
    T_op = 350.0  # Température de fonctionnement (K) - approximation
    
    # Calcul du travail entropique basé sur SHANNON entropy
    # S_mix = -R * (x*ln(x) + (1-x)*ln(1-x))
    def entropy_mix(x):
        if x <= 0 or x >= 1:
            return 0.0
        return -(x * math.log(x) + (1.0 - x) * math.log(1.0 - x))
    
    S_d = entropy_mix(x_d)
    S_b = entropy_mix(x_b)
    
    # Énergie théorique (approximation)
    W_sep = D_flow * R * T_op * (S_d + S_b) / (3600.0 * 1000.0)  # kW
    
    return abs(W_sep)


# ============================================================================
# 6. COÛTS ÉNERGÉTIQUES (ESTIMÉS)
# ============================================================================

def calculate_energy_cost(
    Q_reboil,
    energy_price_reboil=0.05,  # $/kWh (vapeur haute pression)
    energy_price_cond=0.02,    # $/kWh (eau de refroidissement)
    Q_cond=None,
    hours_per_year=8400
):
    """
    Estime le coût énergétique annuel.
    
    Args:
        Q_reboil: Charge rebouilleur (kW)
        energy_price_reboil: Coût vapeur ($/kWh)
        energy_price_cond: Coût refroidissement ($/kWh)
        Q_cond: Charge condenseur (kW) - si None, suppose Q_cond ≈ 0.85*Q_reboil
        hours_per_year: Heures opératoires annuelles (8400 h/an par défaut)
    
    Returns:
        dict avec coûts détaillés
    """
    if Q_cond is None:
        Q_cond = Q_reboil * 0.85
    
    annual_reboil = Q_reboil * energy_price_reboil * hours_per_year
    annual_cond = Q_cond * energy_price_cond * hours_per_year
    total_cost = annual_reboil + annual_cond
    
    return {
        "annual_reboiler_cost": round(annual_reboil, 2),
        "annual_condenser_cost": round(annual_cond, 2),
        "total_annual_cost": round(total_cost, 2),
        "daily_cost": round(total_cost / 365, 2),
        "hourly_cost": round(total_cost / hours_per_year, 2)
    }


# ============================================================================
# 7. OPTIMISATION ÉNERGÉTIQUE
# ============================================================================

def calculate_reflux_energy_tradeoff(R, R_min, D_flow, h_vap):
    """
    Analyse la relation entre reflux et consommation énergétique.
    
    Retourne une courbe du coût énergétique en fonction de R/R_min.
    """
    if R < R_min or R_min <= 0:
        return None
    
    # Consommation énergétique : augmente avec R
    V = (R + 1.0) * D_flow
    Q_energy = calculate_reboiler_duty(V, h_vap)
    
    # Nombre d'étages : diminue avec R (par Gilliland)
    # Approximation : N/N_min ≈ 1 + (R_min/R)^0.5 (forme générale)
    X = (R - R_min) / (R + 1.0)
    if X > 0:
        Y = 0.75 * (1.0 - X**0.5668)
        # N_min estimation à partir du ratio
    else:
        Y = 0.0
    
    return {
        "R": round(R, 2),
        "R_R_min_ratio": round(R / R_min, 2),
        "energy_cost": round(Q_energy, 1),
        "stages_reduction": round(Y * 100, 1)
    }


def find_optimal_reflux(R_min, R_max, D_flow, h_vap, capital_cost_per_stage=50000):
    """
    Trouve le reflux économique optimal (trade-off énergie vs capital).
    
    Modèle simplifié:
    - Coût annuel = Coût énergie + Coût capital amortisé
    - Coût énergie augmente avec R
    - Coût capital diminue avec R (moins d'étages)
    
    Args:
        R_min: Reflux minimum (thermodynamique)
        R_max: Reflux maximum à investiguer
        D_flow: Débit distillat
        h_vap: Chaleur latente
        capital_cost_per_stage: Coût capital d'un étage ($)
    
    Returns:
        dict avec R optimal et coûts
    """
    best_cost = float('inf')
    optimal_R = R_min * 1.2  # Par défaut, 1.2 fois R_min
    results = []
    
    # Scan de R_min * 1.05 à R_min * 3
    n_points = 30
    for i in range(n_points):
        R = R_min * 1.05 + (R_min * 2.95) * (i / n_points)
        
        # Coût énergétique
        V = (R + 1.0) * D_flow
        Q = calculate_reboiler_duty(V, h_vap)
        
        # Nombre d'étages approximé (inverse de la formule de Gilliland)
        X = (R - R_min) / (R + 1.0)
        if 0 < X < 1:
            Y = 0.75 * (1.0 - X**0.5668)
            N_theo = 5 * (1.0 + Y) / (1.0 - Y)  # Approximation
        else:
            N_theo = 5.0
        
        # Coûts annuels ($ par an)
        energy_cost_annual = Q * 0.05 * 8400  # Coût vapeur
        capital_cost_annual = capital_cost_per_stage * N_theo / 15  # Amortissement 15 ans
        total_cost = energy_cost_annual + capital_cost_annual
        
        results.append({
            "R": R,
            "ratio": R / R_min,
            "energy_cost": energy_cost_annual,
            "capital_cost": capital_cost_annual,
            "total_cost": total_cost,
            "n_stages": N_theo
        })
        
        if total_cost < best_cost:
            best_cost = total_cost
            optimal_R = R
    
    return {
        "optimal_R": round(optimal_R, 2),
        "optimal_ratio": round(optimal_R / R_min, 2),
        "minimum_cost": round(best_cost, 0),
        "curve": results
    }


# ============================================================================
# 8. RAPPORT D'ANALYSE ÉNERGÉTIQUE
# ============================================================================

def generate_energy_analysis_report(
    Q_cond, Q_reboil, Q_min, V_flow, D_flow, B_flow, F_flow,
    T_cond_c, T_reboil_c, R, R_min, h_vap, h_d, h_b, h_f
):
    """
    Génère un rapport complet d'analyse énergétique.
    """
    
    # Calculs dérivés
    eta_thermal = calculate_thermal_efficiency(T_cond_c, T_reboil_c)
    spec_energy_feed = calculate_specific_energy(Q_reboil, F_flow)
    spec_energy_product = calculate_specific_energy_product(Q_reboil, D_flow)
    
    # Comparaison à la théorie
    ratio_to_min = Q_reboil / Q_min if Q_min > 0 else 1.0
    
    # Coûts estimés
    costs = calculate_energy_cost(Q_reboil)
    
    report = {
        "charges": {
            "condenser_duty": round(Q_cond, 1),
            "reboiler_duty": round(Q_reboil, 1),
            "minimum_duty": round(Q_min, 1),
            "duty_ratio_to_min": round(ratio_to_min, 2)
        },
        "efficiency": {
            "thermal_efficiency_percent": round(eta_thermal, 1),
            "duty_ratio_reboil_cond": round(Q_reboil / Q_cond if Q_cond > 0 else 1.0, 2)
        },
        "specific_consumption": {
            "per_feed_kmol": round(spec_energy_feed, 2),
            "per_product_kmol": round(spec_energy_product, 2)
        },
        "economics": costs,
        "temperatures": {
            "condenser": round(T_cond_c, 1),
            "reboiler": round(T_reboil_c, 1),
            "temperature_difference": round(T_reboil_c - T_cond_c, 1)
        },
        "industrial_kpis": {
            "energy_integration_score": round((1.0 / ratio_to_min) * 100, 1) if ratio_to_min > 0 else 0.0
        }
    }
    
    return report


# ============================================================================
# 9. DONNÉES POUR GRAPHIQUES
# ============================================================================

def generate_energy_curve_data(Q_values, R_values, alpha_values):
    """Génère les données pour les courbes énergétiques"""
    data = []
    for i, (Q, R, alpha) in enumerate(zip(Q_values, R_values, alpha_values)):
        data.append({
            "step": i,
            "Q": round(Q, 1),
            "R": round(R, 2),
            "alpha": round(alpha, 2)
        })
    return data
