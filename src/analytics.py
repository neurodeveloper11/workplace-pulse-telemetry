"""
Workplace-Pulse-Telemetry: Organizational Analytics & Executive Reporting Engine
Engineered by Fabio Torres (neurodeveloper11)

Aggregates message-level telemetry into department pulses, Karasek matrices,
early burnout warnings, and actionable interventions aligned with Colombian Resolution 2764/2022.
"""

from typing import List, Dict
from datetime import datetime
from collections import defaultdict
import uuid

from src.schemas import (
    MessageTelemetry,
    DepartmentPulse,
    ExecutiveReport,
    KarasekQuadrant,
    RiskLevel,
)


def compute_karasek_quadrant(avg_demand: float, avg_autonomy: float) -> KarasekQuadrant:
    """Classifies a team's organizational climate into the Karasek 4-quadrant topology."""
    if avg_demand >= 45.0:
        if avg_autonomy >= 50.0:
            return KarasekQuadrant.ACTIVE
        else:
            return KarasekQuadrant.HIGH_STRAIN
    else:
        if avg_autonomy >= 50.0:
            return KarasekQuadrant.LOW_STRAIN
        else:
            return KarasekQuadrant.PASSIVE


def compute_risk_level(
    avg_stress: float,
    avg_friction: float,
    avg_psi: float,
    after_hours_ratio: float,
) -> RiskLevel:
    """Evaluates multi-axial psychosocial risk severity."""
    if (
        avg_stress >= 65.0
        or avg_friction >= 55.0
        or avg_psi <= 35.0
        or after_hours_ratio >= 0.40
    ):
        return RiskLevel.CRITICAL
    elif (
        avg_stress >= 50.0
        or avg_friction >= 40.0
        or avg_psi <= 45.0
        or after_hours_ratio >= 0.25
    ):
        return RiskLevel.HIGH
    elif avg_stress >= 35.0 or avg_friction >= 25.0 or avg_psi <= 52.0:
        return RiskLevel.MODERATE
    else:
        return RiskLevel.LOW


def generate_recommendations(
    quadrant: KarasekQuadrant,
    risk: RiskLevel,
    avg_stress: float,
    avg_friction: float,
    avg_psi: float,
    after_hours_ratio: float,
) -> List[str]:
    """
    Formulates evidence-based organizational directives aligned with Res. 2764/2022
    (Intra-labor psychosocial risk management) and Edmondson's psychological safety research.
    """
    recs: List[str] = []

    # 1. After-hours & Burnout
    if after_hours_ratio >= 0.25 or avg_stress >= 55.0:
        recs.append(
            "Barrera de Desconexión Digital: Restringir notificaciones fuera de jornada (19:00 a 07:00) "
            "y auditar cuellos de botella de entrega inmediata (Res. 2764/2022, Dominio Demandas de la Jornada)."
        )

    # 2. Karasek Quadrant Directives
    if quadrant == KarasekQuadrant.HIGH_STRAIN:
        recs.append(
            "Intervención Prioritaria en Alta Tensión: Delegar mayor margen de decisión operativa en las células "
            "y redistribuir picos de carga para mitigar riesgos psicosomáticos y rotación de talento."
        )
    elif quadrant == KarasekQuadrant.PASSIVE:
        recs.append(
            "Reestructuración de Puestos y Autonomía: El equipo evidencia baja demanda pero nula latitud decisional. "
            "Fomentar iniciativas de auto-organización para evitar el síndrome de apatía laboral (Boreout)."
        )
    elif quadrant == KarasekQuadrant.ACTIVE:
        recs.append(
            "Mantenimiento Sostenible de Alto Rendimiento: El equipo exhibe alta autonomía y alta motivación; "
            "monitorear descansos intermitentes para evitar que la sobre-exigencia sostenida degenere en agotamiento."
        )

    # 3. Interpersonal Friction
    if avg_friction >= 35.0:
        recs.append(
            "Protocolo de Higiene Comunicacional: Desescalar patrones de comunicación defensiva y pasivo-agresiva. "
            "Realizar sesiones de alineación de expectativas interdepartamentales (Dominio de Relaciones Sociales en el Trabajo)."
        )

    # 4. Psychological Safety (Amy Edmondson)
    if avg_psi <= 45.0:
        recs.append(
            "Cultura de Seguridad Psicológica (Amy Edmondson): Institucionalizar 'Blameless Post-Mortems' y auditoría de liderazgo "
            "para que los colaboradores puedan reportar incidentes y dudas sin temor a consecuencias punitivas."
        )

    if not recs:
        recs.append(
            "Ambiente Ocupacional Saludable: Mantener políticas de reconocimiento y autonomía vigentes. Realizar chequeos preventivos periódicos."
        )

    return recs


