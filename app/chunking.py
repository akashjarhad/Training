"""
app/chunking.py
Splits the downloaded AapleSeva documents into retrieval-sized chunks, keeping
the provenance of every chunk.

Each chunk records where it came from, which is what makes a semantic search
answer citable rather than just plausible:

    source  - the file in data/raw/ the text was read from
    page    - the 1-based page it sits on (None for the HTML page)
    title   - the human-readable document title, from data/raw/manifest.json

Run ``python -m app.fetch`` first to populate data/raw/.

    python -m app.chunking                 # summarise the chunks
    python -m app.chunking --show 3        # print a few chunks in full
    python -m app.chunking --source RTS_Act_2015.pdf
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from pypdf import PdfReader

# Chunk sizes are in characters, not tokens: these documents mix English and
# Devanagari, and a character budget behaves predictably across both. ~1200
# characters is roughly a long paragraph, comfortably inside the context a
# MiniLM-class embedding model handles well.
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# Below this a chunk is page furniture (a stray header, a page number) rather
# than content worth embedding.
MIN_CHUNK_CHARS = 60

# Titles for documents whose description is missing from the manifest.
_FALLBACK_TITLES = {
    "NS_Service_List.pdf": "Notified Services List (as of 31 March 2025)",
    "RigthToServiceAct.html": "Right to Public Services Act - portal page",
    "RTS_Act_2015.pdf": "Maharashtra Right to Public Services Act, 2015",
    "RTS_Rules_Gazette.pdf": "Right to Public Services Rules (gazette)",
    "RTS_FAQ_English.pdf": "Frequently asked questions on the Act (English)",
    "RTS_Notified_Water_Supply.pdf":
        "Notified services - Water Supply and Sanitation Department",
    "RTS_Notified_Food_Civil_Supplies.pdf":
        "Notified services - Food, Civil Supplies and Consumer Protection",
}


@dataclass
class Chunk:
    """One retrieval-sized passage, with the provenance needed to cite it."""

    id: str
    text: str
    source: str
    page: int | None
    title: str
    source_url: str = ""
    chunk_index: int = 0
    n_chars: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def metadata(self) -> dict:
        """
        Metadata for the vector store.

        Chroma only accepts str / int / float / bool / None in metadata, so
        ``page`` is normalised to an int (-1 meaning "not paginated") rather
        than left as None.
        """
        return {
            "source": self.source,
            "page": self.page if self.page is not None else -1,
            "title": self.title,
            "source_url": self.source_url,
            "chunk_index": self.chunk_index,
        }


def get_raw_dir(raw_dir=None) -> Path:
    """Return the directory holding the downloaded documents."""
    if raw_dir:
        return Path(raw_dir)
    return Path(__file__).resolve().parent.parent / "data" / "raw"


def load_manifest(raw_dir: Path) -> dict:
    """
    Read data/raw/manifest.json so chunks can carry a real title and URL.

    Returns {filename: {"title": ..., "url": ...}}. Missing or unreadable
    manifest is not fatal; the fallback titles are used instead.
    """
    path = raw_dir / "manifest.json"
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  warning: could not read manifest ({exc})", file=sys.stderr)
        return out

    for doc in data.get("documents", []):
        name = doc.get("filename")
        if name:
            out[name] = {
                "title": doc.get("description") or "",
                "url": doc.get("url") or "",
            }
    return out


def _clean(text: str) -> str:
    """Normalise whitespace without destroying paragraph breaks."""
    text = text.replace("\u00a0", " ").replace("\r", "\n")
    # Collapse runs of spaces/tabs, but keep newlines as paragraph signal.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Drop the space-padding pypdf's layout mode adds at line starts.
    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()


def _strip_html(raw: str) -> str:
    """Turn an HTML page into plain text well enough to embed."""
    # Remove whole elements whose text is not content.
    raw = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", raw)
    # Keep block boundaries as newlines so paragraphs survive.
    raw = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6]|/tr)\s*/?>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return _clean(html.unescape(raw))


def split_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping windows, preferring to break at a boundary.

    The overlap means a sentence that straddles a cut still appears whole in
    one of the two chunks, so a query matching it is not lost at the seam.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))

        if end < len(text):
            # Prefer a paragraph break, then a sentence end, then a space,
            # searching only the last quarter of the window so a chunk never
            # ends up tiny.
            window_floor = start + (size * 3) // 4
            cut = -1
            for pattern in ("\n\n", ". ", "\n", " "):
                found = text.rfind(pattern, window_floor, end)
                if found != -1:
                    cut = found + len(pattern)
                    break
            if cut != -1:
                end = cut

        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)

        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return pieces


def chunk_pdf(path: Path, title: str, source_url: str) -> list[Chunk]:
    """
    Chunk a PDF page by page, so every chunk keeps a real page number.

    A page that cannot be read is reported and skipped rather than losing the
    rest of the document.
    """
    chunks: list[Chunk] = []
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        print(f"  {path.name}: unreadable ({type(exc).__name__}: {exc})", file=sys.stderr)
        return chunks

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            print(f"  {path.name} p{page_no}: skipped ({type(exc).__name__})",
                  file=sys.stderr)
            continue

        text = _clean(text)
        if len(text) < MIN_CHUNK_CHARS:
            continue

        for idx, piece in enumerate(split_text(text)):
            if len(piece) < MIN_CHUNK_CHARS:
                continue
            chunks.append(
                Chunk(
                    id=f"{path.name}:p{page_no}:{idx}",
                    text=piece,
                    source=path.name,
                    page=page_no,
                    title=title,
                    source_url=source_url,
                    chunk_index=idx,
                    n_chars=len(piece),
                )
            )
    return chunks


def chunk_html(path: Path, title: str, source_url: str) -> list[Chunk]:
    """Chunk an HTML page. There are no pages, so ``page`` stays None."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"  {path.name}: unreadable ({exc})", file=sys.stderr)
        return []

    text = _strip_html(raw)
    chunks = []
    for idx, piece in enumerate(split_text(text)):
        if len(piece) < MIN_CHUNK_CHARS:
            continue
        chunks.append(
            Chunk(
                id=f"{path.name}:{idx}",
                text=piece,
                source=path.name,
                page=None,
                title=title,
                source_url=source_url,
                chunk_index=idx,
                n_chars=len(piece),
            )
        )
    return chunks


