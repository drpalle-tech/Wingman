"""API models shared by all clients (web UI, VS Code extension, CLI)."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .languages import language_for

FileRole = Literal["target", "related", "config"]
Severity = Literal["critical", "major", "minor", "info"]
FocusArea = Literal[
    "correctness",
    "security",
    "leaks",
    "performance",
    "concurrency",
    "error-handling",
    "design",
    "maintainability",
    "testing",
]


def _clean_path(path: str) -> str:
    path = path.replace("\\", "/").strip()
    while path.startswith("./"):
        path = path[2:]
    return path


class ContextFile(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str
    language: Optional[str] = Field(default=None, description="Overrides detection from the file extension")
    role: FileRole = Field(
        default="target",
        description="target: code to review/change; related: supporting code; config: manifests and tool configs",
    )

    @field_validator("path")
    @classmethod
    def _normalize_path(cls, value: str) -> str:
        return value.replace("\\", "/").strip()

    @property
    def resolved_language(self) -> str:
        return language_for(self.path, self.language)


class Selection(BaseModel):
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)

    @field_validator("path")
    @classmethod
    def _normalize_path(cls, value: str) -> str:
        return value.replace("\\", "/").strip()


class Framework(BaseModel):
    name: str
    version: Optional[str] = None


class ProjectInfo(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[Framework] = Field(default_factory=list)
    runtime: Optional[str] = None


class Diagnostic(BaseModel):
    path: str
    line: int = Field(ge=1)
    severity: Literal["error", "warning", "info", "hint"] = "warning"
    message: str = Field(max_length=2000)
    source: Optional[str] = None


class ContextBundle(BaseModel):
    files: list[ContextFile] = Field(default_factory=list, max_length=100)
    selection: Optional[Selection] = None
    project: Optional[ProjectInfo] = Field(default=None, description="Facts the client already knows; merged with detection")
    diagnostics: list[Diagnostic] = Field(default_factory=list, max_length=500)

    def total_chars(self) -> int:
        return sum(len(f.content) for f in self.files)

    def targets(self) -> list[ContextFile]:
        return [f for f in self.files if f.role == "target"]

    def file_by_path(self, path: str) -> Optional[ContextFile]:
        wanted = _clean_path(path)
        for f in self.files:
            if _clean_path(f.path) == wanted:
                return f
        for f in self.files:
            if _clean_path(f.path).lower() == wanted.lower():
                return f
        basename = wanted.rsplit("/", 1)[-1].lower()
        same_name = [f for f in self.files if f.path.rsplit("/", 1)[-1].lower() == basename]
        return same_name[0] if len(same_name) == 1 else None


class UsageInfo(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class ReviewRequest(BaseModel):
    context: ContextBundle
    focus: list[FocusArea] = Field(default_factory=list, description="Empty means all areas")
    instructions: Optional[str] = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _needs_target(self) -> "ReviewRequest":
        if not self.context.targets():
            raise ValueError("context.files must include at least one file with role 'target'")
        return self


class Finding(BaseModel):
    id: str
    severity: Severity
    category: str
    path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    anchored: bool = Field(description="True when the location was verified against the source")
    quote: str = ""
    title: str
    message: str
    suggestion: str = ""
    suggested_code: Optional[str] = None
    source: Literal["model", "secret-scan"] = "model"


class ReviewResponse(BaseModel):
    summary: str
    findings: list[Finding]
    model: str
    usage: UsageInfo


class GenerateRequest(BaseModel):
    mode: Literal["new", "complete", "refactor"]
    request: str = Field(default="", max_length=8000)
    context: ContextBundle = Field(default_factory=ContextBundle)

    @model_validator(mode="after")
    def _check_inputs(self) -> "GenerateRequest":
        if self.mode in ("new", "refactor") and not self.request.strip():
            raise ValueError(f"'request' is required in {self.mode} mode")
        if self.mode in ("complete", "refactor") and not self.context.targets():
            raise ValueError(f"{self.mode} mode needs at least one file with role 'target'")
        return self


class GeneratedFile(BaseModel):
    path: str
    language: str
    content: str


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=200_000)


class CodeChatRequest(BaseModel):
    messages: list[ChatTurn] = Field(min_length=1, max_length=60, description="Conversation so far, oldest first")
    context: ContextBundle = Field(default_factory=ContextBundle)

    @model_validator(mode="after")
    def _ends_with_question(self) -> "CodeChatRequest":
        last = self.messages[-1]
        if last.role != "user" or not last.content.strip():
            raise ValueError("the last message must be a non-empty user message")
        return self

    def total_chars(self) -> int:
        return self.context.total_chars() + sum(len(m.content) for m in self.messages)


class StreamDone(BaseModel):
    """Payload of the final `done` server-sent event from /v1/generate and /v1/chat."""

    text: str
    files: list[GeneratedFile]
    truncated: bool
    secrets_redacted: int
    model: str
    usage: UsageInfo
