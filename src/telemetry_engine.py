"""
Workplace-Pulse-Telemetry: Occupational Psychometric & NLP Telemetry Engine
Engineered by Fabio Torres (neurodeveloper11)

Bridges Organizational Psychology (Maslach MBI, Amy Edmondson, Karasek JDC, Res. 2764/2022)
with high-performance lexical-syntactic natural language telemetry.
"""

import re
from datetime import datetime
from typing import List, Tuple, Dict, Any
from src.schemas import SanitizedMessage, MessageTelemetry, KarasekQuadrant


class OccupationalTelemetryEngine:
    """
    Computes occupational health and organizational climate indicators from sanitized text:
    - OSBI: Occupational Stress & Burnout Index (0 - 100)
    - PSI: Psychological Safety Index (Amy Edmondson Model) (0 - 100)
    - IFCI: Interpersonal Friction & Climate Index (0 - 100)
    - Demand & Autonomy for Karasek Matrix (0 - 100)
    - Emotional Valence (-1.0 to +1.0)
    """

    def __init__(self):
        # 1. Burnout & Exhaustion Markers (Maslach MBI dimension: Emotional Exhaustion)
        self.exhaustion_terms = [
            r"\bagotad[oa]s?\b", r"\bno doy m[aá]s\b", r"\bquemad[oa]s?\b",
            r"\bcolaps[aoó]ndo?\b", r"\bdrenad[oa]s?\b", r"\bsin energ[ií]a\b",
            r"\bal l[ií]mite\b", r"\bsaturad[oa]s?\b", r"\bsobrecarga(?:da)?\b",
            r"\binsomnio\b", r"\bestr[eé]s\b", r"\bdesbordad[oa]s?\b",
            r"\bexhausted\b", r"\bburn(?:ed|ing)? out\b", r"\boverwhelmed\b",
            r"\bdrained\b", r"\bbreaking point\b", r"\bcan'?t take this\b"
        ]
        self.exhaustion_regex = re.compile("|".join(self.exhaustion_terms), re.IGNORECASE)

        # 2. Cynicism & Depersonalization Markers (MBI dimension: Depersonalization)
        self.cynicism_terms = [
            r"\bda igual\b", r"\bme da lo mismo\b", r"\bqu[eé] m[aá]s da\b",
            r"\bno me pagan lo suficiente\b", r"\bno es mi problema\b",
            r"\bhagan lo que quieran\b", r"\bpara qu[eé]\b", r"\bno vale la pena\b",
            r"\bwhatever\b", r"\bnot my problem\b", r"\bwho cares\b", r"\bdon'?t care\b"
        ]
        self.cynicism_regex = re.compile("|".join(self.cynicism_terms), re.IGNORECASE)

        # 3. Urgency & Panic Pacing Markers
        self.urgency_terms = [
            r"\burgente\b", r"\bya mismo\b", r"\bpara ayer\b", r"\bemergencia\b",
            r"\basap\b", r"\bapaga(?:ndo)? incendios\b", r"\binmediat[ao](?:mente)?\b",
            r"\bahora mismo\b", r"\bbloqueante\b", r"\bcr[ií]tic[ao]\b",
            r"\bse cay[oó]\b", r"\burgently?\b", r"\bemergency\b", r"\bright now\b"
        ]
        self.urgency_regex = re.compile("|".join(self.urgency_terms), re.IGNORECASE)

        # 4. Amy Edmondson - Psychological Safety Positive Indicators
        # A. Vulnerability & Error Admission
        self.vulnerability_terms = [
            r"\bme equivoqu[eé]\b", r"\bcomet[ií] un error\b", r"\bfue mi error\b",
            r"\bnecesito ayuda\b", r"\bno s[eé] c[oó]mo\b", r"\bpido disculpas\b",
            r"\bme hago cargo\b", r"\bi made a mistake\b", r"\bmy bad\b",
            r"\bi was wrong\b", r"\bneed help\b", r"\bapologies\b"
        ]
        self.vulnerability_regex = re.compile("|".join(self.vulnerability_terms), re.IGNORECASE)

        # B. Inquiry, Curiosity & Open Questions
        self.inquiry_terms = [
            r"\bqu[eé] opinan\b", r"\bc[oó]mo lo ven\b", r"\balguien tiene dudas\b",
            r"\bsugerencias\b", r"\bqu[eé] riesgos ven\b", r"\bfeedback\b",
            r"\bqu[eé] piensan\b", r"\bwhat do you think\b", r"\bany ideas\b",
            r"\bopen to feedback\b", r"\bany suggestions\b"
        ]
        self.inquiry_regex = re.compile("|".join(self.inquiry_terms), re.IGNORECASE)

        # C. Constructive Disagreement & Alternative Proposals
        self.constructive_terms = [
            r"\bpropongo\b", r"\botra alternativa\b", r"\botra perspectiva\b",
            r"\by si probamos\b", r"\bdesde mi punto de vista\b",
            r"\bwhat if we try\b", r"\banother perspective\b", r"\balternative approach\b"
        ]
        self.constructive_regex = re.compile("|".join(self.constructive_terms), re.IGNORECASE)

        # 5. Interpersonal Friction & Passive Aggression
        self.friction_terms = [
            r"\bcomo ya (?:te )?hab[ií]a dicho\b", r"\bcomo ya dije\b",
            r"\bfavor leer el hilo\b", r"\bcomo mencion[eé] antes\b",
            r"\botra vez con lo mismo\b", r"\bno vuelvo a repetir\b",
            r"\bno es mi trabajo\b", r"\beso te correspond[ií]a\b",
            r"\bas per my last (?:email|message)\b", r"\bas stated previously\b",
            r"\bread carefully\b", r"\bnot my job\b", r"\bi shouldn'?t have to repeat\b"
        ]
        self.friction_regex = re.compile("|".join(self.friction_terms), re.IGNORECASE)

        # 6. Prosocial & Collaboration Indicators
        self.prosocial_terms = [
            r"\bgracias\b", r"\bmuchas gracias\b", r"\bgran trabajo\b",
            r"\bfelicitaciones\b", r"\btrabajemos juntos\b", r"\bcon gusto\b",
            r"\ba la orden\b", r"\bte ayudo\b", r"\bte apoyo\b",
            r"\bthank you\b", r"\bgreat work\b", r"\bhappy to help\b",
            r"\bteam effort\b", r"\bwell done\b", r"\bkudos\b"
        ]
        self.prosocial_regex = re.compile("|".join(self.prosocial_terms), re.IGNORECASE)

        # 7. Autonomy & Decision Latitude (Karasek Control axis)
        self.autonomy_terms = [
            r"\bdecid[ií]\b", r"\bpodemos elegir\b", r"\btengo autonom[ií]a\b",
            r"\bresolv[ií]\b", r"\bflexibilidad\b", r"\bautogesti[oó]n\b",
            r"\bwe decided\b", r"\bi chose\b", r"\bautonomous\b", r"\bempowered\b"
        ]
        self.autonomy_regex = re.compile("|".join(self.autonomy_terms), re.IGNORECASE)

        # 8. Micromanagement & Rigid Command (Suppresses autonomy & psychological safety)
        self.command_terms = [
            r"\btienes que hacer\b", r"\bdebes enviar ya\b", r"\best[aá] prohibido\b",
            r"\bes obligatorio\b", r"\bhaz lo que digo\b", r"\bsin excepciones\b",
            r"\byou must\b", r"\bmandatory\b", r"\bdo as i said\b", r"\bno excuses\b"
        ]
        self.command_regex = re.compile("|".join(self.command_terms), re.IGNORECASE)

    def is_after_hours(self, dt: datetime) -> bool:
        """
        Determines whether a message was sent outside of normal occupational hours.
        Standard business window: Monday-Friday, 07:00 to 19:00.
        """
        # Weekday: 0=Monday, 6=Sunday. Saturday=5, Sunday=6
        if dt.weekday() in [5, 6]:
            return True
        if dt.hour < 7 or dt.hour >= 19:
            return True
        return False

    def compute_telemetry(self, msg: SanitizedMessage) -> MessageTelemetry:
        """
        Processes a sanitized message and calculates its full psychometric telemetry vector.
        """
        text = msg.sanitized_content
        after_hours = self.is_after_hours(msg.timestamp)
        markers_found: List[str] = []

        # Find matches
        exhaustion_matches = self.exhaustion_regex.findall(text)
        cynicism_matches = self.cynicism_regex.findall(text)
        urgency_matches = self.urgency_regex.findall(text)
        vulnerability_matches = self.vulnerability_regex.findall(text)
        inquiry_matches = self.inquiry_regex.findall(text)
        constructive_matches = self.constructive_regex.findall(text)
        friction_matches = self.friction_regex.findall(text)
        prosocial_matches = self.prosocial_regex.findall(text)
        autonomy_matches = self.autonomy_regex.findall(text)
        command_matches = self.command_regex.findall(text)

        # Register markers
        if exhaustion_matches:
            markers_found.append(f"Exhaustion({len(exhaustion_matches)})")
        if cynicism_matches:
            markers_found.append(f"Cynicism({len(cynicism_matches)})")
        if urgency_matches:
            markers_found.append(f"Urgency({len(urgency_matches)})")
        if vulnerability_matches:
            markers_found.append(f"Vulnerability({len(vulnerability_matches)})")
        if inquiry_matches:
            markers_found.append(f"Inquiry({len(inquiry_matches)})")
        if constructive_matches:
            markers_found.append(f"Constructive({len(constructive_matches)})")
        if friction_matches:
            markers_found.append(f"Friction({len(friction_matches)})")
        if prosocial_matches:
            markers_found.append(f"Prosocial({len(prosocial_matches)})")
        if after_hours:
            markers_found.append("AfterHoursTraffic")

        # Syntactic indicators: ALL-CAPS intensity & multiple exclamation marks
        words = text.split()
        caps_words = [w for w in words if w.isupper() and len(w) >= 4 and not w.startswith("USER_")]
        caps_penalty = min(25.0, len(caps_words) * 8.0)
        exclamation_count = len(re.findall(r"!{2,}", text))
        exclamation_penalty = min(15.0, exclamation_count * 7.5)

        # -------------------------------------------------------------
        # 1. OSBI: Occupational Stress & Burnout Index (0 - 100)
        # -------------------------------------------------------------
        # Baseline neutral stress: 15.0
        base_stress = 15.0
        stress_score = (
            base_stress
            + (len(exhaustion_matches) * 28.0)
            + (len(urgency_matches) * 18.0)
            + (len(cynicism_matches) * 22.0)
            + (18.0 if after_hours else 0.0)
            + caps_penalty
            + exclamation_penalty
            - (len(prosocial_matches) * 8.0)
        )
        stress_score = max(0.0, min(100.0, stress_score))

        # -------------------------------------------------------------
        # 2. PSI: Psychological Safety Index (Amy Edmondson Model) (0 - 100)
        # -------------------------------------------------------------
        # Baseline safety in typical professional interaction: 55.0
        base_psi = 55.0
        psi_score = (
            base_psi
            + (len(vulnerability_matches) * 22.0)
            + (len(inquiry_matches) * 16.0)
            + (len(constructive_matches) * 14.0)
            + (len(prosocial_matches) * 10.0)
            - (len(friction_matches) * 25.0)
            - (len(command_matches) * 15.0)
            - (caps_penalty * 0.5)
        )
        psi_score = max(0.0, min(100.0, psi_score))

        # -------------------------------------------------------------
        # 3. IFCI: Interpersonal Friction & Climate Index (0 - 100)
        # -------------------------------------------------------------
        # Baseline friction: 10.0
        base_friction = 10.0
        friction_score = (
            base_friction
            + (len(friction_matches) * 32.0)
            + (len(cynicism_matches) * 16.0)
            + (len(command_matches) * 14.0)
            + (caps_penalty * 0.6)
            - (len(prosocial_matches) * 15.0)
            - (len(vulnerability_matches) * 10.0)
        )
        friction_score = max(0.0, min(100.0, friction_score))

        # -------------------------------------------------------------
        # 4. Karasek Model Dimensions: Demand & Autonomy
        # -------------------------------------------------------------
        # Demand: combination of task urgency, after hours, and exhaustion load
        base_demand = 20.0
        demand_score = (
            base_demand
            + (len(urgency_matches) * 20.0)
            + (len(exhaustion_matches) * 18.0)
            + (25.0 if after_hours else 0.0)
            + caps_penalty
        )
        demand_score = max(0.0, min(100.0, demand_score))

        # Autonomy: combination of decision agency and inquiries minus rigid commands
        base_autonomy = 45.0
        autonomy_score = (
            base_autonomy
            + (len(autonomy_matches) * 25.0)
            + (len(constructive_matches) * 15.0)
            + (len(inquiry_matches) * 10.0)
            - (len(command_matches) * 22.0)
        )
        autonomy_score = max(0.0, min(100.0, autonomy_score))

        # -------------------------------------------------------------
        # 5. Emotional Valence (-1.0 to +1.0)
        # -------------------------------------------------------------
        pos_tokens = len(prosocial_matches) + len(vulnerability_matches) + len(constructive_matches)
        neg_tokens = len(exhaustion_matches) + len(cynicism_matches) + len(friction_matches) + len(urgency_matches)
        total_valence_tokens = pos_tokens + neg_tokens

        if total_valence_tokens == 0:
            emotional_valence = 0.0
        else:
            raw_valence = (pos_tokens - neg_tokens) / (total_valence_tokens + 1.5)
            emotional_valence = max(-1.0, min(1.0, round(raw_valence, 2)))

        return MessageTelemetry(
            message_id=msg.message_id,
            sender_pseudonym=msg.sender_pseudonym,
            department=msg.department,
            timestamp=msg.timestamp,
            stress_urgency_score=round(stress_score, 1),
            psychological_safety_score=round(psi_score, 1),
            friction_score=round(friction_score, 1),
            autonomy_score=round(autonomy_score, 1),
            demand_score=round(demand_score, 1),
            after_hours_flag=after_hours,
            emotional_valence=emotional_valence,
            detected_markers=markers_found
        )

    def compute_batch(self, messages: List[SanitizedMessage]) -> List[MessageTelemetry]:
        """Calculates telemetry for a batch of sanitized messages."""
        return [self.compute_telemetry(m) for m in messages]
