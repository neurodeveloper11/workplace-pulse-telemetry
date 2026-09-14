"""
Workplace-Pulse-Telemetry v2.0 - Interactive Hugging Face Space & Local-First Platform
Engineered by Fabio Torres (neurodeveloper11)
Bilingual Occupational Behavioral Telemetry, Hierarchical Multi-Format Ingestion & Zero Data Leakage Platform
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.schemas import (
    RawMessage,
    SanitizedMessage,
    MessageTelemetry,
    DepartmentPulse,
    ExecutiveReport,
    ChannelType,
    KarasekQuadrant,
    RiskLevel,
    BatchIngestionResult,
    ScannedDocumentItem,
    DocumentProcessingSummary,
)
from src.anonymizer import LocalAnonymizer
from src.telemetry_engine import OccupationalTelemetryEngine
from src.analytics import (
    aggregate_department_pulse,
    generate_executive_report,
)
from src.synthetic_generator import SyntheticWorkplaceLogGenerator
from src.batch_pipeline import BatchDocumentPipeline

# Initialize global core singletons
anonymizer = LocalAnonymizer(salt="workplace_pulse_demo_salt_2026")
telemetry_engine = OccupationalTelemetryEngine()
generator = SyntheticWorkplaceLogGenerator(seed=42)
batch_pipeline = BatchDocumentPipeline(salt="workplace_pulse_demo_salt_2026")

# Sample demo ZIP path
SAMPLE_ZIP_PATH = os.path.join(
    os.path.dirname(__file__), "data", "sample_documents", "auditoria_organizacional_2026_demo.zip"
)

# Load pre-generated benchmark logs or generate fallback
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "synthetic_workplace_logs.json")
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_json = json.load(f)
        benchmark_raw = [
            RawMessage(
                message_id=item["message_id"],
                sender_id=item["sender_id"],
                department=item["department"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                text_content=item["text_content"],
                channel=ChannelType(item["channel"]),
            )
            for item in raw_json
        ]
else:
    benchmark_raw = generator.generate_full_dataset(25)

# Precompute benchmark report
sanitized_benchmark = anonymizer.anonymize_batch(benchmark_raw)
telemetry_benchmark = telemetry_engine.compute_batch(sanitized_benchmark)
total_pii_benchmark = sum(m.pii_removed_count for m in sanitized_benchmark)
executive_report_benchmark = generate_executive_report(telemetry_benchmark, total_pii_benchmark)


# ==============================================================================
# Plotly Visualization Builders
# ==============================================================================

def create_department_comparison_chart(report: ExecutiveReport) -> go.Figure:
    """Grouped bar chart comparing Burnout, Psychological Safety, and Friction across departments."""
    depts = list(report.department_pulses.keys())
    burnout = [report.department_pulses[d].avg_stress_burnout for d in depts]
    safety = [report.department_pulses[d].avg_psychological_safety for d in depts]
    friction = [report.department_pulses[d].avg_friction for d in depts]

    fig = go.Figure(data=[
        go.Bar(name='Burnout / Estrés (OSBI)', x=depts, y=burnout, marker_color='#f43f5e'),
        go.Bar(name='Seguridad Psicológica (PSI)', x=depts, y=safety, marker_color='#10b981'),
        go.Bar(name='Fricción Interpersonal (IFCI)', x=depts, y=friction, marker_color='#f59e0b')
    ])

    fig.update_layout(
        barmode='group',
        template='plotly_dark',
        paper_bgcolor='#0f172a',
        plot_bgcolor='#1e293b',
        title="<b>Comparativa Psicométrica Multidepartamental</b>",
        title_font=dict(size=15, color="#f8fafc"),
        yaxis=dict(title="Puntuación Indexada (0 - 100)", range=[0, 100], gridcolor='#334155'),
        xaxis=dict(gridcolor='#334155'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=50, b=40),
        height=380
    )
    return fig


def create_karasek_matrix_chart(report: ExecutiveReport) -> go.Figure:
    """2D interactive scatter plot of the Karasek Job Demand-Control Model."""
    fig = go.Figure()

    # Quadrant colored backgrounds
    fig.add_shape(type="rect", x0=0, y0=45, x1=50, y1=100, fillcolor="#ef4444", opacity=0.15, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=50, y0=45, x1=100, y1=100, fillcolor="#10b981", opacity=0.15, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=0, y0=0, x1=50, y1=45, fillcolor="#f59e0b", opacity=0.15, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=50, y0=0, x1=100, y1=45, fillcolor="#3b82f6", opacity=0.15, layer="below", line_width=0)

    # Quadrant annotations
    fig.add_annotation(x=25, y=95, text="<b>🚨 ALTA TENSIÓN (HIGH STRAIN)</b><br>Riesgo Crítico de Burnout", showarrow=False, font=dict(color="#fca5a5", size=11))
    fig.add_annotation(x=75, y=95, text="<b>🚀 ACTIVO (ACTIVE)</b><br>Alto Desempeño & Aprendizaje", showarrow=False, font=dict(color="#6ee7b7", size=11))
    fig.add_annotation(x=25, y=10, text="<b>💤 PASIVO (PASSIVE)</b><br>Apatía & Desenganche (Boreout)", showarrow=False, font=dict(color="#fde68a", size=11))
    fig.add_annotation(x=75, y=10, text="<b>🛡️ BAJA TENSIÓN (LOW STRAIN)</b><br>Confort & Operación Estable", showarrow=False, font=dict(color="#93c5fd", size=11))

    colors = ['#f43f5e', '#38bdf8', '#a855f7', '#fb923c', '#34d399', '#fbbf24']
    for idx, (dept, pulse) in enumerate(report.department_pulses.items()):
        fig.add_trace(go.Scatter(
            x=[pulse.avg_autonomy],
            y=[pulse.avg_demand],
            mode='markers+text',
            text=[f"<b>{dept}</b>"],
            textposition="top center",
            textfont=dict(color="#f8fafc", size=12),
            marker=dict(size=18, color=colors[idx % len(colors)], line=dict(width=2, color='#ffffff')),
            hovertemplate=(
                f"<b>{dept}</b><br>" +
                f"Autonomía (Control): %{{x}}<br>" +
                f"Demanda Psicológica: %{{y}}<br>" +
                f"Cuadrante: {pulse.karasek_quadrant.value.replace('_', ' ').title()}<br>" +
                f"Mensajes fuera de hora: {int(pulse.after_hours_ratio * 100)}%<extra></extra>"
            ),
            name=dept
        ))

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0f172a',
        plot_bgcolor='#1e293b',
        title="<b>Matriz Demanda-Control de Karasek (Salud Ocupacional)</b>",
        title_font=dict(size=16, color="#f8fafc"),
        xaxis=dict(title="Latitud de Decisión / Autonomía (0 - 100)", range=[0, 100], gridcolor='#334155'),
        yaxis=dict(title="Demandas Psicológicas y Carga (0 - 100)", range=[0, 100], gridcolor='#334155'),
        showlegend=False,
        margin=dict(l=50, r=50, t=60, b=50),
        height=460
    )
    return fig


def create_radar_safety_chart(report: ExecutiveReport) -> go.Figure:
    """Radar chart comparing Amy Edmondson safety & climate factors."""
    categories = [
        "Seguridad Psicológica", "Autonomía", "Resistencia a Fricción",
        "Control de Sobrecarga", "Valencia Prosocial"
    ]
    categories_closed = categories + [categories[0]]

    fig = go.Figure()
    colors = ['#38bdf8', '#f43f5e', '#10b981', '#f59e0b', '#a855f7']

    for idx, (dept, pulse) in enumerate(report.department_pulses.items()):
        inv_friction = max(0.0, 100.0 - pulse.avg_friction)
        inv_burnout = max(0.0, 100.0 - pulse.avg_stress_burnout)
        prosocial = min(100.0, pulse.avg_psychological_safety * 0.9 + inv_friction * 0.1)

        values = [
            pulse.avg_psychological_safety,
            pulse.avg_autonomy,
            inv_friction,
            inv_burnout,
            prosocial
        ]
        values_closed = values + [values[0]]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill='toself',
            name=dept,
            line=dict(color=colors[idx % len(colors)], width=2),
            opacity=0.6
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#334155"),
            bgcolor='#1e293b'
        ),
        template='plotly_dark',
        paper_bgcolor='#0f172a',
        title="<b>Huella de Seguridad Psicológica y Resiliencia Ocupacional</b>",
        title_font=dict(size=16, color="#f8fafc"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=50, b=40),
        height=420
    )
    return fig


def create_file_type_donut_chart(breakdown: Dict[str, int]) -> go.Figure:
    """Donut chart depicting file types ingested in the batch."""
    labels = list(breakdown.keys()) if breakdown else ["Ninguno"]
    values = list(breakdown.values()) if breakdown else [1]

    palette = ['#38bdf8', '#818cf8', '#c084fc', '#fb7185', '#34d399', '#fbbf24']

    fig = go.Figure(data=[
        go.Pie(
            labels=[l.upper() for l in labels],
            values=values,
            hole=0.55,
            marker=dict(colors=palette[:len(labels)]),
            textinfo='label+percent',
            hovertemplate="<b>%{label}</b>: %{value} archivos (%{percent})<extra></extra>"
        )
    ])
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0f172a',
        plot_bgcolor='#1e293b',
        title="<b>Distribución por Formato de Archivo</b>",
        title_font=dict(size=14, color="#f8fafc"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=40, b=30),
        height=320
    )
    return fig


# ==============================================================================
# Batch Document Processing Controller
# ==============================================================================

def format_batch_results_to_df(summaries: List[DocumentProcessingSummary]) -> pd.DataFrame:
    """Converts processing summaries into a user-friendly presentation DataFrame."""
    rows = []
    for s in summaries:
        risk_tag = {
            RiskLevel.CRITICAL: "🔴 Crítico",
            RiskLevel.HIGH: "🟠 Alto",
            RiskLevel.MODERATE: "🟡 Moderado",
            RiskLevel.LOW: "🟢 Bajo",
        }.get(s.risk_level, "⚪ Bajo")

        rows.append({
            "Archivo": s.file_name,
            "Departamento": s.department.replace("_", " "),
            "Formato": s.file_type.upper(),
            "Fragmentos (Chunks)": s.chunks_count,
            "PII Redactada": s.pii_redacted_count,
            "Burnout (OSBI)": f"{s.avg_burnout_score:.1f}",
            "Seguridad (PSI)": f"{s.avg_psychological_safety:.1f}",
            "Fricción (IFCI)": f"{s.avg_friction_score:.1f}",
            "Semáforo Riesgo": risk_tag,
            "Estado": s.status
        })

    if not rows:
        return pd.DataFrame(columns=[
            "Archivo", "Departamento", "Formato", "Fragmentos (Chunks)",
            "PII Redactada", "Burnout (OSBI)", "Seguridad (PSI)",
            "Fricción (IFCI)", "Semáforo Riesgo", "Estado"
        ])

    return pd.DataFrame(rows)


def run_batch_ingestion(
    files_input: Optional[List[Any]],
    folder_path: str,
    custom_salt: str
) -> Tuple[str, pd.DataFrame, go.Figure, go.Figure, str, str]:
    """
    Main handler for bulk document ingestion.
    Supports uploaded files, ZIP bundles, or local directory paths.
    """
    salt_val = custom_salt.strip() if custom_salt else "workplace_pulse_demo_salt_2026"
    pipeline = BatchDocumentPipeline(salt=salt_val)

    # 1. Determine execution mode
    try:
        if files_input:
            # Check if single zip uploaded
            if len(files_input) == 1 and str(files_input[0]).lower().endswith(".zip"):
                zip_path = files_input[0]
                result = pipeline.process_zip(zip_path)
            else:
                # Multiple or single non-zip files
                scanned_items = []
                for f in files_input:
                    file_path_str = str(f)
                    p = Path(file_path_str)
                    ext = p.suffix.lower()
                    dept, unit, year = pipeline.scanner.infer_metadata_from_path(p.name, full_path=file_path_str)
                    scanned_items.append(
                        ScannedDocumentItem(
                            file_path=file_path_str,
                            relative_path=p.name,
                            file_name=p.name,
                            file_extension=ext,
                            department=dept,
                            team_unit=unit,
                            year_or_period=year,
                            file_size_bytes=p.stat().st_size if p.exists() else 0
                        )
                    )
                result = pipeline.process_scanned_items(scanned_items)

        elif folder_path and folder_path.strip():
            target_dir = folder_path.strip().strip('"').strip("'")
            if not os.path.isdir(target_dir):
                raise ValueError(f"La ruta ingresada no es un directorio válido: {target_dir}")
            result = pipeline.process_directory(target_dir)

        else:
            # Default fallback: process sample corpus ZIP
            if os.path.exists(SAMPLE_ZIP_PATH):
                result = pipeline.process_zip(SAMPLE_ZIP_PATH)
            else:
                raise ValueError("No se subió ningún archivo ni se especificó una ruta válida.")

    except Exception as e:
        error_md = f'<div class="alert-card"><b>⚠️ Error durante la ingesta documental:</b> {str(e)}</div>'
        empty_df = pd.DataFrame()
        empty_fig = go.Figure()
        return error_md, empty_df, empty_fig, empty_fig, "", ""

    # 2. Build Status Metrics Cards HTML
    status_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px;">
        <div class="metric-card">
            <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Archivos Analizados</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #38bdf8;">{result.total_files_processed} / {result.total_files_discovered}</div>
        </div>
        <div class="metric-card">
            <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Fragmentos Semánticos</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #818cf8;">{result.total_chunks_extracted}</div>
        </div>
        <div class="metric-card">
            <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Entidades PII Redactadas</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #34d399;">{result.total_pii_redacted}</div>
        </div>
        <div class="metric-card">
            <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Burnout Promedio Lote</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #f43f5e;">{result.executive_report.organization_burnout_index:.1f} / 100</div>
        </div>
        <div class="metric-card">
            <div style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Seguridad Psicológica</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #10b981;">{result.executive_report.organization_psych_safety_index:.1f} / 100</div>
        </div>
    </div>
    """

    # 3. Build Audit Table
    df_table = format_batch_results_to_df(result.file_summaries)

    # 4. Build Visual Charts
    fig_donut = create_file_type_donut_chart(result.file_type_breakdown)
    fig_dept = create_department_comparison_chart(result.executive_report)

    # 5. Build Alerts HTML
    if result.executive_report.critical_alerts:
        alerts_list = "\n".join([f"<li>{a}</li>" for a in result.executive_report.critical_alerts])
        alerts_html = f"""
        <div class="alert-card">
            <b>🚨 ALERTAS DE RIESGO IDENTIFICADAS EN EL LOTE:</b>
            <ul style="margin-top: 8px; margin-bottom: 0; padding-left: 20px;">{alerts_list}</ul>
        </div>
        """
    else:
        alerts_html = '<div class="info-box"><b>✅ Sin alertas críticas detectadas:</b> Los documentos procesados se mantienen dentro de los umbrales saludables de clima laboral.</div>'

    # 6. Build Directives & Recommendations
    all_recs = []
    for dept_name, pulse in result.executive_report.department_pulses.items():
        for rec in pulse.key_recommendations:
            all_recs.append(f"<b>[{dept_name.replace('_', ' ')}]</b>: {rec}")

    recs_md = "\n\n".join([f"- {r}" for r in all_recs]) if all_recs else "No se requieren intervenciones prioritarias en este momento."

    return status_html, df_table, fig_donut, fig_dept, alerts_html, recs_md


