import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProcessInsightCopilot:
    def __init__(self):
        self.api_base_url = "https://generativelanguage.googleapis.com/v1beta/models/"
        self.gemini_models = [
            "gemini-2.0-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
        ]

    def generate_expert_analysis(self, api_key, context_data, user_question=None):
        """
        Generate an AI answer with the simulation context when useful.
        Falls back to a local answer so the chat never crashes if remote APIs fail.
        """
        context_data = context_data or {}
        user_question = (user_question or "").strip()

        system_prompt = (
            "Tu es ProcessInsight AI, un assistant francophone utile, clair et pedagogique.\n"
            "Tu peux repondre a toutes les questions de l'utilisateur.\n"
            "Quand la question concerne la simulation, la thermodynamique ou les procedes, "
            "utilise les donnees fournies et explique les resultats.\n"
            "Quand la question est generale, reponds normalement sans inventer de donnees.\n"
            "Si une information manque, dis-le simplement et propose une methode pour avancer.\n"
            "Reponses courtes, bien organisees, en Markdown simple."
        )

        data_text = self._format_context(context_data)
        prompt = user_question or (
            "Fais une courte analyse experte de ce procede. Parle de l'etat actuel "
            "du fluide et donne des recommandations pratiques."
        )

        messages = [
            {"role": "system", "content": f"{system_prompt}\n\n{data_text}"},
            {"role": "user", "content": prompt},
        ]

        gemini_answer = self._ask_gemini(api_key, messages)
        if gemini_answer:
            return gemini_answer

        pollinations_answer = self._ask_pollinations(messages)
        if pollinations_answer:
            return pollinations_answer

        return self._local_fallback(context_data, user_question)

    def _ask_gemini(self, api_key, messages):
        if not api_key:
            return None

        prompt_str = messages[0]["content"] + "\n\nQuestion utilisateur:\n" + messages[1]["content"]
        payload = {"contents": [{"parts": [{"text": prompt_str}]}]}

        for model in self.gemini_models:
            try:
                result = self._post_json(
                    f"{self.api_base_url}{model}:generateContent?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    payload=payload,
                    timeout=12,
                )
                candidates = result.get("candidates") or []
                parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
                if parts and parts[0].get("text"):
                    return parts[0]["text"].strip()
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError):
                continue

        return None

    def _ask_pollinations(self, messages):
        try:
            result = self._post_json(
                "https://text.pollinations.ai/openai",
                headers={"Content-Type": "application/json"},
                payload={"messages": messages, "model": "openai", "temperature": 0.5},
                timeout=18,
            )
            content = result.get("choices", [{}])[0].get("message", {}).get("content")
            return content.strip() if content else None
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError):
            return None

    def _post_json(self, url, headers, payload, timeout):
        data = json.dumps(payload).encode("utf-8")
        request = Request(url, data=data, headers=headers, method="POST")
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)

    def _format_context(self, context_data):
        process_type = context_data.get("process_type") or context_data.get("process_types")
        fields = [
            ("Type", process_type),
            ("Modele", context_data.get("model_used")),
            ("Composants", context_data.get("components")),
            ("Temperature", self._with_unit(context_data.get("T"), "deg C")),
            ("Pression systeme", self._with_unit(context_data.get("P_sys"), "kPa")),
            ("Pression bulle", self._with_unit(context_data.get("P_bubble"), "kPa")),
            ("Pression rosee", self._with_unit(context_data.get("P_dew"), "kPa")),
            ("Facteur Z", context_data.get("Z_factor")),
            ("K1", context_data.get("K1")),
            ("y1", context_data.get("y1")),
        ]

        lines = ["Donnees disponibles de la simulation:"]
        for label, value in fields:
            if value not in (None, "", "None"):
                lines.append(f"- {label}: {value}")

        op_results = context_data.get("op_results")
        if op_results:
            lines.append(f"- Resultats operationnels: {op_results}")

        return "\n".join(lines)

    def _local_fallback(self, context_data, user_question=None):
        question = (user_question or "").strip()
        q = self._normalize(question)

        if not question:
            return self._local_process_summary(context_data)

        if self._looks_like_greeting(q):
            return (
                "Bonjour ! Je suis ProcessInsight AI.\n\n"
                "Posez-moi une question sur votre simulation, un calcul de procede, "
                "une interpretation de resultat, ou meme une question generale."
            )

        if self._asks_about_capabilities(q):
            return (
                "Je peux vous aider a :\n\n"
                "- interpreter les resultats de simulation ;\n"
                "- expliquer les notions de thermodynamique et de procedes ;\n"
                "- verifier des pressions, temperatures, facteurs Z ou equilibres ;\n"
                "- proposer des pistes d'optimisation ;\n"
                "- proposer des liens YouTube, ResearchGate et rapports PDF ;\n"
                "- repondre a une question generale.\n\n"
                "Si la question demande une information absente de la simulation, je vous le dirai clairement."
            )

        if self._asks_for_research_links(q):
            return self._answer_research_links(context_data, question)

        if self._asks_for_improvements(q):
            return self._answer_improvement_question(context_data)

        if self._is_general_question_style(q):
            return self._answer_general_question(question)

        if self._is_process_question(q):
            return self._answer_process_question(context_data, question)

        return self._answer_general_question(question)

    def _local_process_summary(self, context_data):
        p_sys = self._to_float(context_data.get("P_sys"))
        p_bub = self._to_float(context_data.get("P_bubble"))
        p_dew = self._to_float(context_data.get("P_dew"))
        z_factor = self._to_float(context_data.get("Z_factor"))
        components = context_data.get("components") or "non renseignes"

        lines = [
            "### Analyse rapide",
            "",
            f"- **Composants** : {components}",
        ]

        if p_sys is not None and p_bub is not None:
            if p_sys > p_bub * 1.1:
                lines.append("- **Etat probable** : le systeme est plutot en zone liquide/comprimee.")
                lines.append("- **Action utile** : reduire la pression ou augmenter la temperature peut favoriser la vaporisation.")
            elif p_sys < p_bub * 0.9:
                lines.append("- **Etat probable** : vaporisation ou flash important possible.")
                lines.append("- **Action utile** : augmenter la pression ou refroidir peut ramener plus de liquide.")
            else:
                lines.append("- **Etat probable** : proche du point de bulle, zone interessante pour une separation.")
                lines.append("- **Action utile** : verifier le reflux, les etages et la purete cible.")
        elif p_sys is not None and p_dew is not None:
            if p_sys < p_dew:
                lines.append("- **Etat probable** : phase vapeur dominante.")
            else:
                lines.append("- **Etat probable** : condensation possible selon la composition.")
        else:
            lines.append("- **Observation** : les pressions d'equilibre manquent pour conclure precisement.")

        if z_factor is not None and z_factor < 0.9:
            lines.append(f"- **Attention** : Z = {z_factor:.2f}, le comportement non ideal est significatif.")

        return "\n".join(lines)

    def _answer_process_question(self, context_data, question):
        summary = self._local_process_summary(context_data)
        return (
            f"{summary}\n\n"
            "**Lien avec votre question**\n\n"
            f"Pour \"{question}\", utilisez surtout les valeurs de pression, temperature, composition "
            "et facteur Z. Si vous me donnez une cible precise, par exemple purete, debit ou rendement, "
            "je peux orienter la recommandation plus finement."
        )

    def _answer_improvement_question(self, context_data):
        p_sys = self._to_float(context_data.get("P_sys"))
        p_bub = self._to_float(context_data.get("P_bubble"))
        z_factor = self._to_float(context_data.get("Z_factor"))

        lines = [
            "### Ameliorations possibles",
            "",
            "- **Verifier le point de fonctionnement** : comparez la pression systeme avec la pression de bulle et de rosee.",
            "- **Optimiser la separation** : ajustez le reflux, le nombre d'etages ou la purete cible selon le procede.",
            "- **Controler la temperature** : une temperature mieux adaptee peut ameliorer l'equilibre liquide-vapeur.",
            "- **Surveiller la non-idealite** : utilisez un modele adapte si le facteur Z s'eloigne de 1.",
            "- **Valider les bilans** : controlez les bilans matiere et energie avant de modifier les parametres.",
        ]

        if p_sys is not None and p_bub is not None:
            if p_sys > p_bub * 1.1:
                lines.extend([
                    "",
                    "**Priorite pour votre cas** : la pression semble elevee par rapport au point de bulle.",
                    "Essayez de reduire la pression ou d'augmenter legerement la temperature pour favoriser la separation.",
                ])
            elif p_sys < p_bub * 0.9:
                lines.extend([
                    "",
                    "**Priorite pour votre cas** : le systeme peut etre trop vaporise.",
                    "Essayez d'augmenter la pression ou de refroidir pour recuperer plus de phase liquide.",
                ])
            else:
                lines.extend([
                    "",
                    "**Priorite pour votre cas** : vous etes proche d'une zone favorable.",
                    "Travaillez surtout sur le reflux, le nombre d'etages et la specification de purete.",
                ])

        if z_factor is not None and z_factor < 0.9:
            lines.append("Comme Z est faible, gardez un modele non ideal pour eviter des resultats trop optimistes.")

        return "\n".join(lines)

    def _answer_research_links(self, context_data, question):
        from urllib.parse import quote_plus

        process_type = context_data.get("process_type") or context_data.get("process_types") or ""
        components = context_data.get("components") or ""
        raw_query = " ".join(str(part) for part in [process_type, components] if part).strip()
        if question:
            raw_query = f"{raw_query} {question}".strip()
        if not raw_query:
            raw_query = "chemical engineering process simulation"

        youtube = f"https://www.youtube.com/results?search_query={quote_plus(raw_query)}"
        researchgate = f"https://www.researchgate.net/search/publication?q={quote_plus(raw_query + ' process simulation')}"
        reports = f"https://www.google.com/search?q={quote_plus(raw_query + ' chemical engineering report filetype:pdf')}"
        courses = f"https://www.google.com/search?q={quote_plus(raw_query + ' course lecture pdf')}"

        return (
            "### Liens utiles pour votre procede\n\n"
            f"- **Videos YouTube** : [{raw_query}]({youtube})\n"
            f"- **Articles ResearchGate** : [publications et rapports]({researchgate})\n"
            f"- **Rapports PDF** : [recherche de rapports techniques]({reports})\n"
            f"- **Cours PDF** : [supports pedagogiques]({courses})\n\n"
            "La section **Annexe / Recherche** dans la page de simulation genere aussi ces liens automatiquement."
        )

    def _asks_for_research_links(self, normalized_question):
        keywords = [
            "youtube",
            "video",
            "videos",
            "researchgate",
            "article",
            "articles",
            "publication",
            "publications",
            "rapport",
            "rapports",
            "pdf",
            "recherche",
            "chercher",
            "source",
            "sources",
            "lien",
            "liens",
            "annexe",
        ]
        return any(keyword in normalized_question for keyword in keywords)

    def _answer_general_question(self, question):
        q = self._normalize(question)
        subject = self._extract_subject(question)
        known_answer = self._known_answer(q, subject)
        if known_answer:
            return known_answer

        if any(word in q for word in ["explique", "expliquer", "c est quoi", "c'est quoi", "definition", "definir"]):
            return (
                f"### Explication\n\n"
                f"**{subject}** peut etre compris comme le sujet principal de votre question.\n\n"
                "- **Idee simple** : on commence par identifier ce que cela represente.\n"
                "- **Role** : on regarde a quoi cela sert et dans quel contexte il est utilise.\n"
                "- **Exemple** : appliquez-le a un cas concret pour voir son effet.\n\n"
                "Donnez-moi le domaine exact si vous voulez une explication plus precise."
            )

        if any(word in q for word in ["comment", "methode", "etape", "faire"]):
            return (
                f"### Methode proposee\n\n"
                f"Pour **{subject}**, procedez ainsi :\n\n"
                "- definissez l'objectif exact ;\n"
                "- listez les donnees disponibles ;\n"
                "- choisissez la methode ou le modele adapte ;\n"
                "- appliquez le calcul ou l'analyse ;\n"
                "- verifiez le resultat avec un test simple.\n\n"
                "Avec vos valeurs exactes, je peux transformer cela en reponse numerique ou en procedure detaillee."
            )

        if any(word in q for word in ["pourquoi", "cause", "raison"]):
            return (
                f"### Causes possibles\n\n"
                f"Pour **{subject}**, les causes les plus probables sont :\n\n"
                "- une condition d'entree mal adaptee ;\n"
                "- un parametre manquant ou incoherent ;\n"
                "- un modele qui ne correspond pas au cas reel ;\n"
                "- une contrainte physique ou operationnelle non prise en compte.\n\n"
                "La meilleure verification est de comparer les donnees d'entree avec le resultat attendu."
            )

        if any(word in q for word in ["difference", "comparer", "comparaison", "vs"]):
            return (
                f"### Comparaison\n\n"
                f"Pour comparer **{subject}**, utilisez ces criteres :\n\n"
                "- **definition** : ce que chaque element represente ;\n"
                "- **objectif** : a quoi il sert ;\n"
                "- **avantages** : quand il est preferable ;\n"
                "- **limites** : quand il devient moins fiable ;\n"
                "- **cas d'utilisation** : exemple pratique.\n\n"
                "Envoyez les deux elements a comparer et je vous fais un tableau clair."
            )

        if any(word in q for word in ["calcul", "calculer", "combien", "valeur"]):
            return (
                f"### Calcul\n\n"
                f"Je peux calculer **{subject}**, mais il me faut les valeurs numeriques.\n\n"
                "Envoyez les donnees sous cette forme :\n"
                "- grandeur cherchee ;\n"
                "- formule si elle est imposee ;\n"
                "- valeurs avec unites ;\n"
                "- precision souhaitee.\n\n"
                "Des que les valeurs sont presentes, je donne le resultat et les etapes."
            )

        return (
            f"### Reponse\n\n"
            f"Pour **{subject}**, voici une reponse directe : commencez par preciser l'objectif, "
            "les donnees disponibles et le resultat attendu. Ensuite, on peut construire une "
            "explication, une procedure, une comparaison ou un calcul selon votre besoin.\n\n"
            "- Si c'est une question technique, donnez les valeurs.\n"
            "- Si c'est une question de cours, je peux expliquer simplement.\n"
            "- Si c'est une decision, je peux donner les options avec avantages et limites."
        )

    def _known_answer(self, normalized_question, subject):
        if "distillation" in normalized_question:
            return (
                "### Distillation\n\n"
                "La **distillation** est une operation de separation qui utilise la difference "
                "de volatilite entre les composants d'un melange.\n\n"
                "- Le composant le plus volatil part plus facilement en vapeur.\n"
                "- La vapeur est condensee pour obtenir un distillat plus riche en composant leger.\n"
                "- Le liquide restant devient plus riche en composant lourd.\n\n"
                "Pour l'ameliorer, on agit surtout sur le reflux, la pression, la temperature et le nombre d'etages."
            )

        if "pression" in normalized_question:
            return (
                "### Pression\n\n"
                "La **pression** est la force exercee par un fluide sur une surface. "
                "Dans un procede, elle influence fortement l'ebullition, la condensation et l'equilibre des phases.\n\n"
                "- Pression plus elevee : l'ebullition devient plus difficile.\n"
                "- Pression plus faible : la vaporisation est facilitee.\n"
                "- En separation, il faut comparer la pression systeme aux pressions de bulle et de rosee."
            )

        if "temperature" in normalized_question:
            return (
                "### Temperature\n\n"
                "La **temperature** mesure le niveau d'agitation thermique. "
                "Dans un procede, elle change la volatilite, la solubilite et l'equilibre liquide-vapeur.\n\n"
                "- Temperature plus elevee : plus de vaporisation en general.\n"
                "- Temperature plus faible : plus de condensation en general.\n"
                "- Elle doit etre choisie avec la pression pour atteindre la phase souhaitee."
            )

        if "liquide" in normalized_question and "vapeur" in normalized_question:
            return (
                "### Liquide vs vapeur\n\n"
                "- **Liquide** : phase dense, volume faible, molecules proches.\n"
                "- **Vapeur** : phase moins dense, volume plus grand, molecules espacees.\n"
                "- **Equilibre liquide-vapeur** : les deux phases coexistent et echangent de la matiere.\n\n"
                "En distillation, cette difference permet de separer les composants."
            )

        if "benzene" in normalized_question or "benzene" in self._normalize(subject):
            return (
                "### Benzene\n\n"
                "Le **benzene** est un hydrocarbure aromatique volatil, souvent utilise comme compose de reference "
                "en thermodynamique et en distillation.\n\n"
                "Phrase simple : le benzene est un liquide organique volatil qui s'evapore facilement et doit etre manipule avec prudence."
            )

        return None

    def _is_general_question_style(self, normalized_question):
        markers = [
            "explique",
            "expliquer",
            "c est quoi",
            "c'est quoi",
            "definition",
            "definir",
            "comment",
            "methode",
            "etape",
            "pourquoi",
            "cause",
            "raison",
            "difference",
            "comparer",
            "comparaison",
            "calcul",
            "calculer",
            "combien",
            "donne moi",
            "donnez moi",
            "phrase",
            "resume",
        ]
        return any(marker in normalized_question for marker in markers)

    def _extract_subject(self, question):
        cleaned = question.strip().strip(" ?!.:")
        if not cleaned:
            return "ce sujet"

        prefixes = [
            "explique moi",
            "explique",
            "c'est quoi",
            "c est quoi",
            "comment",
            "pourquoi",
            "donnez moi",
            "donne moi",
            "quelle est",
            "quel est",
            "quelles sont",
            "quels sont",
        ]
        normalized = self._normalize(cleaned)
        for prefix in prefixes:
            if normalized.startswith(prefix):
                return cleaned[len(prefix):].strip(" ?!.:") or cleaned
        return cleaned

    def _asks_for_improvements(self, normalized_question):
        keywords = [
            "amelioration",
            "ameliorations",
            "ameliorer",
            "optimisation",
            "optimiser",
            "recommandation",
            "recommandations",
            "conseil",
            "conseils",
            "solution",
            "solutions",
            "possible",
            "possibles",
            "quoi faire",
            "que faire",
        ]
        return any(keyword in normalized_question for keyword in keywords)

    def _is_process_question(self, normalized_question):
        keywords = [
            "simulation",
            "procede",
            "thermo",
            "temperature",
            "pression",
            "bulle",
            "rosee",
            "dew",
            "bubble",
            "facteur z",
            "equilibre",
            "distillation",
            "absorption",
            "extraction",
            "separation",
            "reflux",
            "plateau",
            "colonne",
            "rendement",
            "purete",
            "amelioration",
            "ameliorations",
            "ameliorer",
            "optimisation",
            "optimiser",
            "recommandation",
            "recommandations",
            "composition",
            "phase",
            "liquide",
            "vapeur",
            "gaz",
        ]
        return any(keyword in normalized_question for keyword in keywords)

    def _asks_about_capabilities(self, normalized_question):
        keywords = ["que peux", "tu peux", "aide", "fonction", "capable", "comment utiliser"]
        return any(keyword in normalized_question for keyword in keywords)

    def _looks_like_greeting(self, normalized_question):
        return normalized_question in {"bonjour", "salut", "hello", "bonsoir", "hi", "cc"}

    def _normalize(self, text):
        text = text.lower()
        replacements = {
            "é": "e",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "à": "a",
            "â": "a",
            "ä": "a",
            "î": "i",
            "ï": "i",
            "ô": "o",
            "ö": "o",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "ç": "c",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return re.sub(r"\s+", " ", text).strip()

    def _with_unit(self, value, unit):
        if value in (None, "", "None"):
            return None
        return f"{value} {unit}"

    def _to_float(self, value):
        if value in (None, "", "None"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
