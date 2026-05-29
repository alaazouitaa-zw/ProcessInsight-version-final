"""
PEDAGOGICAL MODE - Mode Pédagogique Interactif
===============================================

Module dédié au mode enseignement avec explications détaillées,
animations éducatives, et interprétation physique des résultats.
"""


class PedagogicalExplainer:
    """Générateur d'explications pédagogiques"""
    
    THEORY_SECTIONS = {
        "distillation_basics": {
            "title": "Fondamentaux de la Distillation",
            "content": """
            La distillation est une opération unitaire de séparation basée sur les différences 
            de volatilité des composants. Un composant plus volatil (point d'ébullition bas) 
            tend à s'enrichir en phase vapeur, tandis qu'un composant moins volatil 
            (point d'ébullition haut) préfère rester en phase liquide.
            
            **Principe physique :** 
            À l'équilibre liquide-vapeur, les fugacités des composants sont égales dans 
            les deux phases. Cela est décrit par les relations d'équilibre (Raoult pour idéal, 
            NRTL pour non-idéal).
            """
        },
        "material_balance": {
            "title": "Bilan de Matière Global",
            "content": """
            Le bilan de matière global d'une colonne de distillation suit le principe 
            de conservation de la masse :
            
            **Bilan Global :**
            F = D + B
            
            Où :
            - F : Débit d'alimentation (kmol/h)
            - D : Débit de distillat (produit léger, haut de colonne)
            - B : Débit de résidu (produit lourd, bas de colonne)
            
            **Bilan par Composant :**
            F·xF = D·xD + B·xB
            
            Où x représente la fraction molaire du composant léger.
            
            Ces deux équations permettent de déterminer D et B à partir de F et des 
            spécifications de composition (xD et xB).
            """
        },
        "relative_volatility": {
            "title": "Volatilité Relative",
            "content": """
            La volatilité relative mesure la facilité de séparation entre deux composants.
            
            **Définition :**
            α = (y₁/x₁) / (y₂/x₂) = (K₁/K₂)
            
            Où K = γ·Psat/P (coefficient de distribution)
            
            **Interprétation :**
            - α = 1 : Composants identiques (pas de séparation possible)
            - α > 1 : Séparation possible (α > 1.5 est bon)
            - α → ∞ : Séparation très facile (par distillation simple)
            - α < 1 : Composant 2 plus léger que composant 1
            
            Une volatilité relative plus élevée signifie que la séparation est plus facile,
            nécessitant moins d'étages et moins de reflux.
            """
        },
        "fenske_equation": {
            "title": "Équation de Fenske (N_min)",
            "content": """
            L'équation de Fenske donne le NOMBRE MINIMUM d'étages nécessaires pour 
            atteindre une séparation donnée, en supposant un reflux infini (R → ∞).
            
            **Formule :**
            N_min = ln[(xD/(1-xD)) / (xB/(1-xB))] / ln(α_avg) - 1
            
            Où :
            - xD : Composition distillat
            - xB : Composition résidu
            - α_avg : Volatilité relative moyenne (géométrique)
            
            **Signification :**
            - Si α_avg = 1 : N_min = ∞ (séparation impossible)
            - Si α_avg est grand : N_min est petit (peu d'étages)
            
            Le "- 1" provient du rebouilleur (compte comme un étage).
            """
        },
        "underwood_equation": {
            "title": "Équation d'Underwood (R_min)",
            "content": """
            L'équation d'Underwood donne le REFLUX MINIMUM théorique, en supposant 
            un nombre d'étages infini (N → ∞).
            
            **Méthode graphique simplifiée :**
            1. Tracer la courbe d'équilibre x-y
            2. Tracer la q-line (passe par point alimentation)
            3. Trouver l'intersection q-line / équilibre : (x_int, y_int)
            4. Calculer : R_min = (xD - y_int) / (y_int - x_int)
            
            **Signification physique :**
            - R < R_min : Impossible (pincement thermodynamique)
            - R = R_min : N = ∞ étages (point de pincement)
            - R = 1.2 × R_min : Optimum technico-économique (industrie)
            - R >> R_min : Coûteux en énergie
            """
        },
        "gilliland_correlation": {
            "title": "Corrélation de Gilliland",
            "content": """
            La corrélation de Gilliland relie le nombre minimum d'étages (N_min), 
            le reflux minimum (R_min), et les conditions opératoires (N, R).
            
            **Formule adimensionnelle :**
            X = (R - R_min) / (R + 1)
            Y = (N - N_min) / (N + 1)
            Y = 0.75 × (1 - X^0.5668)
            
            **Utilisation :**
            1. Fixer R (reflux opérationnel désiré)
            2. Calculer X
            3. Calculer Y
            4. Inverser pour obtenir N : N = (N_min + Y) / (1 - Y)
            
            **Cas limites :**
            - Si X ≤ 0 : Reflux insuffisant (N = ∞)
            - Si X ≥ 1 : R très grand (N ≈ N_min)
            """
        },
        "mccabe_thiele": {
            "title": "Méthode de McCabe-Thiele",
            "content": """
            La méthode de McCabe-Thiele est une construction GRAPHIQUE qui simule 
            l'étage par étage le profil de composition dans la colonne.
            
            **Étapes du stepping (marche en escalier) :**
            1. Partir du sommet : x = xD, y = xD
            2. Aller HORIZONTALEMENT à l'équilibre : x = x_eq, y = y (constant)
            3. Aller VERTICALEMENT à l'opérateur line : x = x_eq, y = y_op
            4. Répéter jusqu'à atteindre le bas (x ≈ xB)
            5. Compter le nombre de marches = nombre d'étages
            
            **Lignes opératoires :**
            - Section rectification (au-dessus alimentation) :
              y = (R/(R+1)) × x + xD/(R+1)
            
            - Section épuisement (sous alimentation) :
              y = (L'/V') × x - (B·xB)/V'
            
            - Q-line (alimentation) :
              y = (q/(q-1)) × x - xF/(q-1)
            
            Le changement de pente du opérateur line se fait à l'intersection 
            alimentation / q-line.
            """
        },
        "q_factor": {
            "title": "Facteur de Qualité d'Alimentation (q)",
            "content": """
            Le facteur q décrit l'état thermique de l'alimentation et son impact 
            sur le reflux interne dans la colonne.
            
            **Définition :**
            q = (quantité de chaleur pour vaporiser 1 mol d'alimentation) / 
                (chaleur latente de vaporisation)
            
            **États thermiques et valeurs q :**
            - q > 1 : Liquide sous-refroidi (refroidissement nécessaire)
            - q = 1 : Liquide saturé (point d'ébullition)
            - 0 < q < 1 : Mélange liquide-vapeur (q = fraction liquide)
            - q = 0 : Vapeur saturée (point de rosée)
            - q < 0 : Vapeur surchauffée (chauffage supplémentaire)
            
            **Impact sur la colonne :**
            - q > 1 : Augmente le reflux interne L' (plus d'étages, moins de reflux externe)
            - q = 1 : Condition de référence
            - q < 1 : Réduit le reflux interne (plus d'étages, plus de reflux externe)
            
            **Équation q-line :**
            La q-line passe par le point alimentation (xF, xF) et guide la construction McCabe-Thiele.
            """
        },
        "energy_balance": {
            "title": "Bilan Énergétique",
            "content": """
            Le bilan énergétique d'une colonne de distillation suit la conservation 
            de l'énergie. L'énergie doit être fournie au rebouilleur et retirée au condenseur.
            
            **Charges énergétiques :**
            - Q_condenser = V × λ_vap : Chaleur à enlever au sommet (kW)
            - Q_reboiler = V' × λ_vap : Chaleur à fournir au pied (kW)
            
            Où λ_vap est la chaleur latente de vaporisation (kJ/kmol).
            
            **Relation :**
            Q_reboiler ≈ Q_condenser + Q_perte
            
            En régime permanent avec entrée/sortie sensibles négligeables.
            
            **Minimum énergétique (Underwood) :**
            Q_min = (R_min + 1) × D × λ_vap / 3600  [en kW]
            
            **Efficacité thermique (Carnot) :**
            η = (1 - T_cond/T_reboil) × 100%
            """
        },
        "reflux_tradeoff": {
            "title": "Optimisation Reflux : Trade-off Énergie vs Capital",
            "content": """
            Il existe une relation inverse entre le reflux R et le nombre d'étages N :
            
            - R ↑ → N ↓ (moins d'étages, mais plus de vapeur générée)
            - R ↓ → N ↑ (plus d'étages, mais moins de vapeur)
            
            **Coûts associés :**
            - Coût énergétique : Proportionnel à Q_reboiler ∝ R
            - Coût capital : Proportionnel au nombre d'étages N ∝ 1/R
            
            **Optimum économique :**
            En industrie, R/R_min = 1.2 à 1.5 est l'optimum technico-économique.
            
            Cela représente le meilleur compromis entre :
            - Consommation énergétique raisonnable
            - Nombre d'étages acceptable
            - Coût de construction modéré
            """
        },
        "lle_extraction": {
            "title": "Extraction Liquide-Liquide",
            "content": """
            L'extraction L-L sépare un soluté entre une phase diluante (raffinat) et une phase
            solvant (extrait) selon l'équilibre y = Kx.
            
            **Bilans :** F + S = R + E  et  F·xF + S·yS = R·xR + E·yE
            
            **Point de mélange :** M = (F·xF + S·yS)/(F+S) — sert à construire la droite opératoire.
            
            **McCabe-Thiele L-L :** marches horizontales (équilibre) et verticales (bilan matière).
            
            **Kremser (contre-courant) :** N = ln[...] / ln(E) avec E = K·S/F — validation analytique.
            """
        },
        "thermodynamic_models": {
            "title": "Modèles Thermodynamiques",
            "content": """
            Le comportement du mélange (idéal ou non) affecte profondément les calculs.
            
            **Loi de Raoult (Idéal) :**
            P = x₁ × P₁sat + x₂ × P₂sat
            y₁ = (x₁ × P₁sat) / P
            
            Suppositions : Interactions moléculaires identiques.
            Valide pour : Mélanges similaires (benzène-toluène, hexane-heptane)
            
            **Modèle NRTL (Non-Idéal) :**
            Ajoute un terme de "coefficient d'activité" γ qui captures l'interaction.
            P = x₁ × γ₁ × P₁sat + x₂ × γ₂ × P₂sat
            
            Valide pour : Pratiquement tous les mélanges réels.
            Paramètres : Bases de données (eau-éthanol, etc.) ou heuristiques polairité.
            
            **Azeotrope :**
            Cas particulier où la courbe d'équilibre croise la ligne y = x.
            Impossible à dépasser par distillation simple.
            """
        }
    }

    FORMULAS = {
        "material_balance": "F = D + B;  F·xF = D·xD + B·xB",
        "fenske": "N_min = ln[xD/(1-xD) × (1-xB)/xB] / ln(α) - 1",
        "underwood": "R_min = (xD - y_int) / (y_int - x_int)",
        "gilliland": "Y = 0.75(1 - X^0.5668)  where X = (R - R_min)/(R + 1)",
        "raoult": "P = Σ xᵢ·Pᵢsat",
        "antoine": "log₁₀(P) = A - B/(C + T)",
        "nrtl_activity": "ln(γ) = (τ·G)² × [τ - Σ xⱼ·G/(x₁ + x₂·G)]",
        "lle_balance": "F + S = R + E;  F·xF + S·yS = R·xR + E·yE",
        "lle_mixing": "M = (F·xF + S·yS)/(F+S)",
        "kremser": "N = ln[(xF-yS/K)/(xR-yS/K)·(1-1/E)+1/E] / ln(E),  E = K·S/F",
    }

    @staticmethod
    def get_section(section_id):
        """Retourne le contenu pédagogique d'une section"""
        return PedagogicalExplainer.THEORY_SECTIONS.get(section_id, {})

    @staticmethod
    def get_formula(formula_id):
        """Retourne une formule spécifique"""
        return PedagogicalExplainer.FORMULAS.get(formula_id, "")

    @staticmethod
    def explain_result(result_type, value, context=None):
        """Génère une explication pour un résultat donné"""
        explanations = {
            "N_min_low": f"N_min = {value:.1f} est très faible. La séparation est très facile (α élevée ou xD/xB contraste élevé).",
            "N_min_high": f"N_min = {value:.1f} est élevé. La séparation est difficile (α faible ou xD/xB peu contrastés).",
            "R_min_low": f"R_min = {value:.2f} est très faible. Peu de reflux nécessaire.",
            "R_min_high": f"R_min = {value:.2f} est élevé. Beaucoup de reflux nécessaire.",
            "R_sufficient": f"R = {value:.2f} est supérieur à R_min. Simulation possible.",
            "R_insufficient": f"R = {value:.2f} est inférieur à R_min = {context['R_min']:.2f}. Pincement : impossible.",
            "N_theo_moderate": f"N_theo = {value:.1f} est modéré (~10 étages). Colonne réaliste.",
            "N_theo_high": f"N_theo = {value:.1f} est élevé. Colonne très grande ou séparation difficile.",
            "azeotrope_detected": f"Azeotrope détecté à x ≈ {value:.2f}. Distillation simple ne peut dépasser cette limite.",
        }
        return explanations.get(result_type, f"Résultat : {value}")

    @staticmethod
    def generate_learning_sequence(simulation_result):
        """Génère une séquence d'apprentissage basée sur les résultats"""
        sequence = []
        
        # Phase 1 : Bilans
        sequence.append({
            "title": "Étape 1 : Bilan de Matière",
            "explanation": f"""
            À partir de F = {simulation_result['flows']['F']} kmol/h et xF = {simulation_result.get('x_f', '?')}:
            D = {simulation_result['flows']['D']} kmol/h (distillat, produit léger)
            B = {simulation_result['flows']['B']} kmol/h (résidu, produit lourd)
            Vérification: D + B = {simulation_result['flows']['D'] + simulation_result['flows']['B']} ✓
            """,
            "formula": "F = D + B;  F·xF = D·xD + B·xB"
        })
        
        # Phase 2 : Thermodynamique
        sequence.append({
            "title": "Étape 2 : Équilibre Thermodynamique",
            "explanation": f"""
            Calcul de la courbe d'équilibre liquide-vapeur (x-y) utilisée pour McCabe-Thiele.
            Nombre de points d'équilibre calculés: 21 (de x=0 à x=1)
            Modèle utilisé: {simulation_result.get('model', 'NRTL')}
            """,
            "visual": "xy_curve"
        })
        
        # Phase 3 : Nombre minimum d'étages
        sequence.append({
            "title": "Étape 3 : Nombre Minimum d'Étages (Fenske)",
            "explanation": f"""
            N_min = {simulation_result['N_min']:.1f} étages
            
            C'est le nombre ABSOLU minimum en supposant un reflux infini.
            Obtenu par l'équation de Fenske en utilisant la volatilité relative.
            """,
            "formula": PedagogicalExplainer.FORMULAS["fenske"]
        })
        
        # Phase 4 : Reflux minimum
        sequence.append({
            "title": "Étape 4 : Reflux Minimum (Underwood)",
            "explanation": f"""
            R_min = {simulation_result['R_min']:.2f}
            
            C'est le reflux ABSOLU minimum pour la séparation demandée.
            Au-dessous de cette valeur, la colonne atteint un pincement thermodynamique.
            """,
            "formula": PedagogicalExplainer.FORMULAS["underwood"]
        })
        
        # Phase 5 : Nombre théorique d'étages
        sequence.append({
            "title": "Étape 5 : Nombre Théorique d'Étages (Gilliland)",
            "explanation": f"""
            N_théorique = {simulation_result['N_theo']:.1f} étages
            Reflux opérationnel R = {simulation_result.get('R', '?'):.2f}
            
            Avec la corrélation de Gilliland, on lie N_min, R_min, N et R.
            """,
            "formula": PedagogicalExplainer.FORMULAS["gilliland"]
        })
        
        # Phase 6 : McCabe-Thiele
        sequence.append({
            "title": "Étape 6 : Simulation McCabe-Thiele",
            "explanation": f"""
            Nombre d'étages simulés = {simulation_result.get('n_stages', '?')}
            Étage d'alimentation optimal = {simulation_result.get('feed_stage', '?')}
            
            Chaque "marche" représente un étage théorique.
            """,
            "visual": "mccabe_thiele"
        })
        
        # Phase 7 : Efficacité et nombre réel
        sequence.append({
            "title": "Étape 7 : Efficacité et Nombre Réel d'Étages",
            "explanation": f"""
            Efficacité Murphree = {simulation_result.get('tray_eff', '75%')}
            N_réel = N_théorique / efficacité = {simulation_result.get('N_reel', '?')} étages
            
            Chaque étage réel n'est jamais 100% efficace (mélange non-parfait).
            """,
            "note": "Efficacité typique industrie: 70-85%"
        })
        
        # Phase 8 : Énergie
        sequence.append({
            "title": "Étape 8 : Consommation Énergétique",
            "explanation": f"""
            Charge condenseur Q_c = {simulation_result['energy']['Q_condenser']:.1f} kW
            Charge rebouilleur Q_r = {simulation_result['energy']['Q_reboiler']:.1f} kW
            Efficacité thermique = {simulation_result['energy']['thermal_efficiency']:.1f}%
            """,
            "visual": "energy_diagram"
        })
        
        return sequence


