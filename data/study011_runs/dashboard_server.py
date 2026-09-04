#!/usr/bin/env python3
"""STUDY-011 Live Dashboard Server — serves dynamic HTML + real-time metrics API.
Runs on http://localhost:8811"""
import http.server
import json
import socketserver
import threading
import time
from pathlib import Path

BASE = Path(r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026")
RECORDS = BASE / "data" / "study011_runs" / "confirmatory" / "canonical-run-002" / "run_records.jsonl"
PORT = 8811

DOCS_DIR = str(BASE / "docs")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOCS_DIR, **kwargs)
    def do_GET(self):
        if self.path == "/api/metrics":
            data = self.compute_metrics()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        elif self.path == "/" or self.path == "/index.html":
            # Serve the dashboard HTML directly
            dash_file = BASE / "docs" / "study011-dashboard-live.html"
            if dash_file.exists():
                content = dash_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404)
        elif self.path == "/api/records":
            recs = self.load_records()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.wfile.write(json.dumps(recs[-50:]).encode())
        else:
            super().do_GET()

    def load_records(self):
        recs = []
        if RECORDS.exists():
            for line in RECORDS.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.strip():
                    try: recs.append(json.loads(line))
                    except: pass
        return recs

    def compute_metrics(self):
        recs = self.load_records()
        cells = {}
        for x in recs:
            k = f"{x.get('provider_name','?')}|{x.get('condition','?')}"
            c = cells.setdefault(k, {"att":0,"lv":0,"fail":0})
            c["att"] += 1
            if x.get("execution_class")=="LIVE_VALID": c["lv"] += 1
            else: c["fail"] += 1
        a010 = [x for x in recs if str(x.get("implementation_fingerprint","")).startswith("dfe3513c")]
        a010_cells = {}
        for x in a010:
            k = f"{x.get('provider_name','?')}|{x.get('condition','?')}"
            c = a010_cells.setdefault(k, {"att":0,"lv":0})
            c["att"] += 1
            if x.get("execution_class")=="LIVE_VALID": c["lv"] += 1
        blocks = {
            "original_confirmatory": {"fp": "b6b7c2d0…", "records": sum(1 for x in recs if str(x.get("implementation_fingerprint","")).startswith("b6b7c2d0")), "valid": sum(1 for x in recs if str(x.get("implementation_fingerprint","")).startswith("b6b7c2d0") and x.get("execution_class")=="LIVE_VALID")},
            "original_openrouter_free": {"fp": "0c588022…", "records": sum(1 for x in recs if x.get("provider_name")=="openrouter" and str(x.get("implementation_fingerprint","")).startswith("0c588022")), "valid": 0},
            "post_amendment_010": {"fp": "dfe3513c…", "records": len(a010), "valid": sum(1 for x in a010 if x.get("execution_class")=="LIVE_VALID")},
        }
        return {
            "cells": cells, "a010_cells": a010_cells, "blocks": blocks,
            "total_records": len(recs),
            "total_valid": sum(1 for x in recs if x.get("execution_class")=="LIVE_VALID"),
            "a010_records": len(a010),
            "a010_valid": sum(1 for x in a010 if x.get("execution_class")=="LIVE_VALID"),
            "runner_alive": self.check_runner(),
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def check_runner(self):
        try:
            import subprocess
            r = subprocess.run(["tasklist", "/FI", "PID eq 41968"], capture_output=True, text=True, timeout=5)
            return "python" in r.stdout.lower()
        except: return False

    def log_message(self, format, *args):
        pass  # suppress access logs

class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    with ReusableTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Dashboard server on http://localhost:{PORT}")
        httpd.serve_forever()
