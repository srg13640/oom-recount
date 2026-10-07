#!/usr/bin/env python3
"""Build the site: inject data/manual.json + data/auto.json and the icons into the
page template, and write a self-contained dist/ ready for GitHub Pages."""
import datetime as dt
import json
import os
import pathlib
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE, DATA, DIST = ROOT / "site", ROOT / "data", ROOT / "dist"


def main():
    manual = json.loads((DATA / "manual.json").read_text(encoding="utf-8"))
    auto = json.loads((DATA / "auto.json").read_text(encoding="utf-8"))
    built = os.environ.get("BUILD_DATE") or dt.datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%dT%H:%M:%S%z")  # dated in US Central time
    repo = os.environ.get("GITHUB_REPOSITORY", "srg13640/oom-recount")
    owner, name = repo.split("/")
    meta = {"built": built, "repo": repo, "workflow": "update.yml", "url": f"https://{owner}.github.io/{name}/"}
    data = {"meta": meta, "manual": manual, "auto": auto}

    tpl = (SITE / "index.template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = tpl.replace("/*{{DATA}}*/null", payload)
    for s in (180, 192, 512):
        html = html.replace("{{ICON%d}}" % s, (SITE / "icons" / f"icon{s}.b64").read_text().strip())
    assert "{{" not in html, "unfilled placeholder in template"

    DIST.mkdir(exist_ok=True)
    (DIST / "index.html").write_text(html, encoding="utf-8")
    stamp = built.replace("-", "").replace(":", "")
    (DIST / "sw.js").write_text((SITE / "sw.js").read_text(encoding="utf-8").replace("{{CACHE}}", f"oom-recount-{stamp}"))
    (DIST / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (DIST / ".nojekyll").write_text("")
    print(f"built dist/index.html ({len(html.encode()):,} bytes), cache oom-recount-{stamp}")


if __name__ == "__main__":
    main()
