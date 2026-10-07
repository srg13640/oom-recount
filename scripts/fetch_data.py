#!/usr/bin/env python3
"""Refresh data/auto.json from the three live public sources.

Sources (all original publishers):
  - Epoch AI, Epoch Capabilities Index:   https://epoch.ai/data/eci_scores.csv
  - Epoch AI, Notable AI Models dataset:  https://epoch.ai/data/notable_ai_models.csv
  - METR, Time Horizon 1.1 results:       https://metr.org/assets/benchmark_results_1_1.yaml

Each source is fetched independently. If one fails, its previous data is kept and the
failure is recorded in auto.json so the site can say so. Hand-entered figures live in
data/manual.json and are never touched here.
"""
import csv
import datetime as dt
import io
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUTO = ROOT / "data" / "auto.json"
UA = {"User-Agent": "oom-recount/1.0 (+https://github.com/srg13640/oom-recount)"}


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def today():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).date().isoformat()  # US Central (approx.)


# ---------------------------------------------------------------- Epoch ECI
def fetch_eci():
    url = "https://epoch.ai/data/eci_scores.csv"
    rows = list(csv.DictReader(io.StringIO(get(url))))
    pts = []
    for r in rows:
        v, date = fnum(r.get("eci")), (r.get("date") or "").strip()
        if v is None or not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            continue
        pts.append({"n": (r.get("Display name") or r.get("Model") or "").strip(), "date": date, "v": round(v, 2),
                    "lo": fnum(r.get("eci_ci_low")), "hi": fnum(r.get("eci_ci_high")),
                    "org": (r.get("Organization") or "").strip()})
    pts.sort(key=lambda p: (p["date"], p["v"]))
    frontier, best = [], -1e9
    for p in pts:
        if p["date"] < "2023-03-01":   # start the frontier at GPT-4
            continue
        if p["v"] > best:
            best = p["v"]
            frontier.append(p)
    ref = next((p for p in pts if p["n"].startswith("GPT-3.5 Turbo")), None)
    if not frontier:
        raise RuntimeError("no ECI rows parsed")
    return {"source": url, "updated": today(), "ok": True, "error": None,
            "n_models": len(pts), "frontier": frontier, "ref": ref}


# ------------------------------------------------------ Epoch training runs
def fetch_runs():
    url = "https://epoch.ai/data/notable_ai_models.csv"
    rows = list(csv.DictReader(io.StringIO(get(url))))
    pts = []
    for r in rows:
        f, date = fnum(r.get("Training compute (FLOP)")), (r.get("Publication date") or "").strip()
        if f is None or f < 1e25 or not re.match(r"^\d{4}-\d{2}-\d{2}$", date) or date < "2023-03-01":
            continue
        pts.append({"n": r.get("Model", "").strip(), "date": date, "flop": f,
                    "conf": (r.get("Confidence") or "").strip(), "org": (r.get("Organization") or "").strip()})
    pts.sort(key=lambda p: (p["date"], p["flop"]))
    frontier, best = [], 0.0
    for p in pts:
        if p["flop"] > best * 1.05:  # a new record must beat the old one by more than rounding noise
            best = p["flop"]
            frontier.append(p)
    if not frontier:
        raise RuntimeError("no training-compute rows parsed")
    return {"source": url, "updated": today(), "ok": True, "error": None,
            "n_models": len(pts), "frontier": frontier}


# ----------------------------------------------------------------- METR
SMALL = {"preview", "early", "codex", "max", "mini", "pro", "turbo", "sonnet", "opus", "haiku", "mythos", "gemini", "flash"}


def pretty_metr_name(key):
    k = re.sub(r"_inspect$", "", key)
    parts = k.split("_")
    out, i = [], 0
    while i < len(parts):
        p = parts[i]
        if p == "claude":
            out.append("Claude")
        elif p == "gpt":
            ver = []
            if i + 1 < len(parts) and re.fullmatch(r"\d+o", parts[i + 1]):   # gpt_4o
                i += 1
                ver.append(parts[i])
            else:
                while i + 1 < len(parts) and parts[i + 1].isdigit() and len(parts[i + 1]) < 4:
                    i += 1
                    ver.append(parts[i])
            out.append("GPT-" + ".".join(ver) if ver else "GPT")
        elif re.fullmatch(r"o\d", p):
            out.append(p)
        elif re.fullmatch(r"\d{8}", p):
            d = dt.date(int(p[:4]), int(p[4:6]), int(p[6:]))
            out.append("(" + d.strftime("%b %Y") + ")")
        elif len(p) == 4 and p.isdigit() and i + 2 < len(parts) and all(re.fullmatch(r"\d{2}", q) for q in parts[i + 1:i + 3]):
            d = dt.date(int(p), int(parts[i + 1]), int(parts[i + 2]))   # gpt_5_2025_08_07
            out.append("(" + d.strftime("%b %Y") + ")")
            i += 2
        elif p.isdigit():
            ver = [p]
            while i + 1 < len(parts) and parts[i + 1].isdigit() and len(parts[i + 1]) < 4:
                i += 1
                ver.append(parts[i])
            out.append(".".join(ver))
        else:
            out.append(p.capitalize())
        i += 1
    s = " ".join(out)
    s = re.sub(r"\b(o\d) Preview\b", r"\1-preview", s)
    s = re.sub(r"\b(o\d) Mini\b", r"\1-mini", s)
    s = s.replace("Mythos Preview Early", "Mythos Preview (early)")
    return s


def fetch_metr():
    import yaml  # PyYAML
    url = "https://metr.org/assets/benchmark_results_1_1.yaml"
    y = yaml.safe_load(get(url))
    models = []
    for key, r in (y.get("results") or {}).items():
        if r.get("benchmark_name") != "METR-Horizon-v1.1":
            continue
        rd = str(r.get("release_date") or "")
        m = r.get("metrics") or {}
        p50, p80 = m.get("p50_horizon_length") or {}, m.get("p80_horizon_length") or {}
        if not rd or p50.get("estimate") is None or rd < "2024-01-01":
            continue
        models.append({"n": pretty_metr_name(key), "key": key, "date": rd,
                       "h50": round(p50["estimate"] / 60, 3),
                       "lo": round((p50.get("ci_low") or 0) / 60, 3), "hi": round((p50.get("ci_high") or 0) / 60, 3),
                       "h80": round((p80.get("estimate") or 0) / 60, 3), "sota": bool(m.get("is_sota"))})
    models.sort(key=lambda p: (p["date"], p["h50"]))
    if not models:
        raise RuntimeError("no METR rows parsed")
    return {"source": url, "updated": today(), "ok": True, "error": None,
            "doubling_days": y.get("doubling_time_in_days") or {}, "models": models}


# ------------------------------------------------------------------ main
def main():
    prev = json.loads(AUTO.read_text()) if AUTO.exists() else {}
    out = {"fetched": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    failures = 0
    for name, fn in (("eci", fetch_eci), ("runs", fetch_runs), ("metr", fetch_metr)):
        try:
            out[name] = fn()
            n = len(out[name].get("frontier") or out[name].get("models") or [])
            print(f"[ok]   {name}: {n} points")
        except Exception as e:  # keep the last good copy, record the failure
            failures += 1
            old = dict(prev.get(name) or {})
            old.update({"ok": False, "error": f"{type(e).__name__}: {e}"[:300], "failed_at": today()})
            out[name] = old
            print(f"[FAIL] {name}: {e}", file=sys.stderr)
    AUTO.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("wrote", AUTO, "with", failures, "failure(s)")


if __name__ == "__main__":
    main()
