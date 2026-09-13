"""
Unit tests for Workplace-Pulse-Telemetry Pydantic v2 schemas.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.schemas import (
    RawMessage,
    SanitizedMessage,
    MessageTelemetry,
    DepartmentPulse,
    ChannelType,
    RiskLevel,
    KarasekQuadrant,
    PIIEntity
)


def test_raw_message_valid():
    msg = RawMessage(
        message_id="MSG-001",
        sender_id="carlos@empresa.com",
        department="Engineering",
        timestamp=datetime.now(),
        text_content="Revisando los logs del servidor.",
        channel=ChannelType.SLACK
    )
    assert msg.message_id == "MSG-001"
    assert msg.channel == ChannelType.SLACK


def test_message_telemetry_bounds_validation():
    # Valid bounds
    valid = MessageTelemetry(
        message_id="T-001",
        sender_pseudonym="User_A1B2",
        department="Engineering",
        timestamp=datetime.now(),
        stress_urgency_score=85.5,
        psychological_safety_score=40.0,
        friction_score=25.0,
        autonomy_score=60.0,
        demand_score=75.0,
        after_hours_flag=True,
        emotional_valence=-0.45,
        detected_markers=["Urgency(2)", "Exhaustion(1)"]
    )
    assert valid.stress_urgency_score == 85.5
    assert valid.emotional_valence == -0.45

    # Out of bounds should raise ValidationError
    with pytest.raises(ValidationError):
        MessageTelemetry(
            message_id="T-ERR",
            sender_pseudonym="User_A1B2",
            department="Engineering",
            timestamp=datetime.now(),
            stress_urgency_score=150.0,  # Invalid: > 100
            psychological_safety_score=40.0,
            friction_score=25.0,
            autonomy_score=60.0,
            demand_score=75.0,
            after_hours_flag=False,
            emotional_valence=0.0
        )

    with pytest.raises(ValidationError):
        MessageTelemetry(
            message_id="T-ERR2",
            sender_pseudonym="User_A1B2",
            department="Engineering",
            timestamp=datetime.now(),
            stress_urgency_score=50.0,
            psychological_safety_score=40.0,
            friction_score=25.0,
            autonomy_score=60.0,
            demand_score=75.0,
            after_hours_flag=False,
            emotional_valence=-2.5  # Invalid: < -1.0
        )


def test_department_pulse_creation():
    pulse = DepartmentPulse(
        department="Port-Logistics",
        message_count=120,
        participant_count=8,
        avg_stress_burnout=62.4,
        avg_psychological_safety=38.1,
        avg_friction=54.2,
        avg_autonomy=35.0,
        avg_demand=68.0,
        after_hours_ratio=0.32,
        karasek_quadrant=KarasekQuadrant.HIGH_STRAIN,
        overall_risk_level=RiskLevel.CRITICAL,
        burnout_alert=True,
        key_recommendations=["Intervención prioritaria en alta tensión."]
    )
    assert pulse.karasek_quadrant == KarasekQuadrant.HIGH_STRAIN
    assert pulse.overall_risk_level == RiskLevel.CRITICAL
    assert pulse.burnout_alert is True
