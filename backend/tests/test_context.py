from assist.context import detect_project, number_lines, render_bundle, selected_text
from assist.schemas import ContextBundle, ContextFile, Selection

PACKAGE_JSON = '{"dependencies": {"react": "^18.2.0", "lodash": "4.0.0"}, "devDependencies": {"typescript": "~5.2.2"}}'
CSPROJ = """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>
  <ItemGroup><PackageReference Include="Microsoft.Data.SqlClient" Version="5.2.0" /></ItemGroup>
</Project>"""


def frameworks(info) -> dict:
    return {fw.name: fw.version for fw in info.frameworks}


def test_number_lines_pads_to_widest_number():
    text = "\n".join(f"x{i}" for i in range(1, 11))
    lines = number_lines(text).splitlines()
    assert lines[0] == " 1 | x1"
    assert lines[9] == "10 | x10"


def test_language_from_extension_or_declared():
    assert ContextFile(path="src/App.tsx", content="").resolved_language == "typescript"
    assert ContextFile(path="Svc.cs", content="").resolved_language == "csharp"
    assert ContextFile(path="notes.unknown", content="").resolved_language == "text"
    assert ContextFile(path="snippet.txt", content="", language="Python").resolved_language == "python"


def test_detects_frameworks_from_manifests():
    files = [
        ContextFile(path="web/package.json", content=PACKAGE_JSON, role="config"),
        ContextFile(path="api/Api.csproj", content=CSPROJ, role="config"),
        ContextFile(path="requirements.txt", content="fastapi==0.104.1\nsomething-else==1.0\n", role="config"),
        ContextFile(path="web/src/App.tsx", content="export const App = () => null"),
    ]
    info = detect_project(files, None)
    assert frameworks(info) == {
        "react": "18.2.0",
        "typescript": "5.2.2",
        "ASP.NET Core": None,
        "Microsoft.Data.SqlClient": "5.2.0",
        "fastapi": "0.104.1",
    }
    assert info.runtime == ".NET net8.0"
    assert info.languages == ["typescript"]


def test_detects_react_from_code_without_manifest():
    files = [ContextFile(path="hooks.ts", content="import { useState } from 'react'\n")]
    assert "react" in frameworks(detect_project(files, None))


def test_pyproject_python_version():
    toml = '[project]\nrequires-python = ">=3.11"\ndependencies = ["django>=5.0"]\n'
    info = detect_project([ContextFile(path="pyproject.toml", content=toml, role="config")], None)
    assert info.runtime == "Python >=3.11"
    assert frameworks(info) == {"django": "5.0"}


def test_file_lookup_normalizes_paths():
    bundle = ContextBundle(
        files=[ContextFile(path="src\\app\\cart.py", content=""), ContextFile(path="src/util.py", content="")]
    )
    assert bundle.file_by_path("src/app/cart.py").path == "src/app/cart.py"
    assert bundle.file_by_path("./src/app/cart.py").path == "src/app/cart.py"
    assert bundle.file_by_path("SRC/APP/CART.PY").path == "src/app/cart.py"
    assert bundle.file_by_path("cart.py").path == "src/app/cart.py"
    assert bundle.file_by_path("missing.py") is None


def test_render_numbers_only_targets_and_lists_diagnostics():
    bundle = ContextBundle(
        files=[
            ContextFile(path="a.py", content="x = 1", role="target"),
            ContextFile(path="b.py", content="y = 2", role="related"),
        ],
        diagnostics=[{"path": "a.py", "line": 1, "severity": "error", "message": "boom", "source": "pyright"}],
    )
    text = render_bundle(bundle, detect_project(bundle.files, None), number_targets=True)
    assert "1 | x = 1" in text
    assert "\ny = 2\n" in text
    assert "- a.py:1 [error] pyright: boom" in text


def test_selected_text():
    bundle = ContextBundle(
        files=[ContextFile(path="a.py", content="l1\nl2\nl3\nl4")],
        selection=Selection(path="a.py", start_line=2, end_line=3),
    )
    assert selected_text(bundle) == "l2\nl3"
