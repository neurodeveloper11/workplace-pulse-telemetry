"""
Unit tests for LocalDocumentParser
"""

import pytest
from pathlib import Path
from src.hierarchy_scanner import HierarchyScanner
from src.document_parser import LocalDocumentParser


@pytest.fixture
def parser():
    return LocalDocumentParser()


@pytest.fixture
def sample_dir():
    return Path(__file__).resolve().parent.parent / "data" / "sample_documents"


def test_parse_docx(parser, sample_dir):
    scanner = HierarchyScanner()
    docx_path = sample_dir / "Operaciones_Portuarias" / "2026" / "Actas_Comite" / "acta_convivencia_marzo_2026.docx"
    assert docx_path.exists()

    scanned_items = scanner.scan_directory(str(docx_path.parent))
    target_item = [i for i in scanned_items if i.file_name.endswith(".docx")][0]

    doc = parser.parse_document(target_item)
    assert doc.file_name.endswith(".docx")
    assert doc.department == "Operaciones_Portuarias"
    assert len(doc.sections) > 0
    assert "COMITÉ DE CONVIVENCIA" in doc.raw_full_text
    assert "Carlos Pérez" in doc.raw_full_text


def test_parse_pdf(parser, sample_dir):
    scanner = HierarchyScanner()
    pdf_path = sample_dir / "Finanzas_Contabilidad" / "2026" / "Auditorias" / "informe_auditoria_financiera_2026.pdf"
    assert pdf_path.exists()

    scanned_items = scanner.scan_directory(str(pdf_path.parent))
    target_item = [i for i in scanned_items if i.file_name.endswith(".pdf")][0]

    doc = parser.parse_document(target_item)
    assert doc.file_name.endswith(".pdf")
    assert doc.department == "Finanzas_Contabilidad"
    assert len(doc.sections) >= 1
    assert "AUDITORÍA" in doc.raw_full_text.upper()


def test_parse_excel(parser, sample_dir):
    scanner = HierarchyScanner()
    xlsx_path = sample_dir / "Ingenieria_Core" / "2026" / "Bitacoras" / "bitacora_guardias_incidentes.xlsx"
    assert xlsx_path.exists()

    scanned_items = scanner.scan_directory(str(xlsx_path.parent))
    target_item = [i for i in scanned_items if i.file_name.endswith(".xlsx")][0]

    doc = parser.parse_document(target_item)
    assert doc.file_name.endswith(".xlsx")
    assert doc.department == "Ingenieria_Core"
    assert len(doc.sections) == 5  # 5 rows with incident descriptions
    assert any("URGENTE: Se cayó" in s.content for s in doc.sections)


def test_parse_email(parser, sample_dir):
    scanner = HierarchyScanner()
    eml_path = sample_dir / "Comite_Convivencia_SST" / "2026" / "Emails" / "alerta_friccion_turno_nocturno.eml"
    assert eml_path.exists()

    scanned_items = scanner.scan_directory(str(eml_path.parent))
    target_item = [i for i in scanned_items if i.file_name.endswith(".eml")][0]

    doc = parser.parse_document(target_item)
    assert doc.file_name.endswith(".eml")
    assert doc.department == "Comite_Convivencia_SST"
    assert "Patricia Salazar" in (doc.author or "")
    assert "Aumento de friccion" in doc.title
    assert "Resolución 2764/2022" in doc.raw_full_text


def test_parse_txt(parser, sample_dir):
    scanner = HierarchyScanner()
    txt_path = sample_dir / "Atencion_Cliente" / "2026" / "Quejas" / "descargo_solicitud_apoyo.txt"
    assert txt_path.exists()

    scanned_items = scanner.scan_directory(str(txt_path.parent))
    target_item = [i for i in scanned_items if i.file_name.endswith(".txt")][0]

    doc = parser.parse_document(target_item)
    assert doc.file_name.endswith(".txt")
    assert doc.department == "Atencion_Cliente"
    assert "Diana Marcela Restrepo" in doc.raw_full_text
