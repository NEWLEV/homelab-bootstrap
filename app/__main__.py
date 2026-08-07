from __future__ import annotations

import argparse
import os


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the Aisha dashboard app.')
    parser.add_argument('--host', default=os.environ.get('AISHA_HOST', '127.0.0.1'), help='Bind host for the web app.')
    parser.add_argument('--port', type=int, default=int(os.environ.get('AISHA_PORT', '8000')), help='Bind port for the web app.')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload during development.')
    return parser


def main() -> None:
    args = build_parser().parse_args()
    import uvicorn

    uvicorn.run('app.main:app', host=args.host, port=args.port, reload=args.reload)


if __name__ == '__main__':
    main()
