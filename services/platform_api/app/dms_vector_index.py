from __future__ import annotations

import argparse
import json

from .config import settings
from .dms_vector import DmsVectorIndex, retry_refresh
from .paperless_client import PaperlessClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Index Paperless OCR text in pgvector")
    parser.add_argument("--max-documents", type=int, default=100)
    parser.add_argument("--wait-seconds", type=int, default=90)
    args = parser.parse_args()
    index = DmsVectorIndex(settings, PaperlessClient(settings))
    print(
        json.dumps(
            retry_refresh(index, args.wait_seconds, args.max_documents),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