def load_sample_zip_demo() -> Tuple[str, pd.DataFrame, go.Figure, go.Figure, str, str]:
    """Helper that runs the sample audit bundle directly."""
    return run_batch_ingestion(
        files_input=None,
        folder_path="",
        custom_salt="workplace_pulse_demo_salt_2026"
    )


# ==============================================================================
# Live Playground & Message Processing
# ==============================================================================

def analyze_single_message_live(text_input: str, custom_salt: str) -> Tuple[str, str, str, str, str, str, str]:
    """Processes user input text in real-time through the Zero-Leakage Pipeline."""
    if not text_input or not text_input.strip():
        return (
            "Por favor ingresa un mensaje para analizar.",
            "{}",
            "0.0", "0.0", "0.0", "0.0", "0.0"
        )

    local_anon = LocalAnonymizer(salt=custom_salt if custom_salt else "workplace_pulse_demo_salt_2026")
    clean_text, pii_entities = local_anon.anonymize_text(text_input)

    now = datetime.now()
    sanitized = SanitizedMessage(
        message_id="LIVE-001",
        sender_pseudonym=local_anon.get_pseudonym("live_user@workspace.internal"),
        department="Live-Sandbox",
        timestamp=now,
        sanitized_content=clean_text,
        channel=ChannelType.DOCUMENT,
        pii_removed_count=len(pii_entities),
        detected_pii=pii_entities
    )

    telemetry = telemetry_engine.compute_telemetry(sanitized)

    pii_summary = {
        "total_redactions": len(pii_entities),
        "entities": [
            {"type": p.entity_type, "masked_replacement": p.masked_value}
            for p in pii_entities
        ]
    }

    stress_str = f"{telemetry.stress_urgency_score:.1f} / 100"
    psi_str = f"{telemetry.psychological_safety_score:.1f} / 100"
    friction_str = f"{telemetry.friction_score:.1f} / 100"
    autonomy_str = f"{telemetry.autonomy_score:.1f} / 100"
    markers_str = ", ".join(telemetry.detected_markers) if telemetry.detected_markers else "Ninguno detectado"

    return (
        clean_text,
        json.dumps(pii_summary, indent=2, ensure_ascii=False),
        stress_str,
        psi_str,
        friction_str,
        autonomy_str,
        markers_str
    )


