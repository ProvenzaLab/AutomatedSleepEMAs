#!/usr/bin/env python3
"""sleep_ema_demo.py – Minimal reproducible demo for the Automated Sleep‑Deviation
Triggered EMA pipeline described in the IEEE NER paper.

Add‑on (June 2025): If no real Oura token is supplied (or the token equals the
placeholder "xxx"), the script falls back to the bundled
`example_oura_sleep.json` so reviewers can run the demo entirely offline.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics as stats
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

import requests

################################################################################
# --------------------------- Config helpers ----------------------------------#
################################################################################

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "config.json"
SAMPLE_JSON = ROOT / "example_oura_sleep.json"
DUMMY = "xxx"  # placeholder string that means "not set"


def load_config(path: Path = CONFIG_FILE) -> Dict[str, Any]:
    """Load JSON config; return minimal skeleton if missing so demo still runs."""
    if not path.exists():
        print(f"[INFO] No config.json found → running sample mode.")
        return {"oura_api_tokens": {"sample": DUMMY}, "qualtrics": {"api_token": DUMMY}}
    with path.open() as f:
        return json.load(f)

################################################################################
# ----------------------------- Oura ingest -----------------------------------#
################################################################################

OURA_SLEEP_URL = "https://api.ouraring.com/v2/usercollection/sleep"


def fetch_sleep_json(token: str | None, days: int = 8) -> List[dict]:
    """Return raw Oura sleep records.

    • If *token* is None, empty, or a placeholder starting with "xxx", the
      function loads the local `example_oura_sleep.json` file instead of
      calling the Oura Cloud API so the demo can run offline.
    """
    if not token or token.startswith(DUMMY):
        print("[INFO] Using bundled sample Oura data (offline mode).")
        with SAMPLE_JSON.open() as fh:          # ← safer than read_text + loads
            return json.load(fh)['data']                # returns list[dict]

    end = date.today()
    start = end - timedelta(days=days)
    r = requests.get(
        OURA_SLEEP_URL,
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": start.isoformat(), "end_date": end.isoformat()},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json().get("data", [])
    return sorted(data, key=lambda d: d["day"])  # oldest → newest


def nightly_totals(records: List[dict]) -> List[float]:
    """Return nightly total sleep (h)"""
    clean = [
        rec for rec in records
        if isinstance(rec, dict)
        and rec.get("type") == "long_sleep"
        and "total_sleep_duration" in rec
    ]
    return [rec["total_sleep_duration"] / 3600 for rec in clean][-8:]

################################################################################
# ---------------------------- Trigger logic ----------------------------------#
################################################################################


def should_trigger(hours: List[float], deviation_pct: float = 25.0, min_hours: float = 4.0) -> bool:
    if len(hours) < 8:
        raise ValueError("Need at least 8 nights for deviation rule.")
    last, baseline = hours[-1], stats.mean(hours[:-1])
    pct_change = abs(last - baseline) / baseline * 100 if baseline else 0
    return last < min_hours or pct_change > deviation_pct and pct_change

################################################################################
# ----------------------------- Qualtrics -------------------------------------#
################################################################################

QUALTRICS_DIST_URL = "https://iad1.qualtrics.com/API/v3/distributions"
QUALTRICS_SMS_URL = f"{QUALTRICS_DIST_URL}/sms"


def send_qualtrics_survey(cfg: dict, patient_id: str, dry: bool = True) -> None:
    qt = cfg.get("qualtrics", {})
    api_token = qt.get("api_token", DUMMY)
    if api_token.startswith(DUMMY):
        dry = True  # force dry‑run if token is dummy

    payload_email = {
        "message": {
            "messageText": "Please fill out this survey: ${l://SurveyURL}",
        },
        "recipients": {
            "mailingListId": qt.get("mailinglist_id", ""),
            "contactId": qt.get(patient_id, ""),
        },
        "header": {
            "fromEmail": "xxx@bcm.edu",
            "replyToEmail": "xxx@bcm.edu",
            "fromName": "Research Team",
            "subject": f"Survey – {datetime.now(timezone.utc):%Y-%m-%d %H:%M}",
        },
        "surveyLink": {"surveyId": qt.get("survey_id", ""), "type": "Individual"},
        "sendDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    hdrs = {"Content-Type": "application/json", "X-API-TOKEN": api_token}

    if dry:
        print("[DRY-RUN] Would POST email invite →", QUALTRICS_DIST_URL)
    else:
        print("[INFO] Sending email…")
        requests.post(QUALTRICS_DIST_URL, headers=hdrs, json=payload_email, timeout=30)

    # SMS payload (same fields)
    payload_sms = {
        "message": {
            "messageText": "Please fill out this survey: ${l://SurveyURL}",
        },
        "recipients": {
            "mailingListId": qt.get("mailinglist_id", ""),
            "contactId": qt.get(patient_id, ""),
        },
        "surveyId": qt.get("survey_id", ""),
        "sendDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "Invite",
        "name": "SMS API Trigger",
    }

    if dry:
        print("[DRY-RUN] Would POST SMS invite →", QUALTRICS_SMS_URL)
    else:
        print("[INFO] Sending SMS…")
        requests.post(QUALTRICS_SMS_URL, headers=hdrs, json=payload_sms, timeout=30)

################################################################################
# ---------------------------- Main pipeline ----------------------------------#
################################################################################


def run_once(config_path: Path, dry_flag: bool, deviation: float, min_hours: float):
    cfg = load_config(config_path)
    tokens = cfg.get("oura_api_tokens", {}) or {"sample": DUMMY}

    for patient_id, token in tokens.items():
        print(f"\n>>> Processing {patient_id}")
        recs = fetch_sleep_json(token, days=8)
        hours = nightly_totals(recs)
        print("Last night sleep (h):", round(hours[-1], 2))
        print("Seven previous nights sleep (h):", [round(h, 2) for h in hours[:-1]])
        last, baseline = hours[-1], stats.mean(hours[:-1])
        pct_change = abs(last - baseline) / baseline * 100 if baseline else 0
        print("Percent Change from Previous 7 Days: ", round(pct_change,2), "%")

        if should_trigger(hours, deviation, min_hours):
            print("Trigger condition met → survey step …")
            send_qualtrics_survey(cfg, patient_id, dry=dry_flag)
        else:
            print("No trigger for this patient.")

################################################################################
# ------------------------------ CLI ------------------------------------------#
################################################################################


def main():
    ap = argparse.ArgumentParser(description="Run one sleep‑deviation EMA check.")
    ap.add_argument("--config", type=Path, default=CONFIG_FILE,
                    help="Path to config.json (default: ./config.json)")
    ap.add_argument("--dry", action="store_true",
                    help="Print instead of hitting external APIs")
    ap.add_argument("--deviation", type=float, default=25.0,
                    help="Percent deviation threshold (default 25)")
    ap.add_argument("--min-hours", type=float, default=4.0,
                    help="Minimum total sleep in hours (default 4)")
    args = ap.parse_args()

    run_once(args.config, dry_flag=args.dry, deviation=args.deviation, min_hours=args.min_hours)


if __name__ == "__main__":
    main()
