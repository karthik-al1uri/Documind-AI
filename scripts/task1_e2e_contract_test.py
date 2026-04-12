#!/usr/bin/env python3
"""Task 1 — Generate a 3-page contract PDF, upload, poll, retrieve, query.

Usage:
  export API_BASE=http://localhost:8002   # optional
  python scripts/task1_e2e_contract_test.py
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from urllib import error, request

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    print("Install reportlab: pip install reportlab", file=sys.stderr)
    sys.exit(1)


API_BASE = os.environ.get("API_BASE", "http://localhost:8002").rstrip("/")


def build_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, h - 72, "MASTER SERVICES AGREEMENT")
    c.setFont("Helvetica", 10)
    y = h - 110
    lines = [
        'This Master Services Agreement (the "Agreement") is entered into as of January 15, 2026,',
        'by and between Acme Corporation ("Provider") and Beta Industries LLC ("Client").',
        "",
        "1. PAYMENT TERMS",
        "Client shall pay all undisputed invoices within thirty (30) days of the invoice date.",
        "Late payments accrue interest at one and one-half percent (1.5%) per month.",
        "All fees are in United States Dollars (USD). A minimum commitment of fifty thousand",
        "dollars ($50,000) applies for the initial twelve (12) month term.",
        "",
        "2. EFFECTIVE DATE AND TERM",
        "This Agreement is effective as of February 1, 2026, and continues for twenty-four (24) months",
        "unless terminated earlier in accordance with Section 8.",
    ]
    for line in lines:
        c.drawString(72, y, line)
        y -= 14

    c.showPage()
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, h - 72, "3. CONFIDENTIALITY")
    c.setFont("Helvetica", 10)
    y = h - 100
    for line in [
        "Each party agrees to protect the other party confidential information using reasonable care.",
        "The confidentiality obligations survive termination for five (5) years.",
        "",
        "4. LIMITATION OF LIABILITY",
        "Except for breaches of confidentiality or indemnity obligations, neither party liability",
        "shall exceed the fees paid in the twelve (12) months preceding the claim.",
    ]:
        c.drawString(72, y, line)
        y -= 14

    c.showPage()
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, h - 72, "5. NOTICES AND GOVERNING LAW")
    c.setFont("Helvetica", 10)
    y = h - 100
    for line in [
        "Notices to Provider: legal-notices@acme.example.com",
        "Notices to Client: contracts@beta.example.com",
        "This Agreement is governed by the laws of the State of Delaware.",
        "Signed: Acme Corporation   Signed: Beta Industries LLC",
    ]:
        c.drawString(72, y, line)
        y -= 14

    c.save()
    return buf.getvalue()


def http_json(method: str, url: str, data: bytes | None = None, headers: dict | None = None):
    req = request.Request(url, data=data, method=method, headers=headers or {})
    with request.urlopen(req, timeout=600) as resp:
        body = resp.read().decode()
        return resp.status, json.loads(body) if body else None


def multipart_body(filename: str, file_bytes: bytes, field_name: str = "file") -> tuple[bytes, str]:
    boundary = "----documindTask1Boundary"
    crlf = b"\r\n"
    parts: list[bytes] = [
        f"--{boundary}".encode(),
        crlf,
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"'
        ).encode(),
        crlf,
        b"Content-Type: application/pdf",
        crlf,
        crlf,
        file_bytes,
        crlf,
        f"--{boundary}--".encode(),
        crlf,
    ]
    return b"".join(parts), boundary


def main() -> None:
    pdf = build_pdf()
    body, boundary = multipart_body("task1_contract.pdf", pdf)

    print("=== UPLOAD ===")
    try:
        status, upload = http_json(
            "POST",
            f"{API_BASE}/upload",
            body,
            {"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
    except error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        raise
    print(json.dumps(upload, indent=2))
    doc_id = upload["document_id"]

    print("\n=== POLL ===")
    for i in range(60):
        _, doc = http_json("GET", f"{API_BASE}/documents/{doc_id}")
        st = doc.get("status")
        print(f"  [{i + 1}] status={st}")
        if st in ("completed", "needs_review", "error"):
            break
        time.sleep(2)
    else:
        raise SystemExit("timeout waiting for document")

    payload = json.dumps(
        {"query": "payment terms", "top_k": 5, "document_ids": [doc_id]}
    ).encode()

    print("\n=== RETRIEVE ===")
    _, ret = http_json(
        "POST",
        f"{API_BASE}/retrieve",
        payload,
        {"Content-Type": "application/json"},
    )
    print(json.dumps(ret, indent=2))

    print("\n=== QUERY ===")
    _, ans = http_json(
        "POST",
        f"{API_BASE}/query",
        payload,
        {"Content-Type": "application/json"},
    )
    print(json.dumps(ans, indent=2))


if __name__ == "__main__":
    main()
