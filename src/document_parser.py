"""
Workplace-Pulse-Telemetry: Local-First Multi-Format Document Parser
Engineered by Fabio Torres (neurodeveloper11)

Extracts clean, structured text and metadata from PDF, DOCX, XLSX, CSV, EML and TXT
without any cloud or heavy GPU dependencies.
"""

import os
import re
import csv
import email
from email import policy
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field

import pandas as pd
from pypdf import PdfReader
import docx

from src.schemas import ScannedDocumentItem


class ExtractedSection(BaseModel):
    """Structured segment extracted from a document before discursive chunking."""
    section_title: Optional[str] = None
    speaker_or_author: Optional[str] = None
    timestamp: Optional[datetime] = None
    content: str
    section_type: str = "paragraph"  # 'heading', 'paragraph', 'table_row', 'email_body', 'tabular_record'


class ExtractedDocument(BaseModel):
    """Complete structured extraction result of an ingested document."""
    file_path: str
    file_name: str
    file_extension: str
    department: str
    detected_date: Optional[datetime] = None
    author: Optional[str] = None
    title: Optional[str] = None
    sections: List[ExtractedSection] = Field(default_factory=list)
    raw_full_text: str = ""


class LocalDocumentParser:
    """
    On-premise zero-leakage document parser supporting:
    - PDF (.pdf) via pypdf
    - Word (.docx) via python-docx
    - Excel & CSV (.xlsx, .csv) via pandas + openpyxl
    - Emails & Memos (.eml, .txt) via standard email & io
    """

    NARRATIVE_COLUMN_KEYWORDS = [
        r"observaci[oó]n", r"descripci[oó]n", r"motivo", r"comentario",
        r"justificaci[oó]n", r"hecho", r"incidente", r"queja", r"descargo",
        r"bit[aá]cora", r"nota", r"detalle", r"asunto", r"narrativa",
        r"situaci[oó]n", r"reporte", r"comunicado", r"mensaje", r"intervenci[oó]n"
    ]

    def __init__(self):
        self._narrative_col_regex = re.compile(
            "|".join(self.NARRATIVE_COLUMN_KEYWORDS), re.IGNORECASE
        )

    def parse_document(self, item: ScannedDocumentItem) -> ExtractedDocument:
        """Parses a document according to its file extension."""
        ext = item.file_extension.lower()
        path = item.file_path

        if ext == ".pdf":
            return self._parse_pdf(item)
        elif ext == ".docx":
            return self._parse_docx(item)
        elif ext in [".xlsx", ".xls"]:
            return self._parse_excel(item)
        elif ext == ".csv":
            return self._parse_csv(item)
        elif ext == ".eml":
            return self._parse_eml(item)
        elif ext == ".txt":
            return self._parse_txt(item)
        else:
            raise ValueError(f"Unsupported document format: {ext}")

    def _parse_pdf(self, item: ScannedDocumentItem) -> ExtractedDocument:
        """Extracts text page-by-page from PDF files."""
        reader = PdfReader(item.file_path)
        sections: List[ExtractedSection] = []
        full_text_parts: List[str] = []

        # Read document metadata
        doc_title = None
        doc_author = None
        doc_date = None

        if reader.metadata:
            doc_title = reader.metadata.title
            doc_author = reader.metadata.author
            creation_date_raw = reader.metadata.get("/CreationDate")
            if creation_date_raw and isinstance(creation_date_raw, str):
                # PDF date format: D:YYYYMMDDHHmmSS
                m = re.search(r"D:(\d{4})(\d{2})(\d{2})", creation_date_raw)
                if m:
                    try:
                        doc_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                    except Exception:
                        pass

        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            clean_page_text = page_text.strip()
            if clean_page_text:
                full_text_parts.append(clean_page_text)
                sections.append(
                    ExtractedSection(
                        section_title=f"Página {page_idx + 1}",
                        speaker_or_author=doc_author,
                        timestamp=doc_date,
                        content=clean_page_text,
                        section_type="paragraph",
                    )
                )

        return ExtractedDocument(
            file_path=item.file_path,
            file_name=item.file_name,
            file_extension=item.file_extension,
            department=item.department,
            detected_date=doc_date,
            author=doc_author,
            title=doc_title or item.file_name,
            sections=sections,
            raw_full_text="\n\n".join(full_text_parts),
        )

    def _parse_docx(self, item: ScannedDocumentItem) -> ExtractedDocument:
        """Extracts paragraphs, headers, and tables from Word (.docx) documents."""
        doc = docx.Document(item.file_path)
        sections: List[ExtractedSection] = []
        full_text_parts: List[str] = []

        doc_author = doc.core_properties.author or None
        doc_date = doc.core_properties.created or None
        doc_title = doc.core_properties.title or None

        current_heading = "Introducción"

        # 1. Process paragraphs
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            style_name = (para.style.name or "").lower()
            if "heading" in style_name or "título" in style_name:
                current_heading = text
                sections.append(
                    ExtractedSection(
                        section_title=current_heading,
                        speaker_or_author=doc_author,
                        timestamp=doc_date,
                        content=text,
                        section_type="heading",
                    )
                )
            else:
                sections.append(
                    ExtractedSection(
                        section_title=current_heading,
                        speaker_or_author=doc_author,
                        timestamp=doc_date,
                        content=text,
                        section_type="paragraph",
                    )
                )
            full_text_parts.append(text)

        # 2. Process tables
        for table_idx, table in enumerate(doc.tables):
            headers = []
            for row_idx, row in enumerate(table.rows):
                row_cells = [cell.text.strip() for cell in row.cells]
                if row_idx == 0:
                    headers = row_cells
                else:
                    row_pairs = []
                    for h_idx, cell_val in enumerate(row_cells):
                        col_name = headers[h_idx] if h_idx < len(headers) and headers[h_idx] else f"Col_{h_idx+1}"
                        if cell_val:
                            row_pairs.append(f"{col_name}: {cell_val}")
                    if row_pairs:
                        row_summary = " | ".join(row_pairs)
                        sections.append(
                            ExtractedSection(
                                section_title=f"Tabla {table_idx + 1}",
                                speaker_or_author=doc_author,
                                timestamp=doc_date,
                                content=row_summary,
                                section_type="table_row",
                            )
                        )
                        full_text_parts.append(row_summary)

        return ExtractedDocument(
            file_path=item.file_path,
            file_name=item.file_name,
            file_extension=item.file_extension,
            department=item.department,
            detected_date=doc_date,
            author=doc_author,
            title=doc_title or item.file_name,
            sections=sections,
            raw_full_text="\n\n".join(full_text_parts),
        )

    def _parse_excel(self, item: ScannedDocumentItem) -> ExtractedDocument:
        """Extracts free-text columns from Excel workbooks (.xlsx)."""
        sections: List[ExtractedSection] = []
        full_text_parts: List[str] = []

        excel_file = pd.ExcelFile(item.file_path, engine="openpyxl")
        sheet_names = excel_file.sheet_names

        for sheet in sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet)
            sheet_sections, sheet_texts = self._process_dataframe_text_rows(df, context_label=sheet)
            sections.extend(sheet_sections)
            full_text_parts.extend(sheet_texts)

        return ExtractedDocument(
            file_path=item.file_path,
            file_name=item.file_name,
            file_extension=item.file_extension,
            department=item.department,
            detected_date=None,
            author=None,
            title=item.file_name,
            sections=sections,
            raw_full_text="\n\n".join(full_text_parts),
        )

    def _parse_csv(self, item: ScannedDocumentItem) -> ExtractedDocument:
        """Extracts free-text columns from CSV files with encoding detection."""
        encodings_to_try = ["utf-8", "latin1", "cp1252"]
        df = None

        for enc in encodings_to_try:
            try:
                # Detect separator
                with open(item.file_path, "r", encoding=enc, errors="replace") as f:
                    sample = f.read(2048)
                    sep = ","
                    if sample.count(";") > sample.count(","):
                        sep = ";"
                    elif sample.count("\t") > sample.count(","):
                        sep = "\t"

                df = pd.read_csv(item.file_path, encoding=enc, sep=sep)
                break
            except Exception:
                continue

        if df is None:
            df = pd.DataFrame()

        sections, full_text_parts = self._process_dataframe_text_rows(df, context_label="CSV")

        return ExtractedDocument(
            file_path=item.file_path,
            file_name=item.file_name,
            file_extension=item.file_extension,
            department=item.department,
            detected_date=None,
            author=None,
            title=item.file_name,
            sections=sections,
            raw_full_text="\n\n".join(full_text_parts),
        )

    def _process_dataframe_text_rows(self, df: pd.DataFrame, context_label: str) -> Tuple[List[ExtractedSection], List[str]]:
        """Scans a DataFrame to locate free-text narrative columns and turns each significant row into an ExtractedSection."""
        sections: List[ExtractedSection] = []
        full_text_parts: List[str] = []

        if df.empty:
            return sections, full_text_parts

        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]

        # 1. Identify date column
        date_col = None
        for col in df.columns:
            if re.search(r"\b(fecha|date|timestamp|dia)\b", col, re.IGNORECASE):
                date_col = col
                break

        # 2. Identify author / speaker column
        author_col = None
        for col in df.columns:
            if re.search(r"\b(empleado|colaborador|autor|usuario|nombre|persona|remitente|user)\b", col, re.IGNORECASE):
                author_col = col
                break

        # 3. Identify narrative columns
        narrative_cols = []
        for col in df.columns:
            if col in [date_col, author_col]:
                continue
            # Check by name
            if self._narrative_col_regex.search(col):
                narrative_cols.append(col)
                continue
            # Check by average word count of string entries
            str_series = df[col].dropna().astype(str)
            if not str_series.empty:
                avg_words = str_series.apply(lambda x: len(x.split())).mean()
                if avg_words >= 3.0:
                    narrative_cols.append(col)

        if not narrative_cols:
            # Fallback: take all object/string columns
            narrative_cols = [c for c in df.select_dtypes(include=["object"]).columns if c not in [date_col, author_col]]

        # 4. Extract rows
        for idx, row in df.iterrows():
            row_date = None
            if date_col and pd.notna(row[date_col]):
                try:
                    row_date = pd.to_datetime(row[date_col]).to_pydatetime()
                except Exception:
                    pass

            row_author = str(row[author_col]).strip() if author_col and pd.notna(row[author_col]) else None

            row_texts = []
            for col in narrative_cols:
                val = row[col]
                if pd.notna(val):
                    val_str = str(val).strip()
                    if len(val_str) > 5:
                        row_texts.append(f"[{col}]: {val_str}")

            if row_texts:
                content = " | ".join(row_texts)
                sections.append(
                    ExtractedSection(
                        section_title=f"{context_label} - Fila {idx + 1}",
                        speaker_or_author=row_author,
                        timestamp=row_date,
                        content=content,
                        section_type="tabular_record",
                    )
                )
                full_text_parts.append(content)

        return sections, full_text_parts

    def _parse_eml(self, item: ScannedDocumentItem) -> ExtractedDocument:
        """Extracts email headers, sender, date, subject and plain text body from .eml files."""
        with open(item.file_path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        sender = msg.get("From", "")
        recipients = msg.get("To", "")
        subject = msg.get("Subject", "")
        date_str = msg.get("Date", "")

        msg_date = None
        if date_str:
            try:
                msg_date = email.utils.parsedate_to_datetime(date_str)
                if msg_date.tzinfo:
                    msg_date = msg_date.replace(tzinfo=None)
            except Exception:
                pass

        # Extract body
        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disp = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in content_disp:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_text += payload.decode(charset, errors="replace") + "\n"
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body_text = payload.decode(charset, errors="replace")

        sections: List[ExtractedSection] = []
        header_summary = f"De: {sender} | Para: {recipients} | Asunto: {subject}"
        sections.append(
            ExtractedSection(
                section_title="Encabezados de Correo",
                speaker_or_author=sender,
                timestamp=msg_date,
                content=header_summary,
                section_type="email_header",
            )
        )

        clean_body = body_text.strip()
        if clean_body:
            sections.append(
                ExtractedSection(
                    section_title=f"Asunto: {subject}",
                    speaker_or_author=sender,
                    timestamp=msg_date,
                    content=clean_body,
                    section_type="email_body",
                )
            )

        raw_full = f"{header_summary}\n\n{clean_body}"
        return ExtractedDocument(
            file_path=item.file_path,
            file_name=item.file_name,
            file_extension=item.file_extension,
            department=item.department,
            detected_date=msg_date,
            author=sender,
            title=subject or item.file_name,
            sections=sections,
            raw_full_text=raw_full,
        )

    def _parse_txt(self, item: ScannedDocumentItem) -> ExtractedDocument:
        """Parses raw text files (.txt) with robust encoding fallback."""
        encodings = ["utf-8", "latin1", "cp1252"]
        content = ""

        for enc in encodings:
            try:
                with open(item.file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except Exception:
                continue

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        sections = [
            ExtractedSection(
                section_title=f"Sección {i+1}",
                speaker_or_author=None,
                timestamp=None,
                content=p,
                section_type="paragraph",
            )
            for i, p in enumerate(paragraphs)
        ]

        return ExtractedDocument(
            file_path=item.file_path,
            file_name=item.file_name,
            file_extension=item.file_extension,
            department=item.department,
            detected_date=None,
            author=None,
            title=item.file_name,
            sections=sections,
            raw_full_text=content,
        )
