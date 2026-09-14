"""
End-to-End Integration Tests for BatchDocumentPipeline
"""

import pytest
from pathlib import Path
from src.batch_pipeline import BatchDocumentPipeline
from src.schemas import BatchIngestionResult, RiskLevel


@pytest.fixture
def pipeline():
    return BatchDocumentPipeline(salt="test_salt_batch_2026")


@pytest.fixture
def sample_dir():
    return Path(__file__).resolve().parent.parent / "data" / "sample_documents"


def test_process_sample_directory(pipeline, sample_dir):
    assert sample_dir.exists()

    result: BatchIngestionResult = pipeline.process_directory(str(sample_dir))

    assert result.total_files_discovered >= 5
    assert result.total_files_processed >= 5
    assert result.total_chunks_extracted >= 10

    # Verify PII was redacted across files
    assert result.total_pii_redacted >= 5

    # Verify departments discovered
    depts = set(result.department_breakdown.keys())
    assert "Operaciones_Portuarias" in depts
    assert "Finanzas_Contabilidad" in depts
    assert "Ingenieria_Core" in depts
    assert "Atencion_Cliente" in depts

    # Verify file formats breakdown
    exts = set(result.file_type_breakdown.keys())
    assert "docx" in exts
    assert "pdf" in exts
    assert "xlsx" in exts
    assert "eml" in exts
    assert "txt" in exts

    # Verify executive report
    report = result.executive_report
    assert report.total_messages_analyzed >= 10
    assert report.organization_burnout_index > 0.0
    assert report.organization_psych_safety_index > 0.0
    assert len(report.department_pulses) >= 4
    assert len(report.critical_alerts) >= 1


def test_process_sample_zip(pipeline, sample_dir):
    zip_path = sample_dir / "auditoria_organizacional_2026_demo.zip"
    assert zip_path.exists()

    result: BatchIngestionResult = pipeline.process_zip(str(zip_path))

    assert result.total_files_discovered == 5
    assert result.total_files_processed == 5
    assert result.total_chunks_extracted >= 10
    assert result.total_pii_redacted >= 5

    # Check file summaries
    assert len(result.file_summaries) == 5
    for summary in result.file_summaries:
        assert summary.status == "Procesado con éxito"
        assert summary.chunks_count > 0
