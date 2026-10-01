"""Loads prompt files and picks the language checklists relevant to a bundle."""

from functools import lru_cache
from pathlib import Path

from .schemas import ContextBundle, ProjectInfo

PROMPT_DIR = Path(__file__).parent / "prompts"
REACT_FRAMEWORKS = {"react", "react-dom", "next"}


@lru_cache(maxsize=None)
def load(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def guide_names(bundle: ContextBundle, project: ProjectInfo) -> list[str]:
    languages = {f.resolved_language for f in bundle.files if f.role != "config"} | set(project.languages)
    names = []
    if "python" in languages:
        names.append("python")
    if "csharp" in languages:
        names.append("csharp")
    if languages & {"typescript", "javascript"}:
        names.append("typescript")
    if any(fw.name.lower() in REACT_FRAMEWORKS for fw in project.frameworks):
        names.append("react")
    return names


def system_prompt(task: str, bundle: ContextBundle, project: ProjectInfo) -> str:
    parts = [load(f"{task}.md")]
    guides = [load(f"languages/{name}.md") for name in guide_names(bundle, project)]
    if guides:
        heading = "## Checklist: what to look for" if task == "review" else "## Pitfalls to avoid"
        parts += [heading, *guides]
    return "\n\n".join(parts)
