from __future__ import annotations

import argparse
import os


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the Mission Control dashboard.')
    parser.add_argument('--host', default=os.environ.get('MISSION_CONTROL_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('MISSION_CONTROL_PORT', '8020')))
    parser.add_argument('--reload', action='store_true')
    return parser


def main() -> None:
    args = build_parser().parse_args()
    import uvicorn

    uvicorn.run('mission_control.app:app', host=args.host, port=args.port, reload=args.reload)


if __name__ == '__main__':
    main()
