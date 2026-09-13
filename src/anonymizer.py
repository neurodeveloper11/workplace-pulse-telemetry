"""
Workplace-Pulse-Telemetry: Local-First Zero Data Leakage Anonymizer
Engineered by Fabio Torres (neurodeveloper11)

Performs deterministic local PII detection, redaction, and salted pseudonymization
guaranteeing that no confidential personal data leaves the local execution boundary.
"""

import re
import hashlib
from typing import List, Tuple, Dict, Optional
from src.schemas import RawMessage, SanitizedMessage, PIIEntity


class LocalAnonymizer:
    """
    On-premise zero-leakage anonymization engine.
    Detects and redacts emails, phone numbers, national identification numbers (CC/DNI/SSN),
    financial data (salaries, credit cards), network addresses, and personal mentions.
    """

    def __init__(self, salt: str = "workplace_pulse_default_salt_2026"):
        self.salt = salt
        self._user_pseudonym_cache: Dict[str, str] = {}

        # 1. Email Regex
        self.email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
        )

        # 2. Phone Numbers (Colombia, USA, International formats)
        self.phone_pattern = re.compile(
            r"(?:\+?57\s*)?(?:\b3\d{2}[\s.-]?\d{3}[\s.-]?\d{4}\b|\b(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b)"
        )

        # 3. National IDs (Cédula de Ciudadanía, DNI, SSN)
        self.id_pattern = re.compile(
            r"\b(?:CC|C\.C\.|Cédula|Cedula|DNI|Identificación|ID)[\s#:.]*([0-9]{1,3}(?:\.[0-9]{3}){2}|[0-9]{6,10})\b",
            re.IGNORECASE
        )
        self.ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

        # 4. Financial & Salary Data (e.g. $12.000.000 COP, $4,500 USD, 4500 USD, salario de 5 millones)
        self.financial_pattern = re.compile(
            r"(?:(?:\$|COP|USD|EUR)\s*[\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?|\b\d+(?:[.,]\d+)*\s*(?:pesos|dólares|dolares|COP|USD|EUR)\b|\b(?:sueldo|salario|pago|honorarios|bono)\s+(?:de\s+)?[\$]?[\d.,]+(?:\s*(?:millones|mil|k|USD|COP))?\b|\b(?:\d{4}[ -]?){3}\d{4}\b)",
            re.IGNORECASE
        )

        # 5. IP Addresses & Internal Domain hosts
        self.ip_pattern = re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        )

        # 6. Corporate Chat Mentions (@carlos, @juan.perez)
        self.mention_pattern = re.compile(r"@([a-zA-Z0-9._-]+)")

        # 7. Common Spanish/English Greetings with Proper Names (e.g. "Hola Carlos,", "Buenos días María,")
        self.greeting_name_pattern = re.compile(
            r"\b(Hola|Buenos días|Buenas tardes|Estimado|Estimada|Dear|Hi|Hello)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)(?=[,\s!?\n]|$)",
            re.IGNORECASE
        )

    def get_pseudonym(self, raw_id: str) -> str:
        """Generates a deterministic, collision-resistant pseudonym salted with SHA-256."""
        if raw_id not in self._user_pseudonym_cache:
            digest = hashlib.sha256(f"{self.salt}:{raw_id}".encode("utf-8")).hexdigest()
            pseudonym = f"User_{digest[:6].upper()}"
            self._user_pseudonym_cache[raw_id] = pseudonym
        return self._user_pseudonym_cache[raw_id]

    def anonymize_text(self, text: str) -> Tuple[str, List[PIIEntity]]:
        """
        Scans text, extracts PII entities, and applies redaction tokens.
        Returns:
            sanitized_text: String with all PII replaced by tokens.
            pii_entities: List of PIIEntity records.
        """
        pii_list: List[PIIEntity] = []
        sanitized = text

        # 1. Redact Emails
        for match in self.email_pattern.finditer(sanitized):
            pii_list.append(PIIEntity(
                entity_type="EMAIL",
                start_idx=match.start(),
                end_idx=match.end(),
                masked_value="[EMAIL_REDACTED]"
            ))
        sanitized = self.email_pattern.sub("[EMAIL_REDACTED]", sanitized)

        # 2. Redact Phone Numbers
        for match in self.phone_pattern.finditer(sanitized):
            pii_list.append(PIIEntity(
                entity_type="PHONE",
                start_idx=match.start(),
                end_idx=match.end(),
                masked_value="[PHONE_REDACTED]"
            ))
        sanitized = self.phone_pattern.sub("[PHONE_REDACTED]", sanitized)

        # 3. Redact National Identification Numbers (CC / DNI / SSN)
        for match in self.id_pattern.finditer(sanitized):
            pii_list.append(PIIEntity(
                entity_type="GOVERNMENT_ID",
                start_idx=match.start(),
                end_idx=match.end(),
                masked_value="[ID_REDACTED]"
            ))
        sanitized = self.id_pattern.sub("[ID_REDACTED]", sanitized)
        sanitized = self.ssn_pattern.sub("[ID_REDACTED]", sanitized)

        # 4. Redact Financial / Salary details
        for match in self.financial_pattern.finditer(sanitized):
            pii_list.append(PIIEntity(
                entity_type="FINANCIAL_SALARY",
                start_idx=match.start(),
                end_idx=match.end(),
                masked_value="[FINANCIAL_REDACTED]"
            ))
        sanitized = self.financial_pattern.sub("[FINANCIAL_REDACTED]", sanitized)

        # 5. Redact IP Addresses
        for match in self.ip_pattern.finditer(sanitized):
            pii_list.append(PIIEntity(
                entity_type="NETWORK_IP",
                start_idx=match.start(),
                end_idx=match.end(),
                masked_value="[IP_REDACTED]"
            ))
        sanitized = self.ip_pattern.sub("[IP_REDACTED]", sanitized)

        # 6. Redact Chat Mentions (@handle -> User_XXXX)
        def replace_mention(match):
            raw_handle = match.group(1)
            pseudo = self.get_pseudonym(raw_handle)
            pii_list.append(PIIEntity(
                entity_type="USER_MENTION",
                start_idx=match.start(),
                end_idx=match.end(),
                masked_value=pseudo
            ))
            return f"@{pseudo}"

        sanitized = self.mention_pattern.sub(replace_mention, sanitized)

        # 7. Redact Salutations with Personal Names ("Hola Carlos" -> "Hola [NAME_REDACTED]")
        def replace_greeting(match):
            greeting = match.group(1)
            name = match.group(2)
            # Avoid replacing known safe terms
            if name.lower() in ["equipo", "todos", "team", "all", "grupo"]:
                return match.group(0)
            pii_list.append(PIIEntity(
                entity_type="PERSON_NAME",
                start_idx=match.start(2),
                end_idx=match.end(2),
                masked_value="[NAME_REDACTED]"
            ))
            return f"{greeting} [NAME_REDACTED]"

        sanitized = self.greeting_name_pattern.sub(replace_greeting, sanitized)

        return sanitized, pii_list

    def anonymize_message(self, raw: RawMessage) -> SanitizedMessage:
        """Converts a RawMessage into a fully compliant SanitizedMessage."""
        sender_pseudo = self.get_pseudonym(raw.sender_id)
        clean_text, detected_pii = self.anonymize_text(raw.text_content)

        return SanitizedMessage(
            message_id=raw.message_id,
            sender_pseudonym=sender_pseudo,
            department=raw.department,
            timestamp=raw.timestamp,
            sanitized_content=clean_text,
            channel=raw.channel,
            pii_removed_count=len(detected_pii),
            detected_pii=detected_pii
        )

    def anonymize_batch(self, raw_messages: List[RawMessage]) -> List[SanitizedMessage]:
        """Processes a sequence of messages in memory with zero disk footprint."""
        return [self.anonymize_message(m) for m in raw_messages]
