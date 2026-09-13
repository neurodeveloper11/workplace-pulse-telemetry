"""
Workplace-Pulse-Telemetry: Realistic Synthetic Workplace Log Generator
Engineered by Fabio Torres (neurodeveloper11)

Generates multi-departmental, timestamp-aware workplace chat logs across 4 archetypes:
1. 'Core-Engineering': High-strain crunch, production outages, after-hours traffic.
2. 'Port-Logistics': Interpersonal friction, passive-aggressiveness, blame-shifting.
3. 'AI-Research-Labs': High psychological safety (Amy Edmondson), innovation, high autonomy.
4. 'Customer-Operations': Low control, rigid micromanagement, cynical disengagement (Karasek Passive).
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict
from src.schemas import RawMessage, ChannelType


class SyntheticWorkplaceLogGenerator:
    """Generates realistic enterprise communication logs containing synthetic PII and behavioral patterns."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.base_time = datetime(2026, 9, 8, 8, 30, 0)  # Start of a work week

    def generate_engineering_crunch_logs(self, count: int = 25) -> List[RawMessage]:
        """Archetype: FinTech Engineering Crunch - Production Outages, Late Nights, Acute Burnout."""
        senders = [
            "carlos.dev@paygate.io", "andrea.lead@paygate.io", "felipe.infra@paygate.io",
            "david.security@paygate.io", "laura.backend@paygate.io"
        ]
        templates = [
            "URGENTE: Se cayó el cluster de Kubernetes en la IP 10.0.12.44. La pasarela de pagos está rechazada. Necesitamos apagar este incendio ya!",
            "Llevo 16 horas seguidas en esto, estoy totalmente agotado y con insomnio. No doy más con estos deploys de madrugada.",
            "Otro rollback de emergencia... El cliente Banco Santander (CC 98765432) está llamando a quejarse al celular +57 312 456 7890.",
            "Favor enviar ya mismo el hotfix a producción sin excepciones. El salario de $12.000.000 COP que pagan aquí no compensa este estrés.",
            "Son las 23:45 y sigo pegado a la consola. La sobrecarga del sprint nos tiene colapsando a todos los del equipo.",
            "CRÍTICO: El webhook de pagos no responde. @andrea.lead por favor confirma si el servidor 192.168.4.10 fue reiniciado.",
            "Estoy saturada de alertas en PagerDuty. Llevo 3 fines de semana sin descansar. Me siento al límite.",
            "Revisé el PR #402. Tienes que aprobarlo de inmediato para salir a prod ahora mismo.",
        ]

        logs: List[RawMessage] = []
        for i in range(count):
            sender = random.choice(senders)
            text = random.choice(templates)
            # 55% after-hours distribution (night or weekend)
            if random.random() < 0.55:
                # Night: between 20:00 and 02:00
                hour = random.choice([20, 21, 22, 23, 0, 1])
                day_offset = random.randint(0, 5)
            else:
                hour = random.randint(9, 18)
                day_offset = random.randint(0, 4)

            timestamp = self.base_time + timedelta(days=day_offset, hours=hour, minutes=random.randint(1, 58))
            logs.append(
                RawMessage(
                    message_id=f"ENG-{i+1:04d}",
                    sender_id=sender,
                    department="Engineering-Core",
                    timestamp=timestamp,
                    text_content=text,
                    channel=ChannelType.SLACK
                )
            )
        return logs

    def generate_port_logistics_friction_logs(self, count: int = 25) -> List[RawMessage]:
        """Archetype: Port Logistics Operations - Blame Shifting, Passive Aggression, Low Safety."""
        senders = [
            "mario.despachos@puertocargo.co", "jorge.operaciones@puertocargo.co",
            "claudia.aduanas@puertocargo.co", "roberto.patio@puertocargo.co"
        ]
        templates = [
            "Como ya te había dicho en el correo anterior, ese contenedor no es mi trabajo. Favor leer el hilo con atención.",
            "Otra vez con lo mismo. No vuelvo a repetir que la autorización de la DIAN para la Cédula 12.345.678 te correspondía a ti.",
            "As per my last email, la grúa 4 estaba bloqueada. No traten de culpar al turno de patio por su falta de planeación.",
            "Hola Claudia, favor prestar más atención cuando generes la guía al celular 300 765 4321. Siempre toca corregirles todo.",
            "No me vengan a pedir favores a última hora. Si el transportador no llegó a tiempo, no es mi problema.",
            "Hagan lo que quieran con ese embarque, pero dejen de mandar correos innecesarios que saturan la bandeja.",
            "Como mencioné antes, el operador con DNI 45678901 no tenía turno asignado. Revisen sus listas antes de quejarse.",
            "Eso no me corresponde a mí. Hablen con el jefe de patio si tienen algún reclamo.",
        ]

        logs: List[RawMessage] = []
        for i in range(count):
            sender = random.choice(senders)
            text = random.choice(templates)
            # Regular shift hours mostly
            timestamp = self.base_time + timedelta(days=random.randint(0, 4), hours=random.randint(7, 18), minutes=random.randint(1, 59))
            logs.append(
                RawMessage(
                    message_id=f"LOG-{i+1:04d}",
                    sender_id=sender,
                    department="Port-Logistics",
                    timestamp=timestamp,
                    text_content=text,
                    channel=ChannelType.TEAMS
                )
            )
        return logs

    def generate_ai_research_safety_logs(self, count: int = 25) -> List[RawMessage]:
        """Archetype: AI Research & Innovation - High Psychological Safety (Edmondson), High Autonomy."""
        senders = [
            "elena.scientist@neuroai.org", "mateo.nlp@neuroai.org",
            "sofia.ethics@neuroai.org", "camilo.mlops@neuroai.org"
        ]
        templates = [
            "Equipo, cometí un error en el preprocesamiento del dataset de entrenamiento. Pido disculpas, ya lo corregí en el repo.",
            "¿Qué opinan sobre probar este nuevo optimizador? Me gustaría escuchar sus sugerencias y ver qué riesgos identifican.",
            "Propongo una alternativa para el pipeline de inferencia. Desde mi punto de vista podríamos ganar un 25% de latencia.",
            "Muchas gracias por la revisión detallada @sofia.ethics, excelente aporte sobre las métricas de equidad.",
            "Decidí refactorizar el módulo de embeddings con total autonomía. ¿Cómo lo ven para la demo del viernes?",
            "Necesito ayuda entendiendo esta divergencia en la loss de validación. ¿Alguien tiene disponibilidad de 15 min para hacer pair programming?",
            "Gran trabajo de todos en el sprint pasado. Resolví el bug de memoria y documenté el aprendizaje para el equipo.",
            "Y si probamos un enfoque heurístico primero? Estoy abierto a feedback sobre la arquitectura.",
        ]

        logs: List[RawMessage] = []
        for i in range(count):
            sender = random.choice(senders)
            text = random.choice(templates)
            # Healthy working hours, no after-hours
            timestamp = self.base_time + timedelta(days=random.randint(0, 4), hours=random.randint(9, 17), minutes=random.randint(1, 55))
            logs.append(
                RawMessage(
                    message_id=f"AI-{i+1:04d}",
                    sender_id=sender,
                    department="AI-Research-Labs",
                    timestamp=timestamp,
                    text_content=text,
                    channel=ChannelType.SLACK
                )
            )
        return logs

    def generate_passive_support_logs(self, count: int = 25) -> List[RawMessage]:
        """Archetype: Customer Support Operations - Low Autonomy, Micromanagement, Cynical Disengagement (Karasek Passive)."""
        senders = [
            "soporte1@servicios.com", "soporte2@servicios.com",
            "supervisor.calidad@servicios.com", "soporte3@servicios.com"
        ]
        templates = [
            "Tienes que hacer las llamadas siguiendo estrictamente el guion. Está prohibido salir del libreto sin excepciones.",
            "Debes enviar ya las 50 encuestas. Es obligatorio cerrar el turno con la cuota completa.",
            "Da igual el caso del cliente, aquí no me pagan lo suficiente para complicarme la vida.",
            "Qué más da si el ticket queda abierto, para qué esforzarse si las métricas nunca cambian.",
            "Haz lo que te digo y no discutas las órdenes de supervisión. Tienes que cumplir la meta hoy.",
            "Me da lo mismo cómo lo resuelvan, hagan lo que quieran con esa solicitud.",
            "No vale la pena proponer cambios, aquí todo se hace siempre igual por orden de la gerencia.",
            "Es obligatorio registrar cada minuto de pausa en la plataforma. Sin excepciones para nadie.",
        ]

        logs: List[RawMessage] = []
        for i in range(count):
            sender = random.choice(senders)
            text = random.choice(templates)
            timestamp = self.base_time + timedelta(days=random.randint(0, 4), hours=random.randint(8, 17), minutes=random.randint(1, 50))
            logs.append(
                RawMessage(
                    message_id=f"SUP-{i+1:04d}",
                    sender_id=sender,
                    department="Customer-Operations",
                    timestamp=timestamp,
                    text_content=text,
                    channel=ChannelType.INTERNAL_CHAT
                )
            )
        return logs

    def generate_full_dataset(self, samples_per_dept: int = 25) -> List[RawMessage]:
        """Generates a comprehensive dataset merging all 4 corporate archetypes."""
        all_logs: List[RawMessage] = []
        all_logs.extend(self.generate_engineering_crunch_logs(samples_per_dept))
        all_logs.extend(self.generate_port_logistics_friction_logs(samples_per_dept))
        all_logs.extend(self.generate_ai_research_safety_logs(samples_per_dept))
        all_logs.extend(self.generate_passive_support_logs(samples_per_dept))
        
        # Sort chronologically
        all_logs.sort(key=lambda x: x.timestamp)
        return all_logs
