"""Writes openapi.json, the source for packages/client's generated types. Makes no Azure calls."""

import json
import os
from pathlib import Path

os.environ.update(
    {
        "AZURE_ENDPOINT": "https://placeholder.openai.azure.com/",
        "AZURE_API_KEY": "unused",
        "AZURE_STORAGE_CONNECTION_STRING": "",
    }
)

import main  # noqa: E402

output = Path(__file__).with_name("openapi.json")
output.write_text(json.dumps(main.app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"Wrote {output}")
