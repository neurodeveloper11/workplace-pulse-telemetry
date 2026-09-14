"""
Workplace-Pulse-Telemetry: Batch Document Ingestion & Hierarchical Telemetry Pipeline
Engineered by Fabio Torres (neurodeveloper11)

Orchestrates multi-format scanning, parsing, discursive chunking, zero-leakage anonymization,
psychometric telemetry calculation and executive aggregation.
"""

import os
import uuid
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

from src.schemas import (
    ScannedDocumentItem,
    DocumentChunk,
    DocumentProcessingSummary,
    BatchIngestionResult,
    RawMessage,
    SanitizedMessage,
    MessageTelemetry,
    ExecutiveReport,
    RiskLevel
)
from src.hierarchy_scanner import HierarchyScanner
from src.document_parser import LocalDocumentParser, ExtractedDocument
from src.chunker import DiscursiveChunker
from src.anonymizer import LocalAnonymizer
from src.telemetry_engine import OccupationalTelemetryEngine
from src.analytics import generate_executive_report, compute_risk_level


class BatchDocumentPipeline:
    """
    High-throughput local-first pipeline for enterprise document hierarchies and archives.
    Guarantees 100% on-premise execution with Zero Data Leakage.
    """

    def __init__(self, salt: str = "workplace_pulse_batch_salt_2026"):
        self.salt = salt
        self.scanner = HierarchyScanner()
        self.parser = LocalDocumentParser()
        self.chunker = DiscursiveChunker()
        self.anonymizer = LocalAnonymizer(salt=self.salt)
        self.telemetry_engine = OccupationalTelemetryEngine()

    def process_directory(self, dir_path: str) -> BatchIngestionResult:
        """Discovers, parses, anonymizes and evaluates all documents within a local directory tree."""
        scanned_items = self.scanner.scan_directory(dir_path)
        return self.process_scanned_items(scanned_items)

    def process_zip(self, zip_path_or_bytes: Any) -> BatchIngestionResult:
        """Safely extracts a ZIP archive into a secure sandbox, processes it, and cleans up the sandbox."""
        scanned_items, temp_dir = self.scanner.extract_and_scan_zip(zip_path_or_bytes)
        try:
            return self.process_scanned_items(scanned_items)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def process_scanned_items(self, scanned_items: List[ScannedDocumentItem]) -> BatchIngestionResult:
        """
        Processes a list of discovered documents through the complete telemetry chain:
        Parse -> Chunk -> Anonymize -> Telemetry -> Analytics Aggregation.
        """
        batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
        file_summaries: List[DocumentProcessingSummary] = []
        all_message_telemetries: List[MessageTelemetry] = []

        file_type_breakdown: Dict[str, int] = defaultdict(int)
        department_breakdown: Dict[str, int] = defaultdict(int)
        total_pii_redacted = 0
        total_chunks_extracted = 0

        for item in scanned_items:
            ext_clean = item.file_extension.replace(".", "").lower()
            file_type_breakdown[ext_clean] += 1
            department_breakdown[item.department] += 1

            try:
                # 1. Parse document
                extracted_doc = self.parser.parse_document(item)

                # 2. Segment into discursive units
                chunks = self.chunker.chunk_document(extracted_doc)
                total_chunks_extracted += len(chunks)

                if not chunks:
                    # Document yielded no valid text chunks
                    file_summaries.append(
                        DocumentProcessingSummary(
                            file_name=item.file_name,
                            relative_path=item.relative_path,
                            department=item.department,
                            file_type=ext_clean,
                            chunks_count=0,
                            pii_redacted_count=0,
                            avg_burnout_score=0.0,
                            avg_psychological_safety=100.0,
                            avg_friction_score=0.0,
                            risk_level=RiskLevel.LOW,
                            status="Sin contenido textual legible"
                        )
                    )
                    continue

                # 3. Convert to RawMessage stream
                raw_messages = [self.chunker.chunk_to_raw_message(chk) for chk in chunks]

                # 4. Zero Data Leakage Anonymization
                sanitized_messages = self.anonymizer.anonymize_batch(raw_messages)
                doc_pii_count = sum(m.pii_removed_count for m in sanitized_messages)
                total_pii_redacted += doc_pii_count

                # 5. Calculate psychometric telemetry
                telemetries = self.telemetry_engine.compute_batch(sanitized_messages)
                all_message_telemetries.extend(telemetries)

                # Document level metrics
                doc_stress = sum(t.stress_urgency_score for t in telemetries) / len(telemetries)
                doc_psi = sum(t.psychological_safety_score for t in telemetries) / len(telemetries)
                doc_friction = sum(t.friction_score for t in telemetries) / len(telemetries)
                after_hours_ratio = sum(1 for t in telemetries if t.after_hours_flag) / len(telemetries)

                doc_risk = compute_risk_level(doc_stress, doc_friction, doc_psi, after_hours_ratio)

                file_summaries.append(
                    DocumentProcessingSummary(
                        file_name=item.file_name,
                        relative_path=item.relative_path,
                        department=item.department,
                        file_type=ext_clean,
                        chunks_count=len(chunks),
                        pii_redacted_count=doc_pii_count,
                        avg_burnout_score=round(doc_stress, 1),
                        avg_psychological_safety=round(doc_psi, 1),
                        avg_friction_score=round(doc_friction, 1),
                        risk_level=doc_risk,
                        status="Procesado con éxito"
                    )
                )

            except Exception as e:
                file_summaries.append(
                    DocumentProcessingSummary(
                        file_name=item.file_name,
                        relative_path=item.relative_path,
                        department=item.department,
                        file_type=ext_clean,
                        chunks_count=0,
                        pii_redacted_count=0,
                        avg_burnout_score=0.0,
                        avg_psychological_safety=100.0,
                        avg_friction_score=0.0,
                        risk_level=RiskLevel.LOW,
                        status=f"Error: {str(e)}"
                    )
                )

        # 6. Global Executive Aggregation
        executive_report = generate_executive_report(
            telemetry_list=all_message_telemetries,
            total_pii_redacted=total_pii_redacted
        )

        return BatchIngestionResult(
            batch_id=batch_id,
            processed_at=datetime.now(),
            total_files_discovered=len(scanned_items),
            total_files_processed=len([s for s in file_summaries if s.chunks_count > 0]),
            total_chunks_extracted=total_chunks_extracted,
            total_pii_redacted=total_pii_redacted,
            file_type_breakdown=dict(file_type_breakdown),
            department_breakdown=dict(department_breakdown),
            file_summaries=file_summaries,
            executive_report=executive_report
        )
