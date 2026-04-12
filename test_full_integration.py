#!/usr/bin/env python3
"""DocuMind.ai full-stack integration test suite.

Exercises Group 1 (Phases 1–4), Group 2 (Phases 5–8), and end-to-end flows
against a running API (default http://localhost:8001) and PostgreSQL.

Usage:
    python test_full_integration.py
    python test_full_integration.py --group 1
    python test_full_integration.py --group 2
    python test_full_integration.py --integration
    python test_full_integration.py --no-cleanup
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import socket
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

try:
    import psycopg2
except ImportError:
    psycopg2 = None  # type: ignore

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    canvas = None
    letter = None

# ---------------------------------------------------------------------------
# Configuration (ports fixed per project instructions)
# ---------------------------------------------------------------------------

BACKEND = os.environ.get("DOCUMIND_BACKEND_URL", "http://localhost:8001")
FRONTEND = os.environ.get("DOCUMIND_FRONTEND_URL", "http://localhost:3001")
PG_HOST = os.environ.get("PGHOST", "localhost")
PG_PORT = int(os.environ.get("PGPORT", "5432"))
DATABASE_URL_SYNC = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://documind:documind@localhost:5432/documind",
)

# Module-level state shared across tests
DOC_ID_PHASE2: Optional[str] = None
CREATED_DOCUMENT_IDS: List[str] = []
CREATED_FEEDBACK_IDS: List[str] = []
STORAGE_PATHS_TO_DELETE: List[str] = []

# Phase outcomes: "PASS" | "FAIL" | "SKIP"
PHASE: Dict[str, str] = {}
ISSUES: List[str] = []

passed = failed = skipped = 0


def _count_result(tag: str) -> None:
    global passed, failed, skipped
    if tag == "PASS":
        passed += 1
    elif tag == "FAIL":
        failed += 1
    elif tag == "SKIP":
        skipped += 1


def log_issue(phase: str, msg: str) -> None:
    ISSUES.append(f"{phase}: {msg}")


def backend_reachable() -> bool:
    try:
        r = requests.get(f"{BACKEND}/health", timeout=3)
        return r.status_code == 200
    except OSError:
        return False


def pg_connect():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not installed")
    return psycopg2.connect(DATABASE_URL_SYNC)


def make_pdf_bytes(lines: List[str]) -> bytes:
    if canvas is None:
        raise RuntimeError("reportlab is not installed")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    y = height - 72
    for line in lines:
        c.drawString(72, y, line[:120])
        y -= 14
        if y < 72:
            c.showPage()
            y = height - 72
    c.save()
    return buf.getvalue()


def upload_pdf(filename: str, pdf_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
    """POST /upload; returns (document_id, error_message)."""
    try:
        r = requests.post(
            f"{BACKEND}/upload",
            files={"file": (filename, pdf_bytes, "application/pdf")},
            timeout=120,
        )
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:500]}"
        data = r.json()
        did = data.get("document_id")
        if not did:
            return None, "missing document_id in response"
        CREATED_DOCUMENT_IDS.append(did)
        return str(did), None
    except Exception as e:
        return None, str(e)


def poll_document_status(doc_id: str, timeout_s: int = 60, interval: float = 2.0) -> Tuple[Optional[str], Optional[str]]:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{BACKEND}/documents/{doc_id}", timeout=10)
            if r.status_code != 200:
                return None, f"GET /documents/{{id}} HTTP {r.status_code}"
            j = r.json()
            last = j.get("status")
            sp = j.get("storage_path")
            if sp:
                STORAGE_PATHS_TO_DELETE.append(sp)
            if last in ("completed", "needs_review"):
                return last, None
        except Exception as e:
            return None, str(e)
        time.sleep(interval)
    return last, f"timeout waiting for status; last={last!r}"


def cleanup(no_cleanup: bool) -> None:
    if no_cleanup:
        print("\n[CLEANUP] Skipped (--no-cleanup)")
        return
    print("\n[CLEANUP] Removing test data...")
    if psycopg2 is None:
        print("  psycopg2 unavailable — skipping DB cleanup")
        return
    try:
        conn = pg_connect()
        cur = conn.cursor()
        for fid in CREATED_FEEDBACK_IDS:
            cur.execute("DELETE FROM feedback WHERE id = %s::uuid", (fid,))
        for did in CREATED_DOCUMENT_IDS:
            cur.execute("DELETE FROM documents WHERE id = %s::uuid", (did,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        err = str(e).lower()
        if "connection refused" in err or "could not connect" in err:
            print("  DB cleanup skipped (PostgreSQL unreachable)")
        else:
            print(f"  DB cleanup error: {e}")

    for p in STORAGE_PATHS_TO_DELETE:
        try:
            if p and os.path.isfile(p):
                os.remove(p)
            elif p and os.path.isdir(p):
                import shutil

                shutil.rmtree(p, ignore_errors=True)
        except OSError:
            pass
    print("  Done.")


# =============================================================================
# Tests
# =============================================================================


def test1_infrastructure() -> str:
    """Phase 1 — Infrastructure."""
    global PHASE
    try:
        if psycopg2 is None:
            PHASE["1"] = "FAIL"
            log_issue("Phase 1", "psycopg2 not installed — pip install psycopg2-binary")
            print("Test 1 — Phase 1: FAIL (psycopg2 missing)")
            return "FAIL"

        # PostgreSQL port
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((PG_HOST, PG_PORT))
            s.close()
        except OSError as e:
            PHASE["1"] = "FAIL"
            log_issue("Phase 1", f"PostgreSQL not reachable on {PG_HOST}:{PG_PORT}: {e}")
            print(f"Test 1 — Phase 1: FAIL (PostgreSQL: {e})")
            return "FAIL"

        conn = pg_connect()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        tables = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()

        required = {"documents", "pages", "chunks", "extracted_fields", "feedback"}
        missing = required - tables
        if missing:
            PHASE["1"] = "FAIL"
            log_issue("Phase 1", f"Missing tables: {missing}")
            print(f"Test 1 — Phase 1: FAIL (missing tables: {missing})")
            return "FAIL"

        try:
            r = requests.get(f"{BACKEND}/health", timeout=5)
        except OSError as e:
            PHASE["1"] = "FAIL"
            log_issue("Phase 1", f"FastAPI not reachable at {BACKEND}: {e}")
            print(f"Test 1 — Phase 1: FAIL (FastAPI: {e})")
            return "FAIL"
        if r.status_code != 200:
            PHASE["1"] = "FAIL"
            log_issue("Phase 1", f"/health HTTP {r.status_code}")
            print(f"Test 1 — Phase 1: FAIL (/health status {r.status_code})")
            return "FAIL"
        try:
            body = r.json()
        except Exception:
            body = {}
        if body.get("status") != "ok":
            PHASE["1"] = "FAIL"
            log_issue("Phase 1", f"/health body unexpected: {body!r}")
            print(f"Test 1 — Phase 1: FAIL (/health body {body!r})")
            return "FAIL"

        PHASE["1"] = "PASS"
        print("Test 1 — Phase 1: PASS")
        return "PASS"
    except Exception as e:
        PHASE["1"] = "FAIL"
        log_issue("Phase 1", str(e))
        print(f"Test 1 — Phase 1: FAIL ({e})")
        return "FAIL"


def test2_ingestion() -> str:
    """Phase 2 — Ingestion."""
    global DOC_ID_PHASE2, PHASE
    if PHASE.get("1") != "PASS":
        PHASE["2"] = "SKIP"
        print("Test 2 — Phase 2: SKIP (Phase 1 did not pass)")
        return "SKIP"
    if not backend_reachable():
        PHASE["2"] = "SKIP"
        print("Test 2 — Phase 2: SKIP (backend unreachable)")
        return "SKIP"
    try:
        # Required phrase plus content so classification & field extraction succeed
        lines = [
            "This is a test contract document.",
            "The parties hereby agree to the terms of this agreement.",
            "Effective date: 01/15/2024.",
            "Additional contract language ensures sufficient length for document type detection.",
        ]
        pdf_bytes = make_pdf_bytes(lines)
        doc_id, err = upload_pdf("phase2_test.pdf", pdf_bytes)
        if err:
            PHASE["2"] = "FAIL"
            log_issue("Phase 2", err)
            print(f"Test 2 — Phase 2: FAIL ({err})")
            return "FAIL"

        DOC_ID_PHASE2 = doc_id
        st, perr = poll_document_status(doc_id)
        if perr:
            PHASE["2"] = "FAIL"
            log_issue("Phase 2", perr)
            print(f"Test 2 — Phase 2: FAIL ({perr})")
            return "FAIL"
        if st not in ("completed", "needs_review"):
            PHASE["2"] = "FAIL"
            log_issue("Phase 2", f"unexpected status {st!r}")
            print(f"Test 2 — Phase 2: FAIL (status {st!r})")
            return "FAIL"

        r = requests.get(f"{BACKEND}/documents/{doc_id}/pages", timeout=30)
        if r.status_code != 200:
            PHASE["2"] = "FAIL"
            log_issue("Phase 2", f"/pages HTTP {r.status_code}")
            print(f"Test 2 — Phase 2: FAIL (cannot load pages)")
            return "FAIL"
        pages = r.json()
        if not pages:
            PHASE["2"] = "FAIL"
            log_issue("Phase 2", "no pages returned")
            print("Test 2 — Phase 2: FAIL (no pages)")
            return "FAIL"

        has_bbox = False
        for p in pages:
            pj = p.get("page_json")
            if not pj:
                continue
            els = pj.get("elements") or []
            for el in els:
                bb = el.get("bbox")
                if isinstance(bb, dict) and all(k in bb for k in ("x0", "y0", "x1", "y1")):
                    has_bbox = True
                    break
            if has_bbox:
                break
        if not has_bbox:
            PHASE["2"] = "FAIL"
            log_issue("Phase 2", "no bounding box on page elements")
            print("Test 2 — Phase 2: FAIL (no element bbox)")
            return "FAIL"

        PHASE["2"] = "PASS"
        print("Test 2 — Phase 2: PASS")
        return "PASS"
    except Exception as e:
        PHASE["2"] = "FAIL"
        log_issue("Phase 2", str(e))
        print(f"Test 2 — Phase 2: FAIL ({e})")
        return "FAIL"


def test3_processing() -> str:
    """Phase 3 — Processing."""
    global PHASE
    if not DOC_ID_PHASE2:
        PHASE["3"] = "SKIP"
        print("Test 3 — Phase 3: SKIP (no document_id from Phase 2)")
        return "SKIP"
    if psycopg2 is None:
        PHASE["3"] = "FAIL"
        print("Test 3 — Phase 3: FAIL (psycopg2 missing)")
        return "FAIL"
    try:
        conn = pg_connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = %s::uuid",
            (DOC_ID_PHASE2,),
        )
        n_chunks = cur.fetchone()[0]
        if n_chunks < 1:
            cur.close()
            conn.close()
            PHASE["3"] = "FAIL"
            log_issue("Phase 3", "no chunks for document")
            print("Test 3 — Phase 3: FAIL (no chunks)")
            return "FAIL"

        cur.execute(
            """
            SELECT section_heading, bbox, text FROM chunks
            WHERE document_id = %s::uuid
            """,
            (DOC_ID_PHASE2,),
        )
        rows = cur.fetchall()
        has_heading = any(r[0] for r in rows)
        has_bbox = any(r[1] for r in rows)
        if not has_heading:
            cur.close()
            conn.close()
            PHASE["3"] = "FAIL"
            log_issue("Phase 3", "no section_heading on chunks")
            print("Test 3 — Phase 3: FAIL (section_heading)")
            return "FAIL"
        if not has_bbox:
            cur.close()
            conn.close()
            PHASE["3"] = "FAIL"
            log_issue("Phase 3", "no bbox on chunks")
            print("Test 3 — Phase 3: FAIL (bbox)")
            return "FAIL"

        ssn_re = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
        email_re = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        for _sh, _bb, txt in rows:
            if not txt:
                continue
            if ssn_re.search(txt) or email_re.search(txt):
                cur.close()
                conn.close()
                PHASE["3"] = "FAIL"
                log_issue("Phase 3", "chunk text contains SSN or email pattern")
                print("Test 3 — Phase 3: FAIL (PII-like pattern in chunk text)")
                return "FAIL"

        cur.execute(
            "SELECT COUNT(*) FROM extracted_fields WHERE document_id = %s::uuid",
            (DOC_ID_PHASE2,),
        )
        n_fields = cur.fetchone()[0]
        cur.close()
        conn.close()

        if n_fields < 1:
            PHASE["3"] = "FAIL"
            log_issue("Phase 3", "extracted_fields empty")
            print("Test 3 — Phase 3: FAIL (no extracted_fields)")
            return "FAIL"

        PHASE["3"] = "PASS"
        print("Test 3 — Phase 3: PASS")
        return "PASS"
    except Exception as e:
        PHASE["3"] = "FAIL"
        log_issue("Phase 3", str(e))
        print(f"Test 3 — Phase 3: FAIL ({e})")
        return "FAIL"


def test4_retrieval() -> str:
    """Phase 4 — Retrieval."""
    global PHASE
    if PHASE.get("1") != "PASS":
        PHASE["4"] = "SKIP"
        print("Test 4 — Phase 4: SKIP")
        return "SKIP"
    if not backend_reachable():
        PHASE["4"] = "SKIP"
        print("Test 4 — Phase 4: SKIP (backend unreachable)")
        return "SKIP"
    try:
        r = requests.post(
            f"{BACKEND}/retrieve",
            json={"query": "payment terms contract", "top_k": 5},
            timeout=120,
        )
        if r.status_code != 200:
            PHASE["4"] = "FAIL"
            log_issue("Phase 4", f"/retrieve HTTP {r.status_code} {r.text[:300]}")
            print(f"Test 4 — Phase 4: FAIL (HTTP {r.status_code})")
            return "FAIL"
        data = r.json()
        if not isinstance(data, list):
            PHASE["4"] = "FAIL"
            log_issue("Phase 4", "response is not a list")
            print("Test 4 — Phase 4: FAIL (not a list)")
            return "FAIL"
        if len(data) == 0:
            PHASE["4"] = "FAIL"
            log_issue("Phase 4", "empty retrieval results")
            print("Test 4 — Phase 4: FAIL (empty results)")
            return "FAIL"

        keys = {"chunk_id", "text", "score", "page_number", "source_filename", "bbox"}
        scores = []
        for item in data:
            if not isinstance(item, dict):
                PHASE["4"] = "FAIL"
                print("Test 4 — Phase 4: FAIL (item not object)")
                return "FAIL"
            if not keys.issubset(item.keys()):
                PHASE["4"] = "FAIL"
                log_issue("Phase 4", f"missing keys in item: {item.keys()}")
                print("Test 4 — Phase 4: FAIL (missing keys)")
                return "FAIL"
            scores.append(float(item["score"]))

        if scores != sorted(scores, reverse=True):
            PHASE["4"] = "FAIL"
            log_issue("Phase 4", f"scores not descending: {scores}")
            print("Test 4 — Phase 4: FAIL (score order)")
            return "FAIL"
        if scores[0] <= 0.0:
            PHASE["4"] = "FAIL"
            log_issue("Phase 4", "top score not above 0")
            print("Test 4 — Phase 4: FAIL (top score)")
            return "FAIL"

        PHASE["4"] = "PASS"
        print("Test 4 — Phase 4: PASS")
        return "PASS"
    except Exception as e:
        PHASE["4"] = "FAIL"
        log_issue("Phase 4", str(e))
        print(f"Test 4 — Phase 4: FAIL ({e})")
        return "FAIL"


def test5_agent() -> str:
    """Phase 5 — Agentic RAG."""
    global PHASE
    if not backend_reachable():
        PHASE["5"] = "SKIP"
        print("Test 5 — Phase 5: SKIP (backend unreachable)")
        return "SKIP"
    try:
        r = requests.post(
            f"{BACKEND}/query",
            json={"query": "What are the payment terms?", "top_k": 5},
            timeout=300,
        )
        if r.status_code != 200:
            PHASE["5"] = "FAIL"
            log_issue("Phase 5", f"/query HTTP {r.status_code} {r.text[:500]}")
            print(f"Test 5 — Phase 5: FAIL (HTTP {r.status_code})")
            return "FAIL"
        data = r.json()
        ans = data.get("answer")
        claims = data.get("claims")
        sources = data.get("sources")
        if not isinstance(ans, str) or not ans.strip():
            PHASE["5"] = "FAIL"
            log_issue("Phase 5", "empty answer")
            print("Test 5 — Phase 5: FAIL (answer)")
            return "FAIL"
        if not isinstance(claims, list):
            PHASE["5"] = "FAIL"
            print("Test 5 — Phase 5: FAIL (claims)")
            return "FAIL"
        if not isinstance(sources, list):
            PHASE["5"] = "FAIL"
            print("Test 5 — Phase 5: FAIL (sources)")
            return "FAIL"
        if len(claims) < 1:
            PHASE["5"] = "FAIL"
            log_issue("Phase 5", "claims list is empty")
            print("Test 5 — Phase 5: FAIL (no claims)")
            return "FAIL"

        for c in claims:
            if not isinstance(c, dict):
                continue
            if "text" not in c or "confidence" not in c or "citation" not in c:
                PHASE["5"] = "FAIL"
                log_issue("Phase 5", f"claim missing keys: {c.keys()}")
                print("Test 5 — Phase 5: FAIL (claim shape)")
                return "FAIL"
            conf = c["confidence"]
            if isinstance(conf, bool) or not isinstance(conf, (int, float)):
                PHASE["5"] = "FAIL"
                log_issue("Phase 5", f"bad confidence type: {conf!r}")
                print("Test 5 — Phase 5: FAIL (confidence type)")
                return "FAIL"
            if not (0.0 <= float(conf) <= 1.0):
                PHASE["5"] = "FAIL"
                log_issue("Phase 5", f"bad confidence: {conf!r}")
                print("Test 5 — Phase 5: FAIL (confidence range)")
                return "FAIL"

        ok_src = False
        for s in sources:
            if isinstance(s, dict) and s.get("page_number") is not None and s.get("source_filename"):
                ok_src = True
                break
        if not ok_src:
            PHASE["5"] = "FAIL"
            log_issue("Phase 5", "no valid source with page_number and source_filename")
            print("Test 5 — Phase 5: FAIL (sources)")
            return "FAIL"

        PHASE["5"] = "PASS"
        print("Test 5 — Phase 5: PASS")
        return "PASS"
    except Exception as e:
        PHASE["5"] = "FAIL"
        log_issue("Phase 5", str(e))
        print(f"Test 5 — Phase 5: FAIL ({e})")
        return "FAIL"


def test6_frontend() -> str:
    """Phase 6 — Frontend."""
    global PHASE
    try:
        r = requests.get(FRONTEND, timeout=10)
        if r.status_code != 200:
            PHASE["6"] = "FAIL"
            log_issue("Phase 6", f"HTTP {r.status_code}")
            print(f"Test 6 — Phase 6: FAIL (HTTP {r.status_code})")
            return "FAIL"
        body = r.text or ""
        if "<html" not in body.lower() and "<!doctype html" not in body.lower():
            PHASE["6"] = "FAIL"
            log_issue("Phase 6", "response does not look like HTML")
            print("Test 6 — Phase 6: FAIL (not HTML)")
            return "FAIL"
        PHASE["6"] = "PASS"
        print("Test 6 — Phase 6: PASS")
        return "PASS"
    except OSError as e:
        PHASE["6"] = "SKIP"
        print(f"Test 6 — Phase 6: SKIP ({e})")
        return "SKIP"
    except Exception as e:
        PHASE["6"] = "FAIL"
        log_issue("Phase 6", str(e))
        print(f"Test 6 — Phase 6: FAIL ({e})")
        return "FAIL"


def test7_evaluation() -> str:
    """Phase 7 — Evaluation endpoint."""
    global PHASE
    if not backend_reachable():
        PHASE["7"] = "SKIP"
        print("Test 7 — Phase 7: SKIP (backend unreachable)")
        return "SKIP"
    try:
        r = requests.get(f"{BACKEND}/evaluation/results", timeout=10)
        if r.status_code == 404:
            PHASE["7"] = "SKIP"
            print("Test 7 — Phase 7: SKIP (no /evaluation/results endpoint)")
            return "SKIP"
        if r.status_code != 200:
            PHASE["7"] = "FAIL"
            print(f"Test 7 — Phase 7: FAIL (HTTP {r.status_code})")
            return "FAIL"
        j = r.json()
        print(
            "  RAGAS / benchmark metrics:",
            json.dumps({k: j.get(k) for k in ("faithfulness", "answer_relevance", "context_precision", "context_recall") if k in j}),
        )
        PHASE["7"] = "PASS"
        print("Test 7 — Phase 7: PASS")
        return "PASS"
    except Exception as e:
        PHASE["7"] = "FAIL"
        log_issue("Phase 7", str(e))
        print(f"Test 7 — Phase 7: FAIL ({e})")
        return "FAIL"


def test8_feedback() -> str:
    """Phase 8 — Feedback."""
    global PHASE
    if not backend_reachable():
        PHASE["8"] = "SKIP"
        print("Test 8 — Phase 8: SKIP (backend unreachable)")
        return "SKIP"
    if psycopg2 is None:
        PHASE["8"] = "FAIL"
        print("Test 8 — Phase 8: FAIL (psycopg2 missing)")
        return "FAIL"
    try:
        payload = {
            "query": "test query",
            "answer": "test answer",
            "rating": 1,
            "correction": None,
            "document_ids": [],
        }
        r = requests.post(f"{BACKEND}/feedback", json=payload, timeout=15)
        if r.status_code not in (200, 201):
            PHASE["8"] = "FAIL"
            log_issue("Phase 8", f"HTTP {r.status_code} {r.text[:300]}")
            print(f"Test 8 — Phase 8: FAIL (HTTP {r.status_code})")
            return "FAIL"
        resp = r.json()
        fid = resp.get("feedback_id")
        if not fid:
            PHASE["8"] = "FAIL"
            log_issue("Phase 8", "no feedback_id")
            print("Test 8 — Phase 8: FAIL (no feedback_id)")
            return "FAIL"
        CREATED_FEEDBACK_IDS.append(fid)

        conn = pg_connect()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM feedback WHERE id = %s::uuid", (fid,))
        ok = cur.fetchone() is not None
        cur.close()
        conn.close()
        if not ok:
            PHASE["8"] = "FAIL"
            log_issue("Phase 8", "row not in database")
            print("Test 8 — Phase 8: FAIL (DB)")
            return "FAIL"

        PHASE["8"] = "PASS"
        print("Test 8 — Phase 8: PASS")
        return "PASS"
    except Exception as e:
        PHASE["8"] = "FAIL"
        log_issue("Phase 8", str(e))
        print(f"Test 8 — Phase 8: FAIL ({e})")
        return "FAIL"


def test9_e2e() -> str:
    """Test 9 — Full pipeline."""
    global PHASE
    if not backend_reachable():
        PHASE["e2e"] = "SKIP"
        print("Test 9 — FULL PIPELINE: SKIP (backend unreachable)")
        return "SKIP"

    def fail_at(step: int, msg: str) -> str:
        print(f"FULL PIPELINE: FAIL at Step {step} — {msg}")
        PHASE["e2e"] = "FAIL"
        log_issue("E2E", f"Step {step}: {msg}")
        return "FAIL"

    try:
        lines = [
            "SERVICES AGREEMENT",
            "payment is due within 30 days of invoice date",
            "This agreement is between Acme Corp and Client X",
            "Governing law: State of Colorado.",
        ]
        pdf_bytes = make_pdf_bytes(lines)
        doc_id, err = upload_pdf("e2e_contract.pdf", pdf_bytes)
        if err:
            return fail_at(2, err)

        st, perr = poll_document_status(doc_id)
        if perr or st != "completed":
            return fail_at(3, perr or f"status={st!r}")

        r = requests.post(
            f"{BACKEND}/query",
            json={"query": "when is payment due?", "top_k": 5},
            timeout=300,
        )
        if r.status_code != 200:
            return fail_at(4, f"/query HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        answer = (data.get("answer") or "").lower()
        if not any(x in answer for x in ("30", "thirty", "30 days")):
            return fail_at(5, f"answer missing payment window: {answer[:200]!r}")

        sources = data.get("sources") or []
        ok_bbox = False
        for s in sources:
            if not isinstance(s, dict):
                continue
            if s.get("page_number") is None:
                continue
            bb = s.get("bbox")
            if bb is None:
                continue
            if isinstance(bb, dict) and all(k in bb for k in ("x0", "y0", "x1", "y1")):
                ok_bbox = True
                break
        if not ok_bbox:
            return fail_at(6, "no source with page_number and bbox dict")

        fr = requests.post(
            f"{BACKEND}/feedback",
            json={
                "query": "when is payment due?",
                "answer": "payment is due within 30 days",
                "rating": 1,
                "correction": None,
                "document_ids": [],
            },
            timeout=15,
        )
        if fr.status_code not in (200, 201):
            return fail_at(7, f"feedback HTTP {fr.status_code}")
        fj = fr.json()
        nfid = fj.get("feedback_id")
        if not nfid:
            return fail_at(7, "no feedback_id")
        CREATED_FEEDBACK_IDS.append(nfid)

        conn = pg_connect()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM feedback WHERE id = %s::uuid", (nfid,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return fail_at(8, "feedback row missing")
        cur.close()
        conn.close()

        print("FULL PIPELINE: PASS")
        PHASE["e2e"] = "PASS"
        return "PASS"
    except Exception as e:
        return fail_at(0, str(e))


def test10_contract() -> str:
    """Test 10 — API contract validation for /retrieve."""
    global PHASE
    if not backend_reachable():
        PHASE["contract"] = "SKIP"
        print("Test 10 — API contract: SKIP (backend unreachable)")
        return "SKIP"
    try:
        r = requests.post(
            f"{BACKEND}/retrieve",
            json={"query": "contract payment invoice", "top_k": 5},
            timeout=120,
        )
        if r.status_code != 200:
            PHASE["contract"] = "FAIL"
            print(f"Test 10 — API contract: FAIL (HTTP {r.status_code})")
            return "FAIL"
        data = r.json()
        if not isinstance(data, list) or not data:
            PHASE["contract"] = "FAIL"
            print("Test 10 — API contract: FAIL (no results)")
            return "FAIL"

        required = (
            "chunk_id",
            "document_id",
            "text",
            "score",
            "page_number",
            "section_heading",
            "bbox",
            "source_filename",
        )
        for item in data:
            if not isinstance(item, dict):
                PHASE["contract"] = "FAIL"
                print("Test 10 — API contract: FAIL (not dict)")
                return "FAIL"
            for k in required:
                if k not in item:
                    PHASE["contract"] = "FAIL"
                    log_issue("Contract", f"missing key {k}")
                    print(f"Test 10 — API contract: FAIL (missing {k})")
                    return "FAIL"
            sc = item["score"]
            if isinstance(sc, bool) or not isinstance(sc, (int, float)):
                PHASE["contract"] = "FAIL"
                print("Test 10 — API contract: FAIL (score type)")
                return "FAIL"
            bb = item.get("bbox")
            if bb is not None:
                if not isinstance(bb, dict):
                    PHASE["contract"] = "FAIL"
                    print("Test 10 — API contract: FAIL (bbox type)")
                    return "FAIL"
                for k in ("x0", "y0", "x1", "y1"):
                    if k not in bb:
                        PHASE["contract"] = "FAIL"
                        print(f"Test 10 — API contract: FAIL (bbox.{k})")
                        return "FAIL"
            for uid_key in ("chunk_id", "document_id"):
                v = item.get(uid_key)
                if not isinstance(v, str):
                    PHASE["contract"] = "FAIL"
                    print(f"Test 10 — API contract: FAIL ({uid_key} not str)")
                    return "FAIL"

        PHASE["contract"] = "PASS"
        print("Test 10 — API contract: PASS")
        return "PASS"
    except Exception as e:
        PHASE["contract"] = "FAIL"
        log_issue("Contract", str(e))
        print(f"Test 10 — API contract: FAIL ({e})")
        return "FAIL"


def print_summary(mode: str) -> None:
    """Print final summary block."""
    def g(ph: str, default: str = "SKIP") -> str:
        return PHASE.get(ph, default)

    print()
    print("=======================================================")
    print("DOCUMIND.AI FULL INTEGRATION TEST RESULTS")
    print("=======================================================")
    print("GROUP 1 — Data Processing and Retrieval (Karthik)")
    print(f"  [{g('1')}] Phase 1 — Infrastructure and setup")
    print(f"  [{g('2')}] Phase 2 — Document ingestion pipeline")
    print(f"  [{g('3')}] Phase 3 — Chunking and processing")
    print(f"  [{g('4')}] Phase 4 — Embedding and retrieval")
    print()
    print("GROUP 2 — Agent, Frontend, Evaluation (Glen)")
    print(f"  [{g('5')}] Phase 5 — Agentic RAG pipeline")
    print(f"  [{g('6')}] Phase 6 — Frontend application")
    print(f"  [{g('7')}] Phase 7 — Evaluation")
    print(f"  [{g('8')}] Phase 8 — Feedback mechanism")
    print()
    print("INTEGRATION")
    print(f"  [{g('e2e')}] End-to-end pipeline walkthrough")
    print(f"  [{g('contract')}] API contract validation")
    print()
    print("=======================================================")
    global passed, failed, skipped
    print(f"RESULT: {passed} passed, {failed} failed, {skipped} skipped")
    print("=======================================================")
    if ISSUES:
        print()
        print("ISSUES TO FIX BEFORE DEMO:")
        for line in ISSUES:
            print(f"  - {line}")


def main() -> None:
    global passed, failed, skipped
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", type=int, choices=(1, 2), default=None)
    parser.add_argument("--integration", action="store_true")
    parser.add_argument("--no-cleanup", action="store_true")
    args = parser.parse_args()

    # Load .env from project root if present
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    except ImportError:
        pass

    mode = "all"
    if args.group == 1:
        mode = "g1"
    elif args.group == 2:
        mode = "g2"
    elif args.integration:
        mode = "int"

    tests_to_run: List[Tuple[str, Callable[[], str]]] = []
    if mode == "all":
        tests_to_run = [
            ("1", test1_infrastructure),
            ("2", test2_ingestion),
            ("3", test3_processing),
            ("4", test4_retrieval),
            ("5", test5_agent),
            ("6", test6_frontend),
            ("7", test7_evaluation),
            ("8", test8_feedback),
            ("e2e", test9_e2e),
            ("contract", test10_contract),
        ]
    elif mode == "g1":
        tests_to_run = [
            ("1", test1_infrastructure),
            ("2", test2_ingestion),
            ("3", test3_processing),
            ("4", test4_retrieval),
        ]
    elif mode == "g2":
        tests_to_run = [
            ("5", test5_agent),
            ("6", test6_frontend),
            ("7", test7_evaluation),
            ("8", test8_feedback),
        ]
    elif mode == "int":
        tests_to_run = [
            ("e2e", test9_e2e),
            ("contract", test10_contract),
        ]

    print("DocuMind.ai — test_full_integration.py")
    print(f"  Backend:  {BACKEND}")
    print(f"  Frontend: {FRONTEND}")
    print()

    passed = failed = skipped = 0
    for name, fn in tests_to_run:
        tag = fn()
        _count_result(tag)

    # Default SKIP for phases not run
    if mode == "g1":
        for k in ("5", "6", "7", "8"):
            PHASE[k] = PHASE.get(k, "SKIP")
        PHASE["e2e"] = "SKIP"
        PHASE["contract"] = "SKIP"
    elif mode == "g2":
        for k in ("1", "2", "3", "4"):
            PHASE[k] = PHASE.get(k, "SKIP")
        PHASE["e2e"] = "SKIP"
        PHASE["contract"] = "SKIP"
    elif mode == "int":
        for k in ("1", "2", "3", "4", "5", "6", "7", "8"):
            PHASE[k] = "SKIP"

    print_summary(mode)
    cleanup(args.no_cleanup)

    if failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