def chunk_documents(raw_dir=None, only=None) -> list[Chunk]:
    """
    Chunk every document in data/raw/.

    ``only`` restricts the run to the given filenames. Each document is
    handled inside its own try/except so one bad file cannot stop the rest.
    """
    raw = get_raw_dir(raw_dir)
    if not raw.exists():
        raise FileNotFoundError(
            f"{raw} not found. Run 'python -m app.fetch' first."
        )

    manifest = load_manifest(raw)
    paths = sorted(
        p for p in raw.iterdir()
        if p.is_file() and p.suffix.lower() in (".pdf", ".html", ".htm")
    )
    if only:
        wanted = set(only)
        paths = [p for p in paths if p.name in wanted]
    if not paths:
        raise FileNotFoundError(f"no PDF or HTML documents found in {raw}")

    all_chunks: list[Chunk] = []
    for path in paths:
        info = manifest.get(path.name, {})
        title = info.get("title") or _FALLBACK_TITLES.get(path.name) or path.stem
        url = info.get("url", "")

        try:
            if path.suffix.lower() == ".pdf":
                produced = chunk_pdf(path, title, url)
            else:
                produced = chunk_html(path, title, url)
        except Exception as exc:
            print(f"  {path.name}: FAILED ({type(exc).__name__}: {exc})", file=sys.stderr)
            continue

        pages = {c.page for c in produced if c.page is not None}
        print(f"  {path.name:<38} {len(produced):>5} chunks"
              f"  {len(pages) or '-':>4} pages")
        all_chunks.extend(produced)

    return all_chunks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Chunk the documents in data/raw/, keeping source, page and title."
    )
    parser.add_argument("--raw-dir", metavar="PATH")
    parser.add_argument("--source", nargs="+", metavar="FILE",
                        help="only chunk these filenames")
    parser.add_argument("--show", type=int, default=0, metavar="N",
                        help="print the first N chunks in full")
    args = parser.parse_args(argv)

    print("Chunking AapleSeva documents")
    try:
        chunks = chunk_documents(args.raw_dir, args.source)
    except FileNotFoundError as exc:
        print(f"  error: {exc}", file=sys.stderr)
        return 1

    if not chunks:
        print("  error: no chunks produced", file=sys.stderr)
        return 1

    sizes = [c.n_chars for c in chunks]
    print()
    print(f"  total chunks  {len(chunks)}")
    print(f"  documents     {len({c.source for c in chunks})}")
    print(f"  chars/chunk   min {min(sizes)}  mean {sum(sizes)//len(sizes)}"
          f"  max {max(sizes)}")
    print(f"  with a page   {sum(1 for c in chunks if c.page is not None)}")

    for chunk in chunks[: args.show]:
        print()
        print(f"  --- {chunk.id} ---")
        print(f"  title: {chunk.title}")
        print(f"  page : {chunk.page}")
        print(f"  {chunk.text[:400]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
