"""Explicit, loopback-only development service entry point."""

from __future__ import annotations

import argparse
import logging


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("web", "api"))
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    if args.service == "web":
        from web.app import app
    else:
        from api.app import app
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    app.run(
        host="127.0.0.1", port=args.port, debug=args.debug,
        use_reloader=False, use_debugger=False,
    )


if __name__ == "__main__":
    main()
