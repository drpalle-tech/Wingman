"""Turning a context bundle into prompt text, plus project/framework detection."""

import json
import re
import tomllib
from typing import Iterable, Optional

from .languages import CODE_LANGUAGES
from .schemas import ContextBundle, ContextFile, Framework, ProjectInfo

KNOWN_JS_PACKAGES = {
    "react", "react-dom", "next", "vue", "@angular/core", "svelte", "express", "typescript",
    "jest", "vitest", "@testing-library/react", "react-router-dom", "@reduxjs/toolkit", "redux",
    "zustand", "@tanstack/react-query", "axios", "vite", "tailwindcss",
}
KNOWN_PY_PACKAGES = {
    "django", "flask", "fastapi", "pydantic", "sqlalchemy", "pytest", "celery", "requests",
    "httpx", "aiohttp", "numpy", "pandas", "uvicorn", "alembic",
}
KNOWN_DOTNET_PREFIXES = (
    "Microsoft.AspNetCore", "Microsoft.EntityFrameworkCore", "Microsoft.Data.SqlClient", "xunit",
    "NUnit", "MSTest", "Moq", "NSubstitute", "Dapper", "Newtonsoft.Json", "Serilog", "AutoMapper",
    "MediatR", "FluentValidation", "Polly",
)
REACT_IMPORT = re.compile(r"""from\s+['"]react['"]|require\(\s*['"]react['"]\s*\)""")


def number_lines(text: str) -> str:
    lines = text.splitlines()
    width = len(str(max(len(lines), 1)))
    return "\n".join(f"{i:>{width}} | {line}" for i, line in enumerate(lines, 1))


def render_file(f: ContextFile, numbered: bool) -> str:
    body = number_lines(f.content) if numbered else f.content
    return f'<file path="{f.path}" language="{f.resolved_language}" role="{f.role}">\n{body}\n</file>'


def render_project(project: ProjectInfo) -> str:
    lines = []
    if project.languages:
        lines.append(f"- Languages: {', '.join(project.languages)}")
    if project.frameworks:
        items = [f"{fw.name} {fw.version}".strip() if fw.version else fw.name for fw in project.frameworks]
        lines.append(f"- Frameworks and libraries: {', '.join(items)}")
    if project.runtime:
        lines.append(f"- Runtime: {project.runtime}")
    return "\n".join(lines) if lines else "- Nothing detected; infer from the code."


def render_bundle(bundle: ContextBundle, project: ProjectInfo, number_targets: bool) -> str:
    parts = ["## Project", render_project(project), "", "## Files"]
    order = {"target": 0, "related": 1, "config": 2}
    for f in sorted(bundle.files, key=lambda f: order[f.role]):
        parts.append(render_file(f, numbered=number_targets and f.role == "target"))
    if bundle.diagnostics:
        parts += ["", "## Existing compiler/linter diagnostics"]
        for d in bundle.diagnostics:
            source = f" {d.source}:" if d.source else ""
            parts.append(f"- {d.path}:{d.line} [{d.severity}]{source} {d.message}")
    return "\n".join(parts)


def selected_text(bundle: ContextBundle) -> Optional[str]:
    sel = bundle.selection
    if sel is None:
        return None
    f = bundle.file_by_path(sel.path)
    if f is None:
        return None
    lines = f.content.splitlines()
    return "\n".join(lines[sel.start_line - 1 : sel.end_line])


def detect_project(files: Iterable[ContextFile], declared: Optional[ProjectInfo]) -> ProjectInfo:
    files = list(files)
    frameworks: dict[str, Optional[str]] = {}
    runtime: Optional[str] = None

    for f in files:
        name = f.path.rsplit("/", 1)[-1].lower()
        if name == "package.json":
            frameworks.update(_from_package_json(f.content))
        elif name.endswith(".csproj"):
            found, target = _from_csproj(f.content)
            frameworks.update(found)
            runtime = runtime or target
        elif name.startswith("requirements") and name.endswith(".txt"):
            frameworks.update(_from_requirements(f.content.splitlines()))
        elif name == "pyproject.toml":
            found, python = _from_pyproject(f.content)
            frameworks.update(found)
            runtime = runtime or python

    code_files = [f for f in files if f.role != "config"]
    if "react" not in frameworks and any(
        f.path.lower().endswith((".tsx", ".jsx")) or REACT_IMPORT.search(f.content) for f in code_files
    ):
        frameworks["react"] = None

    languages = sorted({f.resolved_language for f in code_files if f.resolved_language in CODE_LANGUAGES})

    if declared:
        languages = sorted(set(languages) | {lang.lower() for lang in declared.languages})
        for fw in declared.frameworks:
            frameworks[fw.name] = fw.version or frameworks.get(fw.name)
        runtime = declared.runtime or runtime

    return ProjectInfo(
        languages=languages,
        frameworks=[Framework(name=n, version=v) for n, v in sorted(frameworks.items())],
        runtime=runtime,
    )


def _from_package_json(text: str) -> dict[str, Optional[str]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    found = {}
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        deps = data.get(section)
        if isinstance(deps, dict):
            for name, version in deps.items():
                if name in KNOWN_JS_PACKAGES:
                    found[name] = str(version).lstrip("^~>=<")
    return found


def _from_csproj(text: str) -> tuple[dict[str, Optional[str]], Optional[str]]:
    found: dict[str, Optional[str]] = {}
    if re.search(r'Sdk="Microsoft\.NET\.Sdk\.Web"', text):
        found["ASP.NET Core"] = None
    for match in re.finditer(r'<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]+)")?', text):
        name, version = match.group(1), match.group(2)
        if name.startswith(KNOWN_DOTNET_PREFIXES):
            found[name] = version
    target = re.search(r"<TargetFrameworks?>([^<]+)</TargetFrameworks?>", text)
    return found, (f".NET {target.group(1).strip()}" if target else None)


def _from_requirements(lines: Iterable[str]) -> dict[str, Optional[str]]:
    found: dict[str, Optional[str]] = {}
    for line in lines:
        line = line.split("#", 1)[0].strip()
        match = re.match(r"([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*(?:[=~<>!]=?\s*([^\s,;]+))?", line)
        if match and match.group(1).lower() in KNOWN_PY_PACKAGES:
            found[match.group(1).lower()] = match.group(2)
    return found


def _from_pyproject(text: str) -> tuple[dict[str, Optional[str]], Optional[str]]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}, None
    project = data.get("project", {}) if isinstance(data.get("project"), dict) else {}
    deps = project.get("dependencies", [])
    found = _from_requirements(deps) if isinstance(deps, list) else {}
    python = project.get("requires-python")
    return found, (f"Python {python}" if python else None)
