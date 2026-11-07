"""
app/fetch.py
Downloads the published AapleSeva / Right to Service source documents into
data/raw/.

Everything app/ingest.py reads comes from this directory, so fetching and
parsing stay separate: you can re-parse offline as often as you like without
hitting the government servers again.

Usage:
    python -m app.fetch              # download anything missing
    python -m app.fetch --force      # re-download everything
    python -m app.fetch --only ns_service_list act
    python -m app.fetch --list       # show the catalogue and exit
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://aaplesarkar.mahaonline.gov.in"

# Separate connect and read timeouts. These government hosts accept the
# connection quickly but can be slow to start streaming a large PDF, so the
# read budget is much larger than the connect budget. Never leave this as a
# bare number and never omit it: without a timeout a stalled socket hangs
# the process forever.
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 60.0
TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 2.0
CHUNK_BYTES = 64 * 1024

# Plain requests gets refused or served a different page by some
# mahaonline.gov.in endpoints, so identify as a normal desktop browser.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9,mr;q=0.8",
}

# The documents to fetch. `kind` drives the sanity check applied to the bytes
# that come back, so a login redirect or an HTML error page cannot quietly be
# saved as a .pdf.
DOCUMENTS = [
    {
        "key": "ns_service_list",
        "filename": "NS_Service_List.pdf",
        "url": f"{BASE_URL}/pdf/NS_Service_List.pdf",
        "kind": "pdf",
        "description": "Notified Services List (as of 31 March 2025) - primary dataset",
    },
    {
        "key": "rts_act_page",
        "filename": "RigthToServiceAct.html",
        "url": f"{BASE_URL}/en/CommonForm/RigthToServiceAct",
        "kind": "html",
        "description": "Right to Public Services Act landing page (lists every document)",
    },
    {
        "key": "act",
        "filename": "RTS_Act_2015.pdf",
        "url": f"{BASE_URL}/pdf/RTS_21-8-2015.pdf",
        "kind": "pdf",
        "description": "Maharashtra Right to Public Services Act, 2015",
    },
    {
        "key": "rules",
        "filename": "RTS_Rules_Gazette.pdf",
        "url": f"{BASE_URL}/pdf/RTS_Rules_Gazette.pdf",
        "kind": "pdf",
        "description": "Right to Public Services Rules (gazette notification)",
    },
    {
        "key": "faq_en",
        "filename": "RTS_FAQ_English.pdf",
        "url": f"{BASE_URL}/pdf/FAQ-English-22-11-2021.pdf",
        "kind": "pdf",
        "description": "Frequently asked questions on the Act (English)",
    },
]


def get_raw_dir() -> Path:
    """Return the data/raw/ directory, creating it if needed."""
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


def _validate(content: bytes, kind: str) -> None:
    """
    Check the downloaded bytes look like the document type we asked for.

    Content-Type cannot be trusted here: this server returns no Content-Type
    at all for its PDFs, so check the actual magic bytes instead.
    """
    if not content:
        raise ValueError("response body was empty")

    if kind == "pdf":
        if not content.startswith(b"%PDF"):
            head = content[:80].decode("utf-8", errors="replace")
            raise ValueError(f"expected a PDF but body starts with {head!r}")
    elif kind == "html":
        head = content[:2048].lower()
        if b"<html" not in head and b"<!doctype" not in head:
            raise ValueError("expected HTML but found no <html> or <!doctype> tag")


def download(session: requests.Session, doc: dict, dest: Path) -> dict:
    """
    Download one document, retrying on transient network failures.

    Writes to a .part file and renames only once the body has been validated,
    so an interrupted run can never leave a truncated file that looks complete.
    Returns a manifest entry. Raises on give-up so the caller can record it.
    """
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with session.get(
                doc["url"], timeout=TIMEOUT, stream=True, allow_redirects=True
            ) as response:
                response.raise_for_status()
                content = b"".join(
                    chunk for chunk in response.iter_content(CHUNK_BYTES) if chunk
                )
                status_code = response.status_code
                final_url = response.url

            _validate(content, doc["kind"])

            part = dest.with_suffix(dest.suffix + ".part")
            part.write_bytes(content)
            part.replace(dest)

            return {
                "key": doc["key"],
                "filename": dest.name,
                "url": doc["url"],
                "final_url": final_url,
                "kind": doc["kind"],
                "description": doc["description"],
                "status": "ok",
                "http_status": status_code,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "attempts": attempt,
            }

        # Retry only on failures that a retry could plausibly fix.
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"    attempt {attempt}/{MAX_ATTEMPTS} failed ({type(exc).__name__})")

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            last_error = f"HTTP {status}"
            # 4xx will not fix itself; stop immediately.
            if 400 <= status < 500:
                raise RuntimeError(f"HTTP {status} for {doc['url']}") from exc
            print(f"    attempt {attempt}/{MAX_ATTEMPTS} failed (HTTP {status})")

        except ValueError as exc:
            # Server answered, but with the wrong thing. Retrying is pointless.
            raise RuntimeError(f"unexpected content: {exc}") from exc

        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_SECONDS * attempt)

    raise RuntimeError(f"gave up after {MAX_ATTEMPTS} attempts ({last_error})")


def fetch_all(keys=None, force=False, raw_dir=None) -> dict:
    """
    Download the selected documents into data/raw/.

    Each document is fetched inside its own try/except, so one dead link
    cannot stop the rest. Returns the manifest dict that was written to
    data/raw/manifest.json.
    """
    raw_dir = Path(raw_dir) if raw_dir else get_raw_dir()
    documents = [d for d in DOCUMENTS if keys is None or d["key"] in keys]

    if not documents:
        raise ValueError(f"no documents matched {keys!r}")

    entries = []
    ok = skipped = failed = 0

    with requests.Session() as session:
        session.headers.update(HEADERS)

        for doc in documents:
            dest = raw_dir / doc["filename"]
            print(f"  {doc['key']:<18} {doc['filename']}")

            if dest.exists() and not force:
                content = dest.read_bytes()
                print(f"    already present, skipping ({len(content):,} bytes)")
                entries.append(
                    {
                        "key": doc["key"],
                        "filename": dest.name,
                        "url": doc["url"],
                        "kind": doc["kind"],
                        "description": doc["description"],
                        "status": "cached",
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )
                skipped += 1
                continue

            try:
                entry = download(session, doc, dest)
                print(f"    saved {entry['bytes']:,} bytes")
                entries.append(entry)
                ok += 1
            except Exception as exc:
                # Catch-all on purpose: one bad document must not abort the run.
                print(f"    FAILED: {exc}", file=sys.stderr)
                entries.append(
                    {
                        "key": doc["key"],
                        "filename": doc["filename"],
                        "url": doc["url"],
                        "kind": doc["kind"],
                        "description": doc["description"],
                        "status": "failed",
                        "error": str(exc),
                        "fetched_at": datetime.now(timezone.utc).isoformat(
                            timespec="seconds"
                        ),
                    }
                )
                failed += 1

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "summary": {
            "requested": len(documents),
            "downloaded": ok,
            "cached": skipped,
            "failed": failed,
        },
        "documents": entries,
    }

    manifest_path = raw_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print()
    print(f"  downloaded {ok}, cached {skipped}, failed {failed}")
    print(f"  manifest -> {manifest_path}")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Download AapleSeva / Right to Service source documents into data/raw/."
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="KEY",
        help="download only these document keys (see --list)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-download even if the file is already in data/raw/",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list the document catalogue and exit",
    )
    args = parser.parse_args(argv)

    if args.list:
        print("Available documents:")
        for doc in DOCUMENTS:
            print(f"  {doc['key']:<18} {doc['kind']:<5} {doc['description']}")
            print(f"  {'':<18} {doc['url']}")
        return 0

    if args.only:
        valid = {d["key"] for d in DOCUMENTS}
        unknown = sorted(set(args.only) - valid)
        if unknown:
            parser.error(
                f"unknown document key(s): {', '.join(unknown)}. "
                f"Valid keys: {', '.join(sorted(valid))}"
            )

    print("Fetching AapleSeva source documents")
    print(f"  destination: {get_raw_dir()}")
    print()

    manifest = fetch_all(keys=args.only, force=args.force)

    # Non-zero exit if nothing usable landed, so a CI step or shell && fails.
    usable = [d for d in manifest["documents"] if d["status"] in ("ok", "cached")]
    return 0 if usable else 1


if __name__ == "__main__":
    sys.exit(main())
