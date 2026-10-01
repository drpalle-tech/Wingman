"""Scores the /v1/review endpoint against samples with seeded bugs.

Run against a running backend:
    python evals/run.py --url http://127.0.0.1:8000 [--only py-] [--workers 4]

A seeded issue counts as found when a finding lands within a couple of lines of it and either its
category or its text matches. Clean samples should produce no critical or major findings.
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).parent
SAMPLES = ROOT / "samples"
LINE_TOLERANCE = 2
SERIOUS = {"critical", "major"}


def read(path: str) -> str:
    return (SAMPLES / path).read_text(encoding="utf-8")


def expected_lines(content: str, patterns: list[str]) -> set[int]:
    lines = {n for n, line in enumerate(content.splitlines(), 1) for p in patterns if p in line}
    if not lines:
        raise ValueError(f"Case is out of date: none of {patterns} appear in the sample")
    return lines


def matches(finding: dict, expectation: dict, lines: set[int], path: str) -> bool:
    start = finding.get("start_line")
    if finding["path"] != path or start is None:
        return False
    end = finding.get("end_line") or start
    if not any(start - LINE_TOLERANCE <= line <= end + LINE_TOLERANCE for line in lines):
        return False
    text = " ".join(finding.get(k) or "" for k in ("title", "message", "suggestion", "quote")).lower()
    return finding["category"] in expectation["categories"] or any(k in text for k in expectation["keywords"])


def run_case(client: httpx.Client, case: dict) -> dict:
    files = [{"path": p, "content": read(p), "role": "target"} for p in case["files"]]
    files += [{"path": p, "content": read(p), "role": "config"} for p in case.get("config", [])]
    started = time.perf_counter()
    response = client.post("/v1/review", json={"context": {"files": files}})
    elapsed = time.perf_counter() - started
    base = {"id": case["id"], "language": case["language"], "clean": case.get("clean", False), "elapsed": elapsed}
    if response.status_code != 200:
        return {**base, "error": f"HTTP {response.status_code}: {response.text[:300]}"}

    body = response.json()
    findings = body["findings"]
    target = case["files"][0]
    content = read(target)
    results = []
    for expectation in case["expect"]:
        patterns = expectation["match"] if isinstance(expectation["match"], list) else [expectation["match"]]
        lines = expected_lines(content, patterns)
        hit = next((f for f in findings if matches(f, expectation, lines, target)), None)
        results.append({"match": patterns[0], "lines": sorted(lines), "finding": hit["id"] if hit else None})

    matched = {r["finding"] for r in results if r["finding"]}
    extra = [
        {"id": f["id"], "severity": f["severity"], "category": f["category"], "line": f["start_line"], "title": f["title"]}
        for f in findings
        if f["id"] not in matched and f["severity"] in SERIOUS
    ]
    return {
        **base,
        "expected": len(results),
        "found": sum(1 for r in results if r["finding"]),
        "results": results,
        "extra_serious": extra,
        "findings": len(findings),
        "anchored": sum(1 for f in findings if f["anchored"]),
        "usage": body["usage"],
        "summary": body["summary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--only", default="", help="Run only cases whose id starts with this prefix")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    cases = [c for c in json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))["cases"] if c["id"].startswith(args.only)]
    with httpx.Client(base_url=args.url, timeout=300) as client:
        model = client.get("/health").json().get("model", "unknown")
        print(f"Running {len(cases)} cases against {args.url} (model: {model})\n")
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(lambda c: run_case(client, c), cases))
        total_time = time.perf_counter() - started

    print(f"{'case':<26}{'found':>7}{'extra':>7}{'time':>8}{'tokens':>9}{'cost':>10}")
    for r in results:
        if "error" in r:
            print(f"{r['id']:<26}  ERROR {r['error']}")
            continue
        found = "clean" if r["clean"] else f"{r['found']}/{r['expected']}"
        print(
            f"{r['id']:<26}{found:>7}{len(r['extra_serious']):>7}{r['elapsed']:>7.1f}s"
            f"{r['usage']['total_tokens']:>9,}{r['usage']['cost_usd']:>10.4f}"
        )

    ok = [r for r in results if "error" not in r]
    buggy = [r for r in ok if not r["clean"]]
    found = sum(r["found"] for r in buggy)
    expected = sum(r["expected"] for r in buggy)
    by_language = {}
    for r in buggy:
        f, e = by_language.get(r["language"], (0, 0))
        by_language[r["language"]] = (f + r["found"], e + r["expected"])
    noise = sum(len(r["extra_serious"]) for r in ok if r["clean"])
    unmatched = sum(len(r["extra_serious"]) for r in buggy)
    all_findings = sum(r["findings"] for r in ok)
    anchored = sum(r["anchored"] for r in ok)

    print()
    if expected:
        per_language = ", ".join(f"{lang} {f}/{e}" for lang, (f, e) in sorted(by_language.items()))
        print(f"Recall: {found}/{expected} ({found / expected:.0%}) | {per_language}")
    print(f"Critical/major findings on clean samples: {noise}")
    print(f"Unmatched critical/major findings on buggy samples: {unmatched} (inspect; some may be valid extra issues)")
    if all_findings:
        print(f"Findings anchored to verified lines: {anchored}/{all_findings} ({anchored / all_findings:.0%})")
    tokens = sum(r["usage"]["total_tokens"] for r in ok)
    cost = sum(r["usage"]["cost_usd"] for r in ok)
    print(f"Total: {total_time:.0f}s wall time, {tokens:,} tokens, ${cost:.4f}")
    errors = [r for r in results if "error" in r]
    if errors:
        print(f"Errors: {len(errors)} case(s) failed")

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{model}.json"
    out_file.write_text(json.dumps({"model": model, "url": args.url, "results": results}, indent=2), encoding="utf-8")
    print(f"Details: {out_file}")


if __name__ == "__main__":
    main()
