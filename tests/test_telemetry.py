"""
Unit tests for Occupational Telemetry & Psychometrics Engine.
Validates Maslach MBI markers, Amy Edmondson Safety, Karasek dimensions, and boundary bounds.
"""

from datetime import datetime
from src.telemetry_engine import OccupationalTelemetryEngine
from src.schemas import SanitizedMessage, ChannelType


def test_burnout_and_urgency_detection():
    engine = OccupationalTelemetryEngine()

    high_stress_msg = SanitizedMessage(
        message_id="TEST-01",
        sender_pseudonym="User_A1",
        department="Engineering-Core",
        timestamp=datetime(2026, 9, 8, 23, 45),  # After-hours (night)
        sanitized_content="URGENTE: Se cayó el servidor en producción. Estoy totalmente agotado, con insomnio y no doy más!",
        channel=ChannelType.SLACK
    )

    telemetry = engine.compute_telemetry(high_stress_msg)

    assert telemetry.after_hours_flag is True
    assert telemetry.stress_urgency_score > 70.0
    assert telemetry.demand_score > 60.0
    assert telemetry.emotional_valence < 0.0
    assert any("Exhaustion" in m for m in telemetry.detected_markers)
    assert any("Urgency" in m for m in telemetry.detected_markers)


def test_amy_edmondson_psychological_safety():
    engine = OccupationalTelemetryEngine()

    high_psi_msg = SanitizedMessage(
        message_id="TEST-02",
        sender_pseudonym="User_B2",
        department="AI-Research-Labs",
        timestamp=datetime(2026, 9, 8, 11, 0),  # Daytime
        sanitized_content="Equipo, cometí un error en el código de evaluación. ¿Qué opinan de esta solución? Muchas gracias por su apoyo.",
        channel=ChannelType.SLACK
    )

    telemetry = engine.compute_telemetry(high_psi_msg)

    assert telemetry.psychological_safety_score >= 75.0
    assert telemetry.friction_score < 15.0
    assert telemetry.emotional_valence > 0.3
    assert any("Vulnerability" in m for m in telemetry.detected_markers)
    assert any("Inquiry" in m for m in telemetry.detected_markers)
    assert any("Prosocial" in m for m in telemetry.detected_markers)


def test_interpersonal_friction_passive_aggression():
    engine = OccupationalTelemetryEngine()

    friction_msg = SanitizedMessage(
        message_id="TEST-03",
        sender_pseudonym="User_C3",
        department="Port-Logistics",
        timestamp=datetime(2026, 9, 8, 14, 0),
        sanitized_content="Como ya te había dicho en el correo anterior, favor leer el hilo. Otra vez con lo mismo, eso no es mi trabajo.",
        channel=ChannelType.TEAMS
    )

    telemetry = engine.compute_telemetry(friction_msg)

    assert telemetry.friction_score > 60.0
    assert telemetry.psychological_safety_score < 40.0
    assert telemetry.emotional_valence < -0.3
    assert any("Friction" in m for m in telemetry.detected_markers)


def test_telemetry_bounds_guarantee():
    engine = OccupationalTelemetryEngine()

    # Extreme negative stress overload
    extreme_text = "URGENTE CRÍTICO ALERTA! " + "agotado colapsando quemado no doy más al límite " * 5
    extreme_msg = SanitizedMessage(
        message_id="TEST-EXTREME",
        sender_pseudonym="User_Z9",
        department="Engineering",
        timestamp=datetime(2026, 9, 13, 3, 0),  # Sunday 3 AM
        sanitized_content=extreme_text,
        channel=ChannelType.SLACK
    )
    t = engine.compute_telemetry(extreme_msg)

    assert 0.0 <= t.stress_urgency_score <= 100.0
    assert 0.0 <= t.psychological_safety_score <= 100.0
    assert 0.0 <= t.friction_score <= 100.0
    assert 0.0 <= t.autonomy_score <= 100.0
    assert 0.0 <= t.demand_score <= 100.0
    assert -1.0 <= t.emotional_valence <= 1.0