def aggregate_department_pulse(
    dept_name: str, telemetry_list: List[MessageTelemetry]
) -> DepartmentPulse:
    """Aggregates individual message telemetry into a comprehensive departmental pulse."""
    if not telemetry_list:
        return DepartmentPulse(
            department=dept_name,
            message_count=0,
            participant_count=0,
            avg_stress_burnout=0.0,
            avg_psychological_safety=100.0,
            avg_friction=0.0,
            avg_autonomy=50.0,
            avg_demand=0.0,
            after_hours_ratio=0.0,
            karasek_quadrant=KarasekQuadrant.LOW_STRAIN,
            overall_risk_level=RiskLevel.LOW,
            burnout_alert=False,
            key_recommendations=["Sin actividad registrada en este período."],
        )

    count = len(telemetry_list)
    unique_senders = len(set(m.sender_pseudonym for m in telemetry_list))

    avg_stress = sum(m.stress_urgency_score for m in telemetry_list) / count
    avg_psi = sum(m.psychological_safety_score for m in telemetry_list) / count
    avg_friction = sum(m.friction_score for m in telemetry_list) / count
    avg_autonomy = sum(m.autonomy_score for m in telemetry_list) / count
    avg_demand = sum(m.demand_score for m in telemetry_list) / count

    after_hours_count = sum(1 for m in telemetry_list if m.after_hours_flag)
    after_hours_ratio = after_hours_count / count

    quadrant = compute_karasek_quadrant(avg_demand, avg_autonomy)
    risk = compute_risk_level(avg_stress, avg_friction, avg_psi, after_hours_ratio)
    burnout_flag = avg_stress >= 55.0 or after_hours_ratio >= 0.30

    recs = generate_recommendations(
        quadrant=quadrant,
        risk=risk,
        avg_stress=avg_stress,
        avg_friction=avg_friction,
        avg_psi=avg_psi,
        after_hours_ratio=after_hours_ratio,
    )

    return DepartmentPulse(
        department=dept_name,
        message_count=count,
        participant_count=unique_senders,
        avg_stress_burnout=round(avg_stress, 1),
        avg_psychological_safety=round(avg_psi, 1),
        avg_friction=round(avg_friction, 1),
        avg_autonomy=round(avg_autonomy, 1),
        avg_demand=round(avg_demand, 1),
        after_hours_ratio=round(after_hours_ratio, 2),
        karasek_quadrant=quadrant,
        overall_risk_level=risk,
        burnout_alert=burnout_flag,
        key_recommendations=recs,
    )


def generate_executive_report(
    telemetry_list: List[MessageTelemetry], total_pii_redacted: int = 0
) -> ExecutiveReport:
    """Builds the comprehensive executive report across all departments in the organization."""
    grouped = defaultdict(list)
    for t in telemetry_list:
        grouped[t.department].append(t)

    department_pulses: Dict[str, DepartmentPulse] = {}
    critical_alerts: List[str] = []

    total_msgs = len(telemetry_list)
    if total_msgs == 0:
        return ExecutiveReport(
            report_id=str(uuid.uuid4())[:8],
            total_messages_analyzed=0,
            total_pii_redacted=0,
            organization_burnout_index=0.0,
            organization_psych_safety_index=100.0,
            organization_friction_index=0.0,
            department_pulses={},
            critical_alerts=["No se encontraron datos para procesar."],
        )

    for dept, msgs in grouped.items():
        pulse = aggregate_department_pulse(dept, msgs)
        department_pulses[dept] = pulse

        if pulse.overall_risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            critical_alerts.append(
                f"🚨 [{dept.upper()}] Riesgo {pulse.overall_risk_level.value.upper()}: "
                f"Burnout {pulse.avg_stress_burnout}/100 | Fricción {pulse.avg_friction}/100 | "
                f"Cuadrante Karasek: {pulse.karasek_quadrant.value.replace('_', ' ').title()}"
            )

    org_burnout = sum(m.stress_urgency_score for m in telemetry_list) / total_msgs
    org_psi = sum(m.psychological_safety_score for m in telemetry_list) / total_msgs
    org_friction = sum(m.friction_score for m in telemetry_list) / total_msgs

    return ExecutiveReport(
        report_id=f"WPT-{str(uuid.uuid4())[:8].upper()}",
        generated_at=datetime.now(),
        total_messages_analyzed=total_msgs,
        total_pii_redacted=total_pii_redacted,
        organization_burnout_index=round(org_burnout, 1),
        organization_psych_safety_index=round(org_psi, 1),
        organization_friction_index=round(org_friction, 1),
        department_pulses=department_pulses,
        critical_alerts=critical_alerts,
    )