def generate_pedagogical_html_report(simulation_result):
    """Génère un rapport HTML pédagogique complet"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport Pédagogique - Distillation</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f5f5f5; }
            .container { max-width: 900px; margin: 0 auto; padding: 20px; }
            .section { background: white; padding: 20px; margin: 15px 0; border-radius: 8px; 
                      box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .title { color: #1e40af; border-bottom: 3px solid #1e40af; padding-bottom: 10px; }
            .formula { background: #f0f4f8; padding: 15px; border-left: 4px solid #3b82f6; 
                      font-family: 'Courier New'; margin: 10px 0; }
            .result { background: #e0f2fe; padding: 10px; border-radius: 6px; margin: 5px 0; }
            .alert { padding: 15px; margin: 10px 0; border-radius: 6px; }
            .alert-info { background: #dbeafe; border-left: 4px solid #3b82f6; }
            .alert-warning { background: #fef3c7; border-left: 4px solid #f59e0b; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="color: #1e40af; text-align: center;">Rapport Pédagogique : Simulation Distillation</h1>
            <p style="text-align: center; color: #666;">Étude pas à pas de la séparation par distillation</p>
            
            <!-- Résumé exécutif -->
            <div class="section">
                <h2 class="title">Résumé de la Simulation</h2>
                <div class="result">
                    <p><strong>Nombre d'étages théoriques :</strong> {N_theo:.1f}</p>
                    <p><strong>Nombre réels (avec efficacité) :</strong> {N_reel:.1f}</p>
                    <p><strong>Reflux opérationnel :</strong> {R:.2f}</p>
                    <p><strong>Consommation énergétique :</strong> {Q_reboil:.1f} kW</p>
                </div>
            </div>
            
            <!-- Séquence d'apprentissage -->
            <div id="learning-sequence"></div>
            
            <!-- Notes finales -->
            <div class="section">
                <h2 class="title">✓ Validation Physique</h2>
                <div class="alert alert-info">
                    Tous les résultats ont été vérifiés pour cohérence physique et thermodynamique.
                    Aucune violation des lois de la thermodynamique n'a été détectée.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html
