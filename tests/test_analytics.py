"""
Unit tests for Organizational Analytics and Executive Reporting.
"""

from datetime import datetime
from src.schemas import (
    MessageTelemetry,
    KarasekQuadrant,
    RiskLevel
)
from src.analytics import (
    compute_karasek_quadrant,
    compute_risk_level,
    aggregate_department_pulse,
    generate_executive_report
)


def test_karasek_quadrant_logic():
    # High Demand, Low Autonomy -> High Strain
    assert compute_karasek_quadrant(60.0, 30.0) == KarasekQuadrant.HIGH_STRAIN
    # High Demand, High Autonomy -> Active
    assert compute_karasek_quadrant(60.0, 70.0) == KarasekQuadrant.ACTIVE
    # Low Demand, Low Autonomy -> Passive
    assert compute_karasek_quadrant(30.0, 40.0) == KarasekQuadrant.PASSIVE
    # Low Demand, High Autonomy -> Low Strain
    assert compute_karasek_quadrant(30.0, 80.0) == KarasekQuadrant.LOW_STRAIN


def test_risk_level_evaluation():
    # Critical risk due to high stress
    assert compute_risk_level(70.0, 20.0, 60.0, 0.1) == RiskLevel.CRITICAL
    # Critical risk due to high after-hours ratio
    assert compute_risk_level(40.0, 20.0, 60.0, 0.45) == RiskLevel.CRITICAL
    # Low risk
    assert compute_risk_level(20.0, 10.0, 80.0, 0.05) == RiskLevel.LOW


def test_department_aggregation():
    t1 = MessageTelemetry(
        message_id="1",
        sender_pseudonym="User_1",
        department="Engineering",
        timestamp=datetime(2026, 9, 8, 10, 0),
        stress_urgency_score=70.0,
        psychological_safety_score=30.0,
        friction_score=50.0,
        autonomy_score=40.0,
        demand_score=65.0,
        after_hours_flag=False,
        emotional_valence=-0.4
    )
    t2 = MessageTelemetry(
        message_id="2",
        sender_pseudonym="User_2",
        department="Engineering",
        timestamp=datetime(2026, 9, 8, 22, 0),  # After hours
        stress_urgency_score=80.0,
        psychological_safety_score=35.0,
        friction_score=40.0,
        autonomy_score=30.0,
        demand_score=75.0,
        after_hours_flag=True,
        emotional_valence=-0.6
    )

    pulse = aggregate_department_pulse("Engineering", [t1, t2])

    assert pulse.department == "Engineering"
    assert pulse.message_count == 2
    assert pulse.participant_count == 2
    assert pulse.avg_stress_burnout == 75.0
    assert pulse.avg_autonomy == 35.0
    assert pulse.after_hours_ratio == 0.5
    assert pulse.karasek_quadrant == KarasekQuadrant.HIGH_STRAIN
    assert pulse.overall_risk_level == RiskLevel.CRITICAL
    assert pulse.burnout_alert is True
    assert len(pulse.key_recommendations) > 0


def test_executive_report_generation():
    t1 = MessageTelemetry(
        message_id="1",
        sender_pseudonym="User_1",
        department="Engineering",
        timestamp=datetime(2026, 9, 8, 10, 0),
        stress_urgency_score=70.0,
        psychological_safety_score=30.0,
        friction_score=50.0,
        autonomy_score=40.0,
        demand_score=65.0,
        after_hours_flag=False,
        emotional_valence=-0.4
    )
    report = generate_executive_report([t1], total_pii_redacted=5)

    assert report.total_messages_analyzed == 1
    assert report.total_pii_redacted == 5
    assert "Engineering" in report.department_pulses
    assert len(report.critical_alerts) >= 1
    assert report.organization_burnout_index == 70.0
