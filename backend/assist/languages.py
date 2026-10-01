from pathlib import PurePosixPath
from typing import Optional

EXTENSION_LANGUAGES = {
    ".py": "python",
    ".pyi": "python",
    ".cs": "csharp",
    ".csx": "csharp",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".json": "json",
    ".csproj": "xml",
    ".props": "xml",
    ".xml": "xml",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".md": "markdown",
}

CODE_LANGUAGES = {"python", "csharp", "typescript", "javascript"}


def language_for(path: str, declared: Optional[str] = None) -> str:
    if declared:
        return declared.strip().lower()
    return EXTENSION_LANGUAGES.get(PurePosixPath(path).suffix.lower(), "text")
