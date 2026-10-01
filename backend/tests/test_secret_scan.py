from assist.schemas import ContextBundle, ContextFile
from assist.secret_scan import find_secrets, redact, redact_bundle

AWS_KEY = "AKIAIOSFODNN7EXAMPLE"  # AWS's documented example key ID
STORAGE = "DefaultEndpointsProtocol=https;AccountName=demo;AccountKey=" + "a1B2c3D4" * 11 + "==;EndpointSuffix=core.windows.net"
LLM_KEY = "sk-proj-" + "Zx9Qw3Er7Ty1Ui5Op2As"
GITHUB = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


def rule_ids(text: str) -> list[str]:
    return [m.rule.id for m in find_secrets(text)]


def test_detects_known_secret_formats():
    text = f'aws = "{AWS_KEY}"\nconn = "{STORAGE}"\nkey = "{LLM_KEY}"\ngh = "{GITHUB}"\n'
    assert rule_ids(text) == ["aws-access-key", "azure-storage-key", "api-key", "github-token"]


def test_ignores_placeholders_and_runtime_lookups():
    text = "\n".join(
        [
            'api_key = "your-api-key-here"',
            'password = os.environ["DB_PASSWORD"]',
            'token = "${TOKEN}"',
            'conn = "Server=db;User Id=app;Password=<password>;"',
            "const secret = process.env.CLIENT_SECRET",
        ]
    )
    assert rule_ids(text) == []


def test_generic_credential_needs_randomness():
    assert rule_ids('password = "aaaaaaaaaa"') == []
    assert rule_ids('db_password = "Tr0ub4dor&3xK9"') == ["hardcoded-credential"]


def test_connection_string_password():
    assert rule_ids('var cs = "Server=.;Database=shop;User Id=sa;Password=P@ssw0rd123;";') == ["connection-string-password"]


def test_overlapping_rules_report_once():
    assert rule_ids(f'API_KEY = "{LLM_KEY}"') == ["api-key"]


def test_redaction_keeps_line_numbers():
    text = "line1\n-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nIBAAKC\n-----END RSA PRIVATE KEY-----\nline6\n"
    redacted = redact(text, find_secrets(text))
    assert "MIIEow" not in redacted
    assert "[REDACTED:private-key]" in redacted
    assert redacted.count("\n") == text.count("\n")
    assert redacted.splitlines()[5] == "line6"


def test_redact_bundle_reports_line_and_masks_value():
    content = f'import os\n\nAWS_KEY = "{AWS_KEY}"\n'
    bundle = ContextBundle(files=[ContextFile(path="app/config.py", content=content)])
    redacted, hits = redact_bundle(bundle)
    assert len(hits) == 1
    assert hits[0].line == 3
    assert hits[0].path == "app/config.py"
    assert AWS_KEY not in hits[0].masked_line
    assert hits[0].masked_line.startswith('AWS_KEY = "AKIA')
    assert AWS_KEY not in redacted.files[0].content
    assert bundle.files[0].content == content
