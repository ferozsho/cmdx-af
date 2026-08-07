"""Code Chunker for Local RAG Vector Indexing."""

from pathlib import Path
from typing import Any, Dict, List


class CodeChunker:
    """Splits source code files into semantic text chunks with line metadata."""

    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".json", ".html", ".css", ".sql", ".yaml", ".yml"
    }

    @classmethod
    def chunk_file(cls, file_path: Path, chunk_size: int = 50, overlap: int = 10) -> List[Dict[str, Any]]:
        """Chunk a single file into overlapping line segments."""
        if file_path.suffix not in cls.SUPPORTED_EXTENSIONS or not file_path.is_file():
            return []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return []

        if not lines:
            return []

        chunks: List[Dict[str, Any]] = []
        total_lines = len(lines)
        start = 0

        while start < total_lines:
            end = min(start + chunk_size, total_lines)
            chunk_content = "".join(lines[start:end])
            chunks.append({
                "start_line": start + 1,
                "end_line": end,
                "content": chunk_content,
                "extension": file_path.suffix,
            })
            if end == total_lines:
                break
            start += chunk_size - overlap

        return chunks
