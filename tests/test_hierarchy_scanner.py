"""
Unit tests for HierarchyScanner
"""

import os
import zipfile
import tempfile
import pytest
from pathlib import Path

from src.hierarchy_scanner import HierarchyScanner
from src.schemas import ScannedDocumentItem


@pytest.fixture
def scanner():
    return HierarchyScanner(default_department="General_Corporativo")


def test_infer_metadata_known_departments(scanner):
    dept, unit, year = scanner.infer_metadata_from_path("Operaciones_Portuarias/2026/Actas_Comite/acta_marzo.docx")
    assert dept == "Operaciones_Portuarias"
    assert unit == "Actas Comite"
    assert "2026" in year
    assert "marzo" in year

    dept, unit, year = scanner.infer_metadata_from_path("Finanzas/Auditorias/reporte_2025.pdf")
    assert dept == "Finanzas_Contabilidad"
    assert unit == "Auditorias"
    assert "2025" in year

    dept, unit, year = scanner.infer_metadata_from_path("Talento_Humano/Quejas/caso_01.docx")
    assert dept == "Talento_Humano"
    assert unit == "Quejas"


def test_infer_metadata_custom_department_and_root(scanner):
    dept, unit, year = scanner.infer_metadata_from_path("Logistica_Comercial/2026/inventario.xlsx")
    assert dept == "Logistica_Comercial"

    # Root file without folders
    dept, unit, year = scanner.infer_metadata_from_path("acta_suelta.docx")
    assert dept == "General_Corporativo"
    assert unit is None


def test_scan_directory(tmp_path, scanner):
    # Create sample folder hierarchy
    doc1 = tmp_path / "Operaciones" / "2026" / "reporte.docx"
    doc1.parent.mkdir(parents=True)
    doc1.write_text("dummy content docx", encoding="utf-8")

    doc2 = tmp_path / "Finanzas" / "factura.pdf"
    doc2.parent.mkdir(parents=True)
    doc2.write_text("dummy content pdf", encoding="utf-8")

    ignored = tmp_path / "Finanzas" / "ignored.tmp"
    ignored.write_text("ignored", encoding="utf-8")

    scanned = scanner.scan_directory(str(tmp_path))
    assert len(scanned) == 2

    files_found = {item.file_name: item for item in scanned}
    assert "reporte.docx" in files_found
    assert files_found["reporte.docx"].department == "Operaciones_Portuarias"
    assert files_found["reporte.docx"].file_extension == ".docx"

    assert "factura.pdf" in files_found
    assert files_found["factura.pdf"].department == "Finanzas_Contabilidad"


def test_zip_extraction_and_scan(tmp_path, scanner):
    zip_path = tmp_path / "sample_bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("SST_Comite/2026/acta_enero.docx", "texto de acta de comite")
        zf.writestr("Ingenieria/turnos.csv", "timestamp,speaker,text\n2026-03-01,Dev,error")

    scanned, temp_dir = scanner.extract_and_scan_zip(str(zip_path))
    try:
        assert len(scanned) == 2
        depts = {item.department for item in scanned}
        assert "Comite_Convivencia_SST" in depts
        assert "Ingenieria_Core" in depts
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
