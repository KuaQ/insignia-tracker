import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "dashboard" / "data.js"

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def load_events(path):
    events=[]
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            pass
    return events

def normalize_listings(raw):
    out=[]
    if isinstance(raw, dict):
        for key, value in raw.items():
            if not isinstance(value, dict):
                continue
            row={"key":key, **value}
            out.append(row)
    elif isinstance(raw, list):
        out=raw
    return out

def main():
    listings=normalize_listings(load(DATA/"listings.json", {}))
    events=load_events(DATA/"events.jsonl")
    last=load(DATA/"last_run.json", {})
    bootstrap=load(DATA/"bootstrap_history_2026-10-06.json", {})
    payload={
        "meta":{
            "generated_at":datetime.now(timezone.utc).isoformat(),
            "note":"Dane wygenerowane automatycznie z repozytorium trackera.",
            "last_run":last,
            "bootstrap_snapshot":bootstrap.get("latest_market_snapshot")
        },
        "listings":listings,
        "events":events
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "window.INSIGNIA_DATA = "+json.dumps(payload,ensure_ascii=False,indent=2)+";\n",
        encoding="utf-8"
    )
    print(f"Dashboard: {len(listings)} ofert, {len(events)} zdarzeń -> {OUT}")

if __name__=="__main__":
    main()
