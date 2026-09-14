"""
Workplace-Pulse-Telemetry: Semantic & Discursive Document Chunker
Engineered by Fabio Torres (neurodeveloper11)

Deconstructs multi-page corporate documents (meeting minutes, COPASST acts, incident reports, logs)
into semantically coherent discursive units without diluting psychometric indicators.
"""

import re
import uuid
from typing import List, Optional
from datetime import datetime

from src.schemas import DocumentChunk, RawMessage, ChannelType
from src.document_parser import ExtractedDocument, ExtractedSection

# Regex for speaker turn detection in meeting minutes and testimonies
SPEAKER_TURN_REGEX = re.compile(
    r"^(?:[-*•]\s*)?("
    r"(?:(?:Ing\.|Dr\.|Dra\.|Lic\.|Abg\.|Sr\.|Sra\.)\s+)?"
    r"(?:Presidente|Secretario|Secretaria|Trabajador|Trabajadora|Colaborador|Colaboradora|"
    r"Jefe(?:\s+de\s+\w+)?|Director|Directora|Ingeniero|Ingeniera|Licenciado|Licenciada|Doctor|Doctora|"
    r"Abogado|Abogada|Fiscal|Auditor|Auditora|[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)"
    r"(?:\s*\([^)]+\))?"
    r")\s*:\s*(.*)",
    re.IGNORECASE
)

# Regex for numbered agenda points or conclusions
NUMBERED_ITEM_REGEX = re.compile(
    r"^(?:(?:Punto|Tema|Compromiso|Acuerdo|Hecho|Cargo|Descargo)\s+)?(\d+[\.\)]|[a-zA-Z][\.\)])\s+(.*)",
    re.IGNORECASE
)


