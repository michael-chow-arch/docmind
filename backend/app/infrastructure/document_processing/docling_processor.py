from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import ProcessingError


@dataclass
class ExtractedChunk:
    content: str
    page_number: int | None
    chunk_index: int
    meta: dict


class DoclingProcessor:

    def process(self, file_path: str) -> dict[str, Any]:
        chunks, pages = self._extract_with_pypdf2(file_path)
        
        if chunks is not None:
            return {"pages": pages, "chunks": chunks, "images": [], "tables": []}
        
        try:
            from docling.document_converter import DocumentConverter  # type: ignore
        except Exception as e:
            raise ProcessingError("Docling import failed. Install docling.") from e

        converter = DocumentConverter()
        result = converter.convert(file_path)
        doc = getattr(result, "document", None) or result

        pages = None
        pages_obj = getattr(doc, "pages", None)
        if pages_obj is not None:
            try:
                pages = len(pages_obj)
            except Exception:
                pages = None

        text = ""
        for method in ("export_to_markdown", "export_to_text"):
            fn = getattr(doc, method, None)
            if callable(fn):
                try:
                    text = fn()
                    if text and isinstance(text, str):
                        break
                except Exception:
                    pass
        if not text:
            text = str(doc)
        chunks = self._chunk_text(text, page_number=None)

        return {"pages": pages, "chunks": chunks, "images": [], "tables": []}

    def _extract_with_pypdf2(self, file_path: str) -> tuple[list[ExtractedChunk] | None, int | None]:
        try:
            import PyPDF2  # type: ignore
        except ImportError:
            return None, None

        try:
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                pages = len(pdf_reader.pages)
                
                if pages == 0:
                    return None, None

                all_chunks: list[ExtractedChunk] = []
                chunk_index = 0

                for page_num in range(1, pages + 1):
                    page = pdf_reader.pages[page_num - 1]
                    page_text = page.extract_text() or ""
                    
                    if not self._is_valid_page_text(page_text):
                        continue
                    cleaned_text = self._clean_page_text(page_text)
                    page_chunks = self._chunk_text(cleaned_text, page_number=page_num, start_index=chunk_index)
                    all_chunks.extend(page_chunks)
                    chunk_index += len(page_chunks)

                return all_chunks, pages
        except Exception:
            return None, None

    def _is_valid_page_text(self, text: str) -> bool:
        text = text.strip()
        
        if len(text) < 10:
            return False
        alpha_count = sum(1 for c in text if c.isalpha())
        if alpha_count < len(text) * 0.3:
            return False
        text_lower = text.lower()
        junk_patterns = [
            r"^\d+$",
            r"^page\s+\d+$",
            r"^\d+\s*/\s*\d+$",
        ]
        for pattern in junk_patterns:
            if re.match(pattern, text_lower):
                return False
        
        return True

    def _clean_page_text(self, text: str) -> str:
        if not text:
            return text

        lines = text.split("\n")
        cleaned_lines = [line for line in lines if not re.match(r"^\s*\d+\s*$", line.strip())]
        text = "\n".join(cleaned_lines)
        text = re.sub(r"([a-zA-Z])-\n([a-zA-Z])", r"\1-\2", text)

        paragraphs = text.split("\n\n")
        normalized_paragraphs = [re.sub(r" +", " ", re.sub(r"\n+", " ", para).strip()) for para in paragraphs]
        text = "\n\n".join(normalized_paragraphs)

        text = re.sub(r"(?:^|\n\n)\s*\d+\s+(?=[A-Za-z])", "", text)
        text = re.sub(r"(?<=[A-Za-z])\s+\d+\s*(?=\n\n|$)", "", text)

        return text.strip()

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 1200,
        overlap: int = 120,
        page_number: int | None = None,
        start_index: int = 0
    ) -> list[ExtractedChunk]:
        text = (text or "").strip()
        if not text:
            return []

        chunks: list[ExtractedChunk] = []
        start, idx, n = 0, start_index, len(text)
        while start < n:
            end = min(start + chunk_size, n)
            content = text[start:end].strip()
            if content:
                chunks.append(ExtractedChunk(content=content, page_number=page_number, chunk_index=idx, meta={}))
                idx += 1
            if end == n:
                break
            start = max(0, end - overlap)
        return chunks
