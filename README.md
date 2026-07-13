# Prague Job Scout

Collects open positions matching configured role keywords across all Prague districts, and writes:

- `output/index.html` with new jobs highlighted

The app remembers previously seen job IDs in `data/state.json`, so the next run can mark fresh postings as `NEW`.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Configure

Edit `config.yml` to change the target role keywords and whether broad Prague-only postings should be included when the job board does not expose a district.

## Run

```bash
.venv/bin/python -m findwork collect
```

Open the generated web report:

```bash
.venv/bin/python -m findwork serve
```

Then visit http://127.0.0.1:8000.

## Test

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest
```

## Notes

Current sources:

- Jobs.cz
- Prace.cz
- LinkedIn (public guest search; rate-limited, so some queries may be skipped on busy runs)
- NoFluffJobs
- StartupJobs
- JenPráce.cz
- Cocuma
- Configurable direct company career pages

Some boards do not expose Prague district details. When a source only exposes `Praha`, the report labels it as `Praha, district not specified` so you can decide manually.

For companies that do not advertise on portals, add their career pages under
`sources.company_pages.pages` in `config.yml`.
