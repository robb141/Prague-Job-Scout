from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from .config import AppConfig
from .models import JobPosting


def write_html(path: Path, jobs: list[JobPosting], config: AppConfig, last_run_at: str | None) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    roles = ", ".join(config.roles)
    last_run = last_run_at or "first run"
    rows = "\n".join(_html_row(job) for job in jobs)
    new_count = sum(1 for job in jobs if job.is_new)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Prague Job Scout</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #657084;
      --line: #dfe4ec;
      --new: #fff3bf;
      --accent: #176b87;
      --accent-soft: #d9eef4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      padding: 24px 28px 16px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    .meta {{ color: var(--muted); font-size: 14px; line-height: 1.5; }}
    .toolbar {{
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      padding: 16px 28px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }}
    input {{
      min-width: min(420px, 100%);
      height: 40px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 12px;
      font: inherit;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      border-radius: 999px;
      padding: 0 10px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 700;
      font-size: 13px;
    }}
    main {{ padding: 20px 28px 36px; }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 1180px;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #eef2f6;
      z-index: 1;
      white-space: nowrap;
    }}
    tr.new {{ background: var(--new); }}
    a {{ color: #0b5cab; font-weight: 700; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .muted {{ color: var(--muted); }}
    .status {{
      display: inline-block;
      min-width: 46px;
      color: #754c00;
      font-weight: 800;
    }}
    @media (max-width: 720px) {{
      header, .toolbar, main {{ padding-left: 14px; padding-right: 14px; }}
      h1 {{ font-size: 22px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Prague Job Scout</h1>
    <div class="meta">
      {len(jobs)} matching positions, {new_count} new. Generated {escape(generated_at)}. Previous run: {escape(last_run)}.<br>
      Roles: {escape(roles)}. Location: all Prague districts.
    </div>
  </header>
  <div class="toolbar">
    <input id="search" type="search" placeholder="Filter company, title, district, description">
    <span class="pill">{new_count} new</span>
  </div>
  <main>
    <div class="table-wrap">
      <table id="jobs">
        <thead>
          <tr>
            <th>Status</th>
            <th>Company</th>
            <th>Position</th>
            <th>District</th>
            <th>Location</th>
            <th>Posted</th>
            <th>Description</th>
            <th>Source</th>
            <th>Query</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>
  </main>
  <script>
    const search = document.querySelector("#search");
    const rows = [...document.querySelectorAll("#jobs tbody tr")];
    search.addEventListener("input", () => {{
      const needle = search.value.trim().toLowerCase();
      rows.forEach((row) => {{
        row.style.display = row.innerText.toLowerCase().includes(needle) ? "" : "none";
      }});
    }});
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _html_row(job: JobPosting) -> str:
    row_class = " class=\"new\"" if job.is_new else ""
    status = "<span class=\"status\">NEW</span>" if job.is_new else "<span class=\"muted\">seen</span>"
    return f"""<tr{row_class}>
  <td>{status}</td>
  <td>{escape(job.company)}</td>
  <td><a href="{escape(job.url)}" target="_blank" rel="noopener">{escape(job.title)}</a></td>
  <td>{escape(job.district_match)}</td>
  <td>{escape(job.location)}</td>
  <td>{escape(job.posted_date)}</td>
  <td>{escape(job.company_description or job.summary)}</td>
  <td>{escape(job.source)}</td>
  <td>{escape(job.matched_query)}</td>
</tr>"""
