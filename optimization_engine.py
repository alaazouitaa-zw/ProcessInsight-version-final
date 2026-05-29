def get_insights(y1, x1, T, P_sys, comp1, P_bubble):
    """
    Système d'aide à la décision : Analyse l'efficacité de la séparation et propose des recommandations.
    """
    insights = []
    
    # Efficacité de séparation
    enrichment = y1 - x1
    
    if enrichment < 0.05:
        # Séparation très pauvre
        insights.append({
            "type": "warning",
            "message": f"L'enrichissement en {comp1.name} est très faible (+{round(enrichment*100, 1)}%). Les volatilités sont trop proches."
        })
        
        # Conseils
        if P_sys > 100:
            insights.append({
                "type": "advice",
                "message": "Réduisez la pression de fonctionnement (tirer au vide) pour augmenter la volatilité relative."
            })
        else:
            insights.append({
                "type": "advice",
                "message": "La distillation simple ne suffira pas. Envisagez de l'extraction ou de la distillation azéotropique."
            })
    elif enrichment > 0.3:
        # Excellente séparation
        insights.append({
            "type": "success",
            "message": "Excellente séparation ! La molécule s'évapore très efficacement."
        })
        
    # Analyse Pression bulle vs système
    if P_sys > P_bubble * 1.5:
        insights.append({
            "type": "warning",
            "message": "Le système est largement sous-refroidi (P système très supérieure à P_bulle). La molécule restera totalement liquide."
        })
        insights.append({
            "type": "advice",
            "message": f"Pour initier l'évaporation, augmentez la température au-delà de {T + 10}°C ou baissez la pression."
        })
    elif P_system_low := P_bubble > P_sys * 1.5:
        insights.append({
            "type": "warning",
            "message": "Surchauffe détectée. Le liquide s'évaporera instantanément en flash."
        })
    
    # Base
    if len(insights) == 0:
        insights.append({
            "type": "info",
            "message": "Les conditions sont stables pour un bon équilibre liquide-vapeur."
        })
        
    return insights
