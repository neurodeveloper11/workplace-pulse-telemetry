"""
Workplace-Pulse-Telemetry: Pydantic v2 Data Schemas
Defines core contracts for zero-leakage ingestion, anonymization, telemetric scoring and executive aggregation.
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class ChannelType(str, Enum):
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    INTERNAL_CHAT = "internal_chat"


class RiskLevel(str, Enum):
    LOW = "low"            # Verde - Entorno protegido / saludable
    MODERATE = "moderate"  # Amarillo - Atención preventiva
    HIGH = "high"          # Naranja - Riesgo psicosocial emergente
    CRITICAL = "critical"  # Rojo - Alerta inminente de Burnout / Fricción severa


class KarasekQuadrant(str, Enum):
    HIGH_STRAIN = "high_strain"  # Alta Demanda + Bajo Control (Zona Crítica)
    ACTIVE = "active"            # Alta Demanda + Alto Control (Alto Desempeño / Crecimiento)
    LOW_STRAIN = "low_strain"    # Baja Demanda + Alto Control (Baja Tensión / Confort)
    PASSIVE = "passive"          # Baja Demanda + Bajo Control (Pasivo / Apatía / Desenganche)


class PIIEntity(BaseModel):
    """Represents an identified and redacted piece of Personally Identifiable Information."""
    model_config = ConfigDict(frozen=True)
    
    entity_type: str = Field(..., description="Tipo de PII detectada (e.g. EMAIL, PHONE, NAME, ID, SALARY)")
    start_idx: int = Field(..., description="Índice de inicio original")
    end_idx: int = Field(..., description="Índice de finalización original")
    masked_value: str = Field(..., description="Valor seguro de reemplazo")


class RawMessage(BaseModel):
    """Raw communication event ingested locally before any sanitization."""
    message_id: str = Field(..., description="Identificador único del mensaje")
    sender_id: str = Field(..., description="Identificador sin procesar del emisor (nombre, email, handle)")
    department: str = Field(..., description="Departamento o célula de trabajo (e.g., Engineering, Sales, Logistics)")
    timestamp: datetime = Field(..., description="Fecha y hora de emisión del mensaje")
    text_content: str = Field(..., description="Contenido de texto crudo del mensaje")
    channel: ChannelType = Field(default=ChannelType.SLACK, description="Canal de comunicación de origen")


class SanitizedMessage(BaseModel):
    """Sanitized, anonymized message compliant with Zero Data Leakage requirements."""
    message_id: str
    sender_pseudonym: str = Field(..., description="Pseudónimo determinista generado localmente (ej: User_7a9f)")
    department: str
    timestamp: datetime
    sanitized_content: str = Field(..., description="Texto redactado sin ninguna entidad de PII")
    channel: ChannelType
    pii_removed_count: int = Field(default=0, description="Total de entidades sensibles eliminadas")
    detected_pii: List[PIIEntity] = Field(default_factory=list)


class MessageTelemetry(BaseModel):
    """Psychometric & NLP telemetry computed for an individual sanitized message."""
    message_id: str
    sender_pseudonym: str
    department: str
    timestamp: datetime
    stress_urgency_score: float = Field(..., ge=0.0, le=100.0, description="Índice de estrés y urgencia (OSBI)")
    psychological_safety_score: float = Field(..., ge=0.0, le=100.0, description="Índice de seguridad psicológica (PSI)")
    friction_score: float = Field(..., ge=0.0, le=100.0, description="Índice de fricción interpersonal (IFCI)")
    autonomy_score: float = Field(..., ge=0.0, le=100.0, description="Latitud de decisión y control verbal")
    demand_score: float = Field(..., ge=0.0, le=100.0, description="Demanda psicológica cuantitativa y emocional")
    after_hours_flag: bool = Field(default=False, description="Indica si el mensaje fue enviado fuera de horario laboral")
    emotional_valence: float = Field(..., ge=-1.0, le=1.0, description="Valencia afectiva (-1.0 muy negativo, +1.0 muy positivo)")
    detected_markers: List[str] = Field(default_factory=list, description="Marcadores léxico-psicométricos identificados")


class DepartmentPulse(BaseModel):
    """Aggregated organizational pulse for a specific department or team."""
    department: str
    message_count: int
    participant_count: int
    avg_stress_burnout: float = Field(..., ge=0.0, le=100.0)
    avg_psychological_safety: float = Field(..., ge=0.0, le=100.0)
    avg_friction: float = Field(..., ge=0.0, le=100.0)
    avg_autonomy: float = Field(..., ge=0.0, le=100.0)
    avg_demand: float = Field(..., ge=0.0, le=100.0)
    after_hours_ratio: float = Field(..., ge=0.0, le=1.0, description="Proporción de mensajes emitidos en deshoras")
    karasek_quadrant: KarasekQuadrant
    overall_risk_level: RiskLevel
    burnout_alert: bool = Field(default=False, description="Alerta temprana activada por sobrecarga crítica")
    key_recommendations: List[str] = Field(default_factory=list, description="Directivas psicológicas sugeridas")


class ExecutiveReport(BaseModel):
    """Executive organizational report for leadership, HR and occupational health committees."""
    report_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    total_messages_analyzed: int
    total_pii_redacted: int
    organization_burnout_index: float = Field(..., ge=0.0, le=100.0)
    organization_psych_safety_index: float = Field(..., ge=0.0, le=100.0)
    organization_friction_index: float = Field(..., ge=0.0, le=100.0)
    department_pulses: Dict[str, DepartmentPulse]
    critical_alerts: List[str] = Field(default_factory=list)
    regulatory_framework_summary: str = Field(
        default="Alineado con los dominios de la Resolución 2764/2022 (Colombia) y directrices ISO 45003:2021 de Gestión del Riesgo Psicosocial."
    )
