"""
Workplace-Pulse-Telemetry: Local Hierarchical Directory & Archive Scanner
Engineered by Fabio Torres (neurodeveloper11)

Recursively navigates enterprise folder structures and ZIP archives,
inferring organizational hierarchy (departments, units, dates) from folder patterns and file metadata.
"""

import os
import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from src.schemas import ScannedDocumentItem

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".eml", ".txt"}

# Canonical department aliases for pattern matching in folder paths
DEPARTMENT_PATTERNS = {
    "Operaciones_Portuarias": [
        r"operacion(?:es)?(?:_portuarias?)?", r"puerto", r"terminal", r"muelle", r"patio"
    ],
    "Ingenieria_Core": [
        r"ingenier[ií]a", r"engineering", r"sistemas", r"desarrollo", r"it(?:_core)?", r"tecnolog[ií]a", r"dev"
    ],
    "Talento_Humano": [
        r"talento_humano", r"recursos_humanos", r"rrhh", r"human_resources", r"hr", r"gestion_humana"
    ],
    "Finanzas_Contabilidad": [
        r"finanzas", r"contabilidad", r"finance", r"tesorer[ií]a", r"auditor[ií]a(?:s)?"
    ],
    "Logistica_Comercial": [
        r"log[ií]stica", r"logistics", r"almac[eé]n", r"bodega", r"cadena_suministro", r"supply"
    ],
    "Comite_Convivencia_SST": [
        r"comit[eé](?:_convivencia)?", r"convivencia", r"sst", r"salud_ocupacional", r"seguridad_salud", r"hse"
    ],
    "Atencion_Cliente": [
        r"atenci[oó]n_cliente", r"servicio_cliente", r"customer(?:_operations)?", r"soporte", r"call_center"
    ]
}

MONTH_REGEX = re.compile(
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|"
    r"january|february|march|april|may|june|july|august|september|october|november|december|"
    r"ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)",
    re.IGNORECASE
)

YEAR_REGEX = re.compile(r"(?:^|[\D_])(20\d{2})(?:[\D_]|$)")


class HierarchyScanner:
    """
    On-premise scanner capable of inspecting enterprise directories and ZIP bundles.
    Infers department and period without cloud dependencies.
    """

    def __init__(self, default_department: str = "General_Corporativo"):
        self.default_department = default_department

    def infer_metadata_from_path(self, relative_path: str, full_path: Optional[str] = None) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Parses a relative path (e.g. 'Operaciones_Portuarias/2026/Actas/acta_01.docx')
        and extracts (department, team_unit, year_or_period).
        If relative path lacks department clues, optionally inspects full_path.
        """
        # Normalize slashes
        clean_path = relative_path.replace("\\", "/").strip("/")
        parts = clean_path.split("/")

        detected_dept = None
        detected_year = None
        detected_unit = None

        # 1. Search for known department patterns across all path tokens
        for part in parts[:-1]:  # exclude file name from pure folder search
            part_lower = part.lower().strip()
            for canonical_name, patterns in DEPARTMENT_PATTERNS.items():
                for pat in patterns:
                    if re.search(r"^" + pat + r"$", part_lower) or re.search(r"[\b_]" + pat + r"[\b_]", f"_{part_lower}_"):
                        detected_dept = canonical_name
                        break
                if detected_dept:
                    break
            if detected_dept:
                break

        # 1b. Fallback to full_path if not detected in relative_path
        if not detected_dept and full_path:
            clean_full = full_path.replace("\\", "/").strip("/")
            full_parts = clean_full.split("/")
            for part in full_parts[:-1]:
                part_lower = part.lower().strip()
                for canonical_name, patterns in DEPARTMENT_PATTERNS.items():
                    for pat in patterns:
                        if re.search(r"^" + pat + r"$", part_lower) or re.search(r"[\b_]" + pat + r"[\b_]", f"_{part_lower}_"):
                            detected_dept = canonical_name
                            break
                    if detected_dept:
                        break
                if detected_dept:
                    break

        # 2. Extract year and month from path and filename
        path_to_search_date = full_path if full_path else clean_path
        year_match = YEAR_REGEX.search(path_to_search_date)
        if year_match:
            detected_year = year_match.group(1)
        
        month_match = MONTH_REGEX.search(path_to_search_date)
        if month_match and detected_year:
            detected_year = f"{detected_year}-{month_match.group(0).lower()}"
        elif not detected_year:
            detected_year = str(datetime.now().year)

        # 3. If department not matched by catalog, use first non-year, non-root directory
        if not detected_dept and len(parts) > 1:
            for part in parts[:-1]:
                if not YEAR_REGEX.match(part) and part.lower() not in ["empresa", "corporativo", "docs", "archivos", "data"]:
                    clean_folder = re.sub(r"[^\w\-]", "_", part).strip("_")
                    if clean_folder:
                        detected_dept = clean_folder.title()
                        break

        if not detected_dept:
            detected_dept = self.default_department

        # 4. Infer team unit if multiple nested subfolders exist
        if len(parts) > 2:
            subfolder = parts[-2]
            if subfolder.lower() != detected_dept.lower() and not YEAR_REGEX.match(subfolder):
                detected_unit = subfolder.replace("_", " ").title()

        return detected_dept, detected_unit, detected_year

    def scan_directory(self, root_dir: str) -> List[ScannedDocumentItem]:
        """Recursively scans a local directory for supported multi-format documents."""
        results: List[ScannedDocumentItem] = []
        root_path = Path(root_dir).resolve()

        if not root_path.exists() or not root_path.is_dir():
            return results

        for current_root, dirs, files in os.walk(root_path):
            # Ignore hidden directories like .git
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in sorted(files):
                # Ignore hidden or lock files
                if file.startswith(".") or file.startswith("~$"):
                    continue

                file_path = Path(current_root) / file
                ext = file_path.suffix.lower()

                if ext in SUPPORTED_EXTENSIONS:
                    try:
                        rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")
                        size = file_path.stat().st_size
                    except Exception:
                        rel_path = file
                        size = 0

                    dept, unit, year = self.infer_metadata_from_path(rel_path, full_path=str(file_path))

                    results.append(
                        ScannedDocumentItem(
                            file_path=str(file_path),
                            relative_path=rel_path,
                            file_name=file,
                            file_extension=ext,
                            department=dept,
                            team_unit=unit,
                            year_or_period=year,
                            file_size_bytes=size,
                        )
                    )

        return results

    def extract_and_scan_zip(self, zip_path_or_bytes: Any) -> Tuple[List[ScannedDocumentItem], str]:
        """
        Extracts a ZIP archive into an isolated temporary directory with path traversal protection,
        then scans it for documents.
        Returns:
            scanned_items: List of discovered ScannedDocumentItem
            temp_dir: Path to the temporary extraction directory (caller should clean up with shutil.rmtree)
        """
        temp_dir = tempfile.mkdtemp(prefix="wpt_zip_")

        try:
            if isinstance(zip_path_or_bytes, (str, Path)):
                archive = zipfile.ZipFile(zip_path_or_bytes, "r")
            else:
                archive = zipfile.ZipFile(zip_path_or_bytes)

            with archive as zf:
                for member in zf.infolist():
                    # Security check: Prevent Zip Slip path traversal vulnerability
                    extracted_path = Path(os.path.abspath(os.path.join(temp_dir, member.filename)))
                    if not str(extracted_path).startswith(os.path.abspath(temp_dir)):
                        continue  # skip malicious archive member

                    zf.extract(member, temp_dir)

            scanned = self.scan_directory(temp_dir)
            return scanned, temp_dir
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