class DiscursiveChunker:
    """
    Intelligent occupational document chunker.
    Splits text along natural discursive and dialogical boundaries:
    - Speaker interventions (turns in committee minutes)
    - Agenda items and commitments
    - Narrative tabular records (shift logs, complaint sheets)
    - Sliding windows for monolithic expository prose
    """

    def __init__(self, target_max_words: int = 250, target_min_words: int = 5, overlap_words: int = 25):
        self.target_max_words = target_max_words
        self.target_min_words = target_min_words
        self.overlap_words = overlap_words

    def chunk_document(self, doc: ExtractedDocument) -> List[DocumentChunk]:
        """Processes all extracted sections of a document into discrete DocumentChunks."""
        chunks: List[DocumentChunk] = []

        for sec in doc.sections:
            sec_chunks = self._chunk_section(sec, doc)
            chunks.extend(sec_chunks)

        # If document had no sections or generated nothing, fallback to full text
        if not chunks and doc.raw_full_text.strip():
            fallback_chunks = self._chunk_free_text(
                text=doc.raw_full_text,
                doc=doc,
                section_title=doc.title or "Documento Completo",
                default_speaker=doc.author or "Autor Desconocido",
                default_timestamp=doc.detected_date or datetime.now()
            )
            chunks.extend(fallback_chunks)

        return chunks

    def _chunk_section(self, sec: ExtractedSection, doc: ExtractedDocument) -> List[DocumentChunk]:
        """Segments an individual ExtractedSection into one or more DocumentChunks."""
        content = sec.content.strip()
        if not content:
            return []

        doc_date = sec.timestamp or doc.detected_date or datetime.now()
        doc_speaker = sec.speaker_or_author or doc.author or "Colaborador"

        # 1. Tabular records (from Excel / CSV) - usually each row is self-contained
        if sec.section_type == "tabular_record":
            words = content.split()
            if len(words) < self.target_min_words:
                return []
            return [
                DocumentChunk(
                    chunk_id=f"chk-{uuid.uuid4().hex[:8]}",
                    file_path=doc.file_path,
                    file_name=doc.file_name,
                    department=doc.department,
                    section_title=sec.section_title or "Registro Tabular",
                    speaker=sec.speaker_or_author or doc_speaker,
                    timestamp=doc_date,
                    text_content=content,
                    chunk_type="tabular_record",
                    word_count=len(words)
                )
            ]

        # 2. Check for speaker turns line by line (typical in Actas de Comité de Convivencia)
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        line_chunks: List[DocumentChunk] = []
        current_speaker = doc_speaker
        current_buffer: List[str] = []

        for line in lines:
            speaker_match = SPEAKER_TURN_REGEX.match(line)
            numbered_match = NUMBERED_ITEM_REGEX.match(line)

            if speaker_match:
                # Flush previous speaker buffer if exists
                if current_buffer:
                    buf_text = " ".join(current_buffer)
                    words_count = len(buf_text.split())
                    if words_count >= self.target_min_words:
                        line_chunks.append(
                            DocumentChunk(
                                chunk_id=f"chk-{uuid.uuid4().hex[:8]}",
                                file_path=doc.file_path,
                                file_name=doc.file_name,
                                department=doc.department,
                                section_title=sec.section_title or "Intervención",
                                speaker=current_speaker,
                                timestamp=doc_date,
                                text_content=buf_text,
                                chunk_type="speaker_intervention",
                                word_count=words_count
                            )
                        )
                    current_buffer = []

                current_speaker = speaker_match.group(1).strip()
                speech_text = speaker_match.group(2).strip()
                if speech_text:
                    current_buffer.append(speech_text)

            elif numbered_match and not current_buffer:
                # Numbered agenda point
                item_text = line
                words_count = len(item_text.split())
                if words_count >= self.target_min_words:
                    line_chunks.append(
                        DocumentChunk(
                            chunk_id=f"chk-{uuid.uuid4().hex[:8]}",
                            file_path=doc.file_path,
                            file_name=doc.file_name,
                            department=doc.department,
                            section_title=f"{sec.section_title or 'Punto'}: {numbered_match.group(1)}",
                            speaker=current_speaker,
                            timestamp=doc_date,
                            text_content=item_text,
                            chunk_type="agenda_item",
                            word_count=words_count
                        )
                    )
            else:
                current_buffer.append(line)

        # Flush trailing buffer
        if current_buffer:
            buf_text = " ".join(current_buffer)
            words_count = len(buf_text.split())
            if words_count >= self.target_min_words:
                line_chunks.append(
                    DocumentChunk(
                        chunk_id=f"chk-{uuid.uuid4().hex[:8]}",
                        file_path=doc.file_path,
                        file_name=doc.file_name,
                        department=doc.department,
                        section_title=sec.section_title or "Intervención",
                        speaker=current_speaker,
                        timestamp=doc_date,
                        text_content=buf_text,
                        chunk_type="speaker_intervention" if current_speaker != doc_speaker else "paragraph",
                        word_count=words_count
                    )
                )

        if line_chunks:
            # Check if any chunk in line_chunks is excessively large (> target_max_words)
            final_chunks: List[DocumentChunk] = []
            for chk in line_chunks:
                if chk.word_count > self.target_max_words:
                    sub_chunks = self._chunk_free_text(
                        text=chk.text_content,
                        doc=doc,
                        section_title=chk.section_title,
                        default_speaker=chk.speaker or doc_speaker,
                        default_timestamp=chk.timestamp
                    )
                    final_chunks.extend(sub_chunks)
                else:
                    final_chunks.append(chk)
            return final_chunks

        # 3. Fallback: windowing for general paragraph or narrative
        return self._chunk_free_text(
            text=content,
            doc=doc,
            section_title=sec.section_title or "Sección",
            default_speaker=doc_speaker,
            default_timestamp=doc_date
        )

    def _chunk_free_text(
        self,
        text: str,
        doc: ExtractedDocument,
        section_title: Optional[str],
        default_speaker: str,
        default_timestamp: datetime
    ) -> List[DocumentChunk]:
        """Breaks monolithic text into word-capped chunks with overlap."""
        words = text.split()
        total_words = len(words)

        if total_words < self.target_min_words:
            return []

        if total_words <= self.target_max_words:
            return [
                DocumentChunk(
                    chunk_id=f"chk-{uuid.uuid4().hex[:8]}",
                    file_path=doc.file_path,
                    file_name=doc.file_name,
                    department=doc.department,
                    section_title=section_title,
                    speaker=default_speaker,
                    timestamp=default_timestamp,
                    text_content=text,
                    chunk_type="paragraph",
                    word_count=total_words
                )
            ]

        # Windowing with overlap
        chunks: List[DocumentChunk] = []
        step = max(1, self.target_max_words - self.overlap_words)

        for start_idx in range(0, total_words, step):
            end_idx = min(start_idx + self.target_max_words, total_words)
            chunk_words = words[start_idx:end_idx]

            if len(chunk_words) < self.target_min_words:
                break

            sub_text = " ".join(chunk_words)
            part_num = len(chunks) + 1
            chunks.append(
                DocumentChunk(
                    chunk_id=f"chk-{uuid.uuid4().hex[:8]}",
                    file_path=doc.file_path,
                    file_name=doc.file_name,
                    department=doc.department,
                    section_title=f"{section_title} (Parte {part_num})",
                    speaker=default_speaker,
                    timestamp=default_timestamp,
                    text_content=sub_text,
                    chunk_type="paragraph",
                    word_count=len(chunk_words)
                )
            )

            if end_idx >= total_words:
                break

        return chunks

    @staticmethod
    def chunk_to_raw_message(chunk: DocumentChunk) -> RawMessage:
        """Converts a DocumentChunk into a RawMessage for seamless ingestion into the Telemetry Engine."""
        channel_type = ChannelType.DOCUMENT
        if chunk.file_name.lower().endswith(".eml"):
            channel_type = ChannelType.EMAIL

        return RawMessage(
            message_id=chunk.chunk_id,
            sender_id=chunk.speaker or "Colaborador_Documental",
            department=chunk.department,
            timestamp=chunk.timestamp,
            text_content=chunk.text_content,
            channel=channel_type
        )
