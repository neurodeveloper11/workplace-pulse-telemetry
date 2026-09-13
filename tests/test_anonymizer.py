"""
Unit tests for Local-First Zero Data Leakage Anonymizer.
Verifies total elimination of PII and cryptographic pseudonym integrity.
"""

from datetime import datetime
from src.anonymizer import LocalAnonymizer
from src.schemas import RawMessage, ChannelType


def test_email_redaction():
    anon = LocalAnonymizer()
    text = "Por favor enviar la auditoría a fabio.torres@empresa.com.co y copia a admin@servicios.org."
    clean, pii = anon.anonymize_text(text)

    assert "fabio.torres@empresa.com.co" not in clean
    assert "admin@servicios.org" not in clean
    assert clean.count("[EMAIL_REDACTED]") == 2
    assert len(pii) == 2
    assert all(p.entity_type == "EMAIL" for p in pii)


def test_phone_redaction_colombia_and_international():
    anon = LocalAnonymizer()
    text = "Llamar al celular +57 315 789 1234 o al conmutador (555) 234-5678 para confirmar."
    clean, pii = anon.anonymize_text(text)

    assert "315 789 1234" not in clean
    assert "234-5678" not in clean
    assert "[PHONE_REDACTED]" in clean


def test_national_id_redaction():
    anon = LocalAnonymizer()
    text = "El colaborador con CC 1.020.304.050 y DNI 98765432 no tiene turno activo."
    clean, pii = anon.anonymize_text(text)

    assert "1.020.304.050" not in clean
    assert "98765432" not in clean
    assert "[ID_REDACTED]" in clean


def test_financial_and_salary_redaction():
    anon = LocalAnonymizer()
    text = "Su salario de $12.000.000 COP fue depositado, con bono de 4500 USD."
    clean, pii = anon.anonymize_text(text)

    assert "12.000.000" not in clean
    assert "4500 USD" not in clean
    assert "[FINANCIAL_REDACTED]" in clean


def test_ip_address_redaction():
    anon = LocalAnonymizer()
    text = "El fallo se originó en el nodo 192.168.1.105 hacia la puerta 10.0.0.1."
    clean, pii = anon.anonymize_text(text)

    assert "192.168.1.105" not in clean
    assert "10.0.0.1" not in clean
    assert "[IP_REDACTED]" in clean


def test_greeting_names_and_mentions():
    anon = LocalAnonymizer()
    text = "Hola Carlos, avísale a @laura.sanchez que revise el informe."
    clean, pii = anon.anonymize_text(text)

    assert "Carlos" not in clean
    assert "laura.sanchez" not in clean
    assert "[NAME_REDACTED]" in clean
    assert "@User_" in clean


def test_pseudonym_consistency():
    anon1 = LocalAnonymizer(salt="custom_salt_abc")
    anon2 = LocalAnonymizer(salt="custom_salt_abc")

    # Same salt yields deterministic pseudonym
    p1 = anon1.get_pseudonym("carlos.mendoza@empresa.com")
    p2 = anon2.get_pseudonym("carlos.mendoza@empresa.com")
    assert p1 == p2
    assert p1.startswith("User_")

    # Different salt yields different pseudonym
    anon_diff = LocalAnonymizer(salt="different_salt_xyz")
    p3 = anon_diff.get_pseudonym("carlos.mendoza@empresa.com")
    assert p1 != p3


def test_full_message_anonymization():
    anon = LocalAnonymizer()
    raw = RawMessage(
        message_id="RAW-99",
        sender_id="fabio.torres@puerto.co",
        department="Port-Logistics",
        timestamp=datetime(2026, 9, 10, 14, 30),
        text_content="Buenos días María, favor transferir $5.000.000 al transportador CC 10203040.",
        channel=ChannelType.SLACK
    )

    sanitized = anon.anonymize_message(raw)

    assert sanitized.message_id == "RAW-99"
    assert sanitized.sender_pseudonym.startswith("User_")
    assert "María" not in sanitized.sanitized_content
    assert "5.000.000" not in sanitized.sanitized_content
    assert "10203040" not in sanitized.sanitized_content
    assert sanitized.pii_removed_count >= 3
