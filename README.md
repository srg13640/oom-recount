# Recounting the OOMs

Leopold Aschenbrenner's June 2024 essay *Situational Awareness* projected AI compute, spending, power, and capability through 2030. This site checks those projections against what has actually been observed, redrawn in the essay's own chart style, with an explicit measure of intelligence (Epoch AI's capability index, GPQA, and his effective-compute ladder).

Live site: https://srg13640.github.io/oom-recount/

It is a self-contained, offline-capable web app (installable on iPhone from Safari: Share → Add to Home Screen).

## How it is put together

| Part | What it does |
| --- | --- |
| `site/index.template.html` | The whole app: page, charts, sliders, owner tools. Data is injected at build time. |
| `site/sw.js` | Service worker so the installed app opens offline. |
| `data/manual.json` | Hand-entered figures (capex, revenue, power, site sizes, GPQA scores), the scorecard text, and the source list. Edit this on GitHub when a figure changes. |
| `data/auto.json` | Machine-fetched series: Epoch AI's Capabilities Index, Epoch AI's training-compute estimates, METR's time horizons. Refreshed by the update workflow. |
| `scripts/fetch_data.py` | Pulls the three live series from the publishers' own files and rewrites `auto.json`, keeping the old copy of any series that fails. |
| `scripts/build.py` | Merges the two data files and the icons into the template and writes `dist/`. |
| `.github/workflows/deploy.yml` | On every push to `main`: build and publish to GitHub Pages. |
| `.github/workflows/update.yml` | The "Update the site now" button: fetch → commit → build → publish. |

## Updating the site

**From the app.** Open the live site, go to Sources → Owner tools, and press **Update the site now**. Without a token the button opens the workflow page on GitHub, where you tap *Run workflow*. With a token saved on your device the button starts the run itself and tells you when it is done.

To make the token: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate. Repository access: only `oom-recount`. Permissions: **Actions: Read and write**. Paste it into the Owner tools page on the device you use; it is stored only in that browser.

**Changing a hand-entered figure.** Edit `data/manual.json` on GitHub (the Owner tools page links straight to it), commit to `main`, and the deploy workflow republishes in two to three minutes. Dates are `YYYY-MM` (mid-month), `YYYY-MM-DD`, or a decimal year such as `2024.5`.

**From a Mac.**

```sh
pip install pyyaml
python3 scripts/fetch_data.py   # refresh data/auto.json
python3 scripts/build.py        # write dist/
python3 -m http.server --directory dist 8000   # preview at http://localhost:8000
```

## Data and credit

- Projections: Aschenbrenner, *Situational Awareness: The Decade Ahead* (June 2024). Charts are redrawn after the essay's figures; its text is not reproduced.
- Epoch AI data (Capabilities Index, Notable AI Models) is CC BY 4.0: Epoch AI, https://epoch.ai.
- METR time-horizon results: https://metr.org/time-horizons/.
- Everything else is cited in the app's Sources tab, with the source number shown next to each figure.

Nothing in the public site contacts the network. The owner tools call api.github.com only when the owner uses them.
