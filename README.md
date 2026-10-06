# Sec1-Slides

PDF Slides for COMS 4181.

## Automatic lecture PDF export

This repository includes an automated exporter for lecture decks hosted at:

- `https://zzhang.xyz/teaching/security1-fall26/lectures/`

### How it works

- `scripts/export_slides.py` downloads the lectures index page.
- It discovers lecture deck links under the lectures path.
- It runs `decktape` once per lecture and writes one PDF per lecture into `slides/`.
  - In GitHub Actions, it adds Chromium `--no-sandbox` flags for runner compatibility.
- It removes stale PDFs if a lecture disappears from the index.

### Run manually

```bash
npm install -g decktape
python scripts/export_slides.py --output-dir slides
```

### Scheduled updates

GitHub Actions workflow: `.github/workflows/update-slides-pdfs.yml`

- Runs on every push
- Runs daily at 4:27 AM UTC (`27 4 * * *`)
- Can also be triggered manually (`workflow_dispatch`)
- Commits and pushes updated PDFs automatically when changes are detected
