document.addEventListener('DOMContentLoaded', () => {
    
    // Eléments DOM
    const comp1Select = document.getElementById('comp1');
    const comp2Select = document.getElementById('comp2');
    const tempInput = document.getElementById('temperature');
    const tempVal = document.getElementById('temp-val');
    const presInput = document.getElementById('pressure');
    const presVal = document.getElementById('pres-val');
    const x1Input = document.getElementById('x1_frac');
    const x1Val = document.getElementById('x1-val');
    const btnSimulate = document.getElementById('btn-simulate');
    const resultsCard = document.getElementById('results-card');
    const molecule = document.getElementById('molecule');
    const molStatus = document.getElementById('molecule-status');
    const insightsContainer = document.getElementById('insights-container');
    
    let mccabeChartInstance = null;

    // Mise à jour des labels
    tempInput.addEventListener('input', (e) => tempVal.innerText = e.target.value);
    presInput.addEventListener('input', (e) => presVal.innerText = e.target.value);
    x1Input.addEventListener('input', (e) => x1Val.innerText = e.target.value);

    // Initialisation
    fetchComponents();

    function fetchComponents() {
        // En vrai production, un call interceptor gérerait les 401/403 pour rediriger sur login
        fetch('/api/components')
            .then(r => r.json())
            .then(data => {
                data.forEach((c) => {
                    comp1Select.add(new Option(c.name, c.id));
                    comp2Select.add(new Option(c.name, c.id));
                });
                if (data.length > 1) {
                    comp1Select.selectedIndex = 0; 
                    comp2Select.selectedIndex = 1; 
                }
            }).catch(e => console.error("Erreur, utilisateur potentiellement déconnecté"));
    }

    btnSimulate.addEventListener('click', () => {
        molecule.classList.add('agitating');
        molStatus.innerText = "Calcul ProcessInsight en cours...";
        insightsContainer.innerHTML = "<p>Génération de l'analyse...</p>";

        const payload = {
            comp1_id: parseInt(comp1Select.value),
            comp2_id: parseInt(comp2Select.value),
            temperature: parseFloat(tempInput.value),
            pressure: parseFloat(presInput.value),
            x1: parseFloat(x1Input.value)
        };

        fetch('/api/simulate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                molStatus.innerText = "Erreur : " + data.error;
                molecule.classList.remove('agitating');
                return;
            }
            displayResults(data);
            displayInsights(data.insights);
            animateMolecule(data);
            renderChart(data);
        })
        .catch(err => {
            molStatus.innerText = "Erreur système.";
            molecule.classList.remove('agitating');
        });
    });

    function displayResults(data) {
        resultsCard.classList.remove('hidden');
        document.getElementById('auto-model').innerText = data.model_used;
        document.getElementById('res-pbubble').innerText = data.equilibrium.P_bubble;
        document.getElementById('res-alpha').innerText = data.relative_volatility;
        document.getElementById('res-y1').innerText = data.equilibrium.y1;
    }

    function displayInsights(insights) {
        insightsContainer.innerHTML = "";
        insights.forEach(insight => {
            const div = document.createElement('div');
            div.className = `insight-card ${insight.type}`;
            
            let icon = "💡";
            if(insight.type === "warning") icon = "⚠️";
            if(insight.type === "success") icon = "✅";
            if(insight.type === "info") icon = "ℹ️";
            
            div.innerHTML = `<strong>${icon} ${insight.type.toUpperCase()} :</strong> ${insight.message}`;
            insightsContainer.appendChild(div);
        });
    }

    function animateMolecule(data) {
        let y1 = data.equilibrium.y1;
        let volatility = data.relative_volatility;
        let P_sys = data.equilibrium.P_sys;
        let P_bubble = data.equilibrium.P_bubble;
        
        // Nouvelle intelligence d'animation ProcessInsight
        let targetStage = 1;
        if (P_sys > P_bubble * 1.5) {
            molStatus.innerText = "La molécule reste liquide et retombe rapidement. Pas d'ébullition !";
            targetStage = 1;
        } else if (P_bubble > P_sys * 1.5) {
            molStatus.innerText = "Flash Thermique ! La molécule est vaporisée violemment au sommet.";
            targetStage = 10;
        } else if (volatility < 1.05) {
            molStatus.innerText = "La molécule bloque au milieu (volatilité faible ou azéotrope potentiel).";
            targetStage = 5;
        } else if (y1 > 0.8) {
            molStatus.innerText = "La molécule monte les étages avec succès et en grande quantité.";
            targetStage = 9;
        } else {
            molStatus.innerText = "La molécule monte quelques étages puis s'équilibre.";
            targetStage = 6;
        }

        let bottomPos = 20 + ((targetStage - 1) * 38); 
        molecule.style.bottom = `${bottomPos}px`;

        setTimeout(() => molecule.classList.remove('agitating'), 1500);
    }

    function renderChart(data) {
        const ctx = document.getElementById('mccabeChart').getContext('2d');
        const eqData = data.mccabe.equilibrium_curve;
        const x_eq = eqData.map(d => d.x);
        const y_eq = eqData.map(d => d.y);

        if (mccabeChartInstance) mccabeChartInstance.destroy();
        Chart.defaults.color = '#9ba4b5';

        mccabeChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: x_eq,
                datasets: [
                    {
                        label: 'Equilibre y=f(x)',
                        data: y_eq,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 0
                    },
                    {
                        label: 'Idéal y=x',
                        data: x_eq,
                        borderColor: '#9ba4b5',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display:false },
                    y: { display:false }
                }
            }
        });
    }
});
