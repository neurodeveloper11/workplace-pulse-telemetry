"""
Unit tests for DiscursiveChunker
"""

import pytest
from datetime import datetime
from src.chunker import DiscursiveChunker
from src.document_parser import ExtractedDocument, ExtractedSection
from src.schemas import ChannelType


@pytest.fixture
def chunker():
    return DiscursiveChunker(target_max_words=50, target_min_words=4, overlap_words=10)


def test_chunk_speaker_interventions(chunker):
    acta_text = """
    Presidente: Bienvenidos a la sesión del Comité de Convivencia.
    Carlos Pérez: Me siento sumamente agotado y con sobrecarga laboral insostenible.
    Ing. Sofía Gómez: Como ya te había dicho antes, debemos cumplir con el cronograma.
    Carlos Pérez: Pido que se revise la distribución de turnos de noche.
    """
    doc = ExtractedDocument(
        file_path="acta.docx",
        file_name="acta.docx",
        file_extension=".docx",
        department="Operaciones_Portuarias",
        sections=[
            ExtractedSection(
                section_title="Desarrollo",
                content=acta_text,
                section_type="paragraph"
            )
        ]
    )

    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 4

    speakers = [c.speaker for c in chunks]
    assert "Presidente" in speakers
    assert "Carlos Pérez" in speakers
    assert "Ing. Sofía Gómez" in speakers

    types = [c.chunk_type for c in chunks]
    assert all(t == "speaker_intervention" for t in types)


def test_chunk_tabular_records(chunker):
    doc = ExtractedDocument(
        file_path="turnos.xlsx",
        file_name="turnos.xlsx",
        file_extension=".xlsx",
        department="Ingenieria_Core",
        sections=[
            ExtractedSection(
                section_title="Guardias - Fila 1",
                speaker_or_author="Dev_Juan",
                content="[Descripcion]: Incidente crítico en base de datos. Servidor caído.",
                section_type="tabular_record"
            ),
            ExtractedSection(
                section_title="Guardias - Fila 2",
                speaker_or_author="Dev_Laura",
                content="[Descripcion]: Corrección desplegada con éxito tras el error de configuración.",
                section_type="tabular_record"
            )
        ]
    )

    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 2
    assert chunks[0].speaker == "Dev_Juan"
    assert chunks[1].speaker == "Dev_Laura"
    assert chunks[0].chunk_type == "tabular_record"


def test_chunk_free_text_windowing(chunker):
    # Monolithic long text without speakers
    words = ["palabra" for _ in range(120)]
    long_text = " ".join(words)

    doc = ExtractedDocument(
        file_path="memo.txt",
        file_name="memo.txt",
        file_extension=".txt",
        department="Talento_Humano",
        sections=[
            ExtractedSection(
                section_title="Memo General",
                content=long_text,
                section_type="paragraph"
            )
        ]
    )

    chunks = chunker.chunk_document(doc)
    # Target max is 50 words, so 120 words should yield multiple windowed chunks
    assert len(chunks) >= 3
    assert all(c.word_count <= 50 for c in chunks)


def test_chunk_to_raw_message(chunker):
    doc = ExtractedDocument(
        file_path="alerta.eml",
        file_name="alerta.eml",
        file_extension=".eml",
        department="Comite_Convivencia_SST",
        sections=[
            ExtractedSection(
                section_title="Asunto",
                speaker_or_author="Dra. Patricia",
                content="Solicitud de revisión urgente de clima laboral.",
                section_type="email_body"
            )
        ]
    )

    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1

    raw_msg = chunker.chunk_to_raw_message(chunks[0])
    assert raw_msg.message_id == chunks[0].chunk_id
    assert raw_msg.sender_id == "Dra. Patricia"
    assert raw_msg.department == "Comite_Convivencia_SST"
    assert raw_msg.channel == ChannelType.EMAIL
