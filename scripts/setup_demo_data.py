#!/usr/bin/env python3
"""Fill all demo systems idempotently through their public/admin APIs."""

from demo_data_api import main

if __name__ == "__main__":
    raise SystemExit(main("setup"))