# ==============================================================================
# Gradio UI Construction
# ==============================================================================

CUSTOM_CSS = """
.gradio-container {
    background-color: #0b0f19 !important;
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.header-box {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    border: 1px solid #312e81;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
}
.metric-card {
    background: #1e293b;
    border-radius: 10px;
    border: 1px solid #334155;
    padding: 16px;
    text-align: center;
}
.alert-card {
    background: #450a0a;
    border: 1px solid #b91c1c;
    border-radius: 8px;
    padding: 14px;
    color: #fecaca;
    font-size: 0.95rem;
    line-height: 1.5;
    margin-top: 10px;
    margin-bottom: 10px;
}
.info-box {
    background: #0f172a;
    border-left: 4px solid #38bdf8;
    padding: 14px;
    border-radius: 6px;
    color: #e2e8f0;
    margin-top: 10px;
}
"""

with gr.Blocks(title="Workplace-Pulse-Telemetry v2.0 | Fabio Torres") as demo:

    with gr.Row(elem_classes=["header-box"]):
        with gr.Column(scale=1):
            gr.Markdown(
                """
                # 🏢 Workplace-Pulse-Telemetry `v2.0`
                ### **Plataforma Local-First de Ingesta Jerárquica Documental, Telemetría Ocupacional & Detección de Burnout**
                **Arquitectura On-Premise con Cero Fuga de Datos (Zero Data Leakage) para Actas, Reportes, Hojas de Cálculo y Correos**  
                *Diseñado y Desarrollado por **Fabio Torres** (`neurodeveloper11` en GitHub / `neurodeveloper` en Hugging Face)*  
                *Psicólogo Especialista con 10+ años en Riesgo Psicosocial (Res. 2764/2022 y 2646/2008) • M.Sc. en Ingeniería de Datos (UTEL)*
                """
            )

    with gr.Tabs():

        # -------------------------------------------------------------
        # TAB 1: INGESTA MASIVA MULTI-FORMATO (V2.0 CORE)
        # -------------------------------------------------------------
        with gr.TabItem("📁 1. Ingesta Masiva de Documentos & Carpetas (v2.0)"):
            gr.Markdown(
                """
                ### 🚀 Motor de Ingesta Jerárquica On-Premise
                Sube una carpeta comprimida en **ZIP** con la estructura corporativa de tu organización (`[Departamento]/[Año]/[Archivo]`) 
                o arrastra archivos sueltos en formatos **Word (`.docx`), PDF (`.pdf`), Excel (`.xlsx`), CSV (`.csv`), Correos (`.eml`) o Memos (`.txt`)**.  
                *El motor inferirá automáticamente el departamento, segmentará actas extensas por intervenciones y redactará toda la PII sensible.*
                """
            )

            with gr.Row():
                with gr.Column(scale=2):
                    file_input = gr.File(
                        label="Arrastra aquí tus archivos (.pdf, .docx, .xlsx, .csv, .eml, .txt) o un archivo comprimido .ZIP",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".xlsx", ".csv", ".eml", ".txt", ".zip"]
                    )
                    folder_input = gr.Textbox(
                        label="O ingresa una Ruta de Directorio Local en el Servidor (On-Premise Path)",
                        placeholder="Ejemplo: D:/Empresa/Operaciones_Portuarias/2026/Auditorias",
                        lines=1
                    )
                    salt_box = gr.Textbox(
                        label="Sal Criptográfica Local (Salt)",
                        value="workplace_pulse_demo_salt_2026",
                        type="password"
                    )

                    with gr.Row():
                        btn_run_batch = gr.Button("⚡ Procesar Estructura Documental", variant="primary")
                        btn_load_demo = gr.Button("🧪 Cargar Caso Demo Completo (ZIP)", variant="secondary")

                with gr.Column(scale=3):
                    batch_status_cards = gr.HTML(
                        """
                        <div class="info-box">
                            <b>💡 Listo para procesar:</b> Haz clic en <b>"Cargar Caso Demo Completo (ZIP)"</b> para auditar en 1 segundo 
                            un lote real de 5 departamentos portuarios y financieros, o sube tus propios archivos confidenciales.
                        </div>
                        """
                    )

            gr.Markdown("### 📋 Auditoría Detallada Archivo por Archivo")
            audit_dataframe = gr.Dataframe(
                label="Inventario de Archivos Procesados, PII Redactada y Semáforo de Riesgo",
                wrap=True,
                headers=["Archivo", "Departamento", "Formato", "Fragmentos (Chunks)", "PII Redactada", "Burnout (OSBI)", "Seguridad (PSI)", "Fricción (IFCI)", "Semáforo Riesgo", "Estado"]
            )

            with gr.Row():
                with gr.Column(scale=1):
                    batch_donut_chart = gr.Plot(label="Distribución de Formatos")
                with gr.Column(scale=2):
                    batch_dept_chart = gr.Plot(label="Comparativa Psicométrica del Lote")

            batch_alerts_box = gr.HTML()

            with gr.Accordion("🏛️ Directivas de Intervención Recomendadas para el Lote (Res. 2764/2022)", open=False):
                batch_recommendations_box = gr.Markdown("Presiona procesar para generar las directivas personalizadas.")

            # Bind actions
            btn_run_batch.click(
                fn=run_batch_ingestion,
                inputs=[file_input, folder_input, salt_box],
                outputs=[batch_status_cards, audit_dataframe, batch_donut_chart, batch_dept_chart, batch_alerts_box, batch_recommendations_box]
            )

            btn_load_demo.click(
                fn=load_sample_zip_demo,
                inputs=[],
                outputs=[batch_status_cards, audit_dataframe, batch_donut_chart, batch_dept_chart, batch_alerts_box, batch_recommendations_box]
            )

        # -------------------------------------------------------------
        # TAB 2: RESUMEN EJECUTIVO & BENCHMARK ORGANIZACIONAL
        # -------------------------------------------------------------
        with gr.TabItem("📊 2. Resumen Ejecutivo & Benchmark"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 🔍 Métricas Globales del Clima Corporativo (Benchmark)")
                    with gr.Row():
                        m1 = gr.Number(label="🔥 Índice de Burnout (OSBI)", value=executive_report_benchmark.organization_burnout_index, precision=1)
                        m2 = gr.Number(label="🛡️ Seguridad Psicológica (PSI)", value=executive_report_benchmark.organization_psych_safety_index, precision=1)
                    with gr.Row():
                        m3 = gr.Number(label="⚡ Fricción Interpersonal (IFCI)", value=executive_report_benchmark.organization_friction_index, precision=1)
                        m4 = gr.Number(label="🔒 Entidades PII Redactadas", value=executive_report_benchmark.total_pii_redacted)

                    gr.Markdown("### 🚨 Alertas Tempranas de Riesgo Psicosocial")
                    alerts_md = "\n\n".join([f"- {alert}" for alert in executive_report_benchmark.critical_alerts])
                    gr.Markdown(f'<div class="alert-card">{alerts_md}</div>')

                with gr.Column(scale=1):
                    dept_chart = gr.Plot(value=create_department_comparison_chart(executive_report_benchmark))

        # -------------------------------------------------------------
        # TAB 3: MATRIZ DE KARASEK (DEMANDA - CONTROL)
        # -------------------------------------------------------------
        with gr.TabItem("🎯 3. Matriz Demanda-Control (Karasek)"):
            gr.Markdown(
                """
                ### Modelo Demanda-Control de Robert Karasek (Salud Ocupacional)
                Clasificación de equipos en 4 cuadrantes según sus **Demandas Psicológicas Cuantitativas** y su **Latitud de Decisión / Autonomía**.
                - **Alta Tensión:** Máximo riesgo de estrés crónico, burnout y somatización.
                - **Activo:** Motivación óptima, alto aprendizaje y resolución creativa de problemas.
                """
            )
            karasek_plot = gr.Plot(value=create_karasek_matrix_chart(executive_report_benchmark))

        # -------------------------------------------------------------
        # TAB 4: SEGURIDAD PSICOLÓGICA (AMY EDMONDSON)
        # -------------------------------------------------------------
        with gr.TabItem("🧠 4. Seguridad Psicológica (Amy Edmondson)"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown(
                        """
                        ### Constructo Científico de Seguridad Psicológica
                        Basado en el modelo de 7 factores de la **Dra. Amy Edmondson** (Harvard Business School):
                        1. **Vulnerabilidad y Admisión de Errores:** Libertad de reportar fallos sin miedo al castigo.
                        2. **Indagación y Preguntas Abiertas:** Curiosidad vs órdenes rígidas.
                        3. **Disenso Constructivo:** Capacidad de proponer alternativas y cuestionar decisiones.
                        4. **Higiene Comunicacional:** Ausencia de agresividad pasiva y condescendencia.
                        """
                    )
                    radar_plot = gr.Plot(value=create_radar_safety_chart(executive_report_benchmark))
                with gr.Column(scale=1):
                    gr.Markdown(
                        """
                        ### 📈 Diagnóstico por Departamento (Benchmark Base)
                        - **`AI-Research-Labs`:** Clima sobresaliente en seguridad psicológica (83.2/100). Alta admisión de errores y apertura a ideas.
                        - **`Engineering-Core`:** Tensión extrema por incidentes de producción (Burnout 72.8/100). El 55% de la comunicación ocurre en deshoras.
                        - **`Port-Logistics`:** Fricción interpersonal severa (62.4/100). Comunicación pasivo-agresiva ("como ya te había dicho").
                        - **`Customer-Operations`:** Micromanagement rígido y cinismo verbal ("da igual"). Cuadrante Karasek Pasivo.
                        """
                    )

        # -------------------------------------------------------------
        # TAB 5: INSPECTOR EN VIVO (PLAYGROUND ZERO-LEAKAGE)
        # -------------------------------------------------------------
        with gr.TabItem("🔬 5. Inspector en Vivo (Zero-Leakage Playground)"):
            gr.Markdown(
                """
                ### Prueba Interactiva: Pega cualquier texto confidencial de chat o correo
                El motor redactará **en tu propia máquina** toda la información sensible (nombres, cédulas, emails, salarios, teléfonos, IPs) 
                y calculará los vectores psicométricos en **< 15 milisegundos**, sin enviar ningún dato a la nube.
                """
            )
            with gr.Row():
                with gr.Column(scale=1):
                    input_text = gr.Textbox(
                        label="Entrada de Texto Confidencial (Raw Chat o Acta)",
                        lines=5,
                        placeholder="Ejemplo: Hola Carlos, llámame al 315 123 4567 o transfiere mi salario de $12.000.000 COP al banco...",
                        value="URGENTE: Se cayó el servidor de pagos en la IP 10.0.1.45. Hola Carlos, llama al celular +57 312 456 7890 del cliente Banco Santander (CC 12345678). Estoy totalmente agotado con este sprint, no doy más!"
                    )
                    salt_input = gr.Textbox(
                        label="Sal Criptográfica Local (Salt)",
                        value="workplace_pulse_demo_salt_2026",
                        type="password"
                    )
                    btn_analyze = gr.Button("⚡ Analizar con Telemetría Local-First", variant="primary")

                    gr.Markdown("#### Ejemplos Rápidos:")
                    example_btn1 = gr.Button("🚨 Ejemplo 1: Incidente Crítico y Burnout")
                    example_btn2 = gr.Button("⚡ Ejemplo 2: Fricción Pasivo-Agresiva")
                    example_btn3 = gr.Button("🌱 Ejemplo 3: Alta Seguridad Psicológica (Edmondson)")
                    example_btn4 = gr.Button("💤 Ejemplo 4: Desconexión y Apatía")

                with gr.Column(scale=1):
                    sanitized_output = gr.Textbox(label="Texto Sanitizado (Zero Data Leakage Output)", lines=3)
                    pii_output = gr.Code(label="PII Entities Redactadas Localmente", language="json")

                    with gr.Row():
                        out_stress = gr.Textbox(label="🔥 Burnout (OSBI)")
                        out_psi = gr.Textbox(label="🛡️ Seguridad Psicológica")
                    with gr.Row():
                        out_friction = gr.Textbox(label="⚡ Fricción")
                        out_autonomy = gr.Textbox(label="🎮 Autonomía")
                    out_markers = gr.Textbox(label="🏷️ Marcadores Psicométricos Identificados")

            # Connect analyze action
            btn_analyze.click(
                fn=analyze_single_message_live,
                inputs=[input_text, salt_input],
                outputs=[sanitized_output, pii_output, out_stress, out_psi, out_friction, out_autonomy, out_markers]
            )

            # Connect preset examples
            example_btn1.click(
                fn=lambda: "URGENTE: Se cayó el servidor en producción. Llevo 15 horas seguidas y no doy más con el insomnio. Favor llamar a Carlos al celular 310 987 6543 ya mismo!",
                outputs=[input_text]
            )
            example_btn2.click(
                fn=lambda: "Como ya te había dicho en el correo anterior, favor leer el hilo con atención. Otra vez con lo mismo, la orden con DNI 45678901 no es mi trabajo.",
                outputs=[input_text]
            )
            example_btn3.click(
                fn=lambda: "Equipo, cometí un error en la configuración del modelo. Pido disculpas, ya subí la corrección. ¿Qué opinan de esta solución? Muchas gracias por su apoyo.",
                outputs=[input_text]
            )
            example_btn4.click(
                fn=lambda: "Qué más da cómo quede el ticket, para qué esforzarse si da igual. Aquí no me pagan lo suficiente para complicarme la vida.",
                outputs=[input_text]
            )

        # -------------------------------------------------------------
        # TAB 6: DIRECTIVAS HR & RESOLUCIÓN 2764/2022
        # -------------------------------------------------------------
        with gr.TabItem("📋 6. Directivas HR & Marco Legal (Res. 2764/2022)"):
            gr.Markdown(
                """
                ### 🏛️ Marco Regulador: Resolución 2764/2022 & 2646/2008 (Ministerio del Trabajo de Colombia)
                Este módulo transforma los hallazgos de telemetría en intervenciones estructuradas según los dominios legales de riesgo psicosocial:

                #### 1. Dominio: Demandas del Trabajo (Carga Cuantitativa y Jornada Laboral)
                - **Hallazgo:** El equipo de `Engineering-Core` presenta un ratio de tráfico extralaboral de **55%**, indicando vulneración del derecho a la desconexión.
                - **Intervención:** Establecer compuertas tecnológicas de bloqueo de notificaciones de Slack/Teams entre las 19:00 y las 07:00, y formalizar guardias remuneradas compensatorias.

                #### 2. Dominio: Control sobre el Trabajo (Autonomía y Participación)
                - **Hallazgo:** El equipo de `Customer-Operations` se ubica en el cuadrante **Karasek Pasivo** con baja latitud decisional.
                - **Intervención:** Rediseñar protocolos de atención otorgando facultades a los operadores para resolver disputas de clientes sin requerir autorización piramidal jerárquica.

                #### 3. Dominio: Liderazgo y Relaciones Sociales en el Trabajo
                - **Hallazgo:** En `Port-Logistics`, el índice de fricción alcanza **62.4/100** con expresiones defensivas reiteradas.
                - **Intervención:** Taller de alineación operativa interdepartamental y adopción del protocolo de comunicación constructiva de Amy Edmondson.
                """
            )

    gr.Markdown(
        """
        ---
        <div style="text-align: center; color: #94a3b8; font-size: 0.85rem;">
            <b>Workplace-Pulse-Telemetry v2.0</b> • Creado por <b>Fabio Torres</b> (M.Sc. Data Engineering • Psicólogo Especialista en Riesgo Psicosocial)<br>
            Código abierto bajo licencia MIT en <a href="https://github.com/neurodeveloper11/workplace-pulse-telemetry" target="_blank" style="color: #38bdf8;">GitHub</a> • 
            Demostración en vivo en <a href="https://huggingface.co/spaces/neurodeveloper/workplace-pulse-telemetry" target="_blank" style="color: #38bdf8;">Hugging Face Spaces</a>
        </div>
        """
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True, css=CUSTOM_CSS, theme=gr.themes.Base())
