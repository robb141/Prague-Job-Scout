from __future__ import annotations

import argparse
import logging
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from .collector import collect_jobs


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Collect Prague job postings and build a web report.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Fetch jobs and write the HTML report.")
    collect_parser.add_argument("--config", default="config.yml", help="Path to config file.")

    serve_parser = subparsers.add_parser("serve", help="Serve the generated web report.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "collect":
        summary = collect_jobs(ROOT / args.config)
        print(f"Collected {summary.total} jobs ({summary.new} new).")
        print(f"HTML: {summary.html_path}")
        return

    if args.command == "serve":
        output_dir = ROOT / "output"
        output_dir.mkdir(exist_ok=True)
        handler = lambda *handler_args, **kwargs: SimpleHTTPRequestHandler(  # noqa: E731
            *handler_args,
            directory=str(output_dir),
            **kwargs,
        )
        server = ThreadingHTTPServer((args.host, args.port), handler)
        print(f"Serving {output_dir / 'index.html'} at http://{args.host}:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
