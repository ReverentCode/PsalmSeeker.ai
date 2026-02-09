# scripts/build_index.py
"""
PsalmSeeker index builder (one-time / safe to rerun)

This script will:
1) Load data/bible_kjv.json (verse-level Bible JSON)
2) Extract ALL Psalms (book == "Psalms" / "Psalm", case-insensitive)
3) Chunk each Psalm into verse-blocks designed for context
4) Overwrite data/psalm_data_main.json with the extracted/blocked Psalm chunks
5) Embed each chunk with Ollama embeddings and write storage/psalms_index.npz

Notes:
- It is SAFE to rerun. It will deterministically regenerate psalm_data_main.json + psalms_index.npz.
- Uses your existing services/ollama.py OllamaClient.embed() method.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json
from collections import defaultdict

import numpy as np
from dotenv import load_dotenv

from services.ollama import OllamaClient

load_dotenv()

# Paths
DATA_DIR = os.getenv("DATA_DIR", "data")
BIBLE_PATH = os.getenv("BIBLE_PATH", os.path.join(DATA_DIR, "bible_kjv.json"))
PSALMS_OUT_PATH = os.getenv("PSALMS_PATH", os.path.join(DATA_DIR, "psalm_data_main.json"))
INDEX_PATH = os.getenv("INDEX_PATH", "storage/psalms_index.npz")

# Chunking (tuned for PsalmSeeker “movement + context”)
# Default: 8-verse blocks with 4-verse stride (50% overlap).
# Very short Psalms stay whole for coherence.
BLOCK_VERSES = int(os.getenv("BLOCK_VERSES", "8"))
STRIDE_VERSES = int(os.getenv("STRIDE_VERSES", "4"))
WHOLE_IF_AT_MOST = int(os.getenv("WHOLE_IF_AT_MOST", "10"))  # if psalm has <= 10 verses, keep it as 1 block

# Formatting
INCLUDE_VERSE_NUMBERS_IN_BLOCK_TEXT = os.getenv("INCLUDE_VERSE_NUMBERS", "true").lower() in ("1", "true", "yes")


def _is_psalms_book(book: str) -> bool:
    """
    Be tolerant to common variants: "Psalms", "Psalm", "PSALMS", etc.
    """
    if not book:
        return False
    b = book.strip().lower()
    return b == "psalms" or b == "psalm" or b.startswith("psalm")


def _load_json(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing required file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _group_psalm_verses(bible_rows: list[dict]) -> dict[int, list[tuple[int, str]]]:
    """
    Returns:
      { psalm_number: [(verse_number, verse_text), ...] }
    Where psalm_number == chapter in the Bible JSON for book == Psalms.
    """
    by_psalm: dict[int, list[tuple[int, str]]] = defaultdict(list)

    for r in bible_rows:
        if not _is_psalms_book(r.get("book")):
            continue

        # In your bible_kjv.json structure:
        # book: "Psalms", chapter: <psalm #>, verse: <verse #>, text: <verse text>
        psalm_num = r.get("chapter")
        verse_num = r.get("verse")
        text = (r.get("text") or "").strip()

        if psalm_num is None or verse_num is None or not text:
            continue

        try:
            psalm_num = int(psalm_num)
            verse_num = int(verse_num)
        except Exception:
            continue

        by_psalm[psalm_num].append((verse_num, text))

    # Sort verses within each psalm
    for p in by_psalm:
        by_psalm[p].sort(key=lambda x: x[0])

    return dict(by_psalm)


def _make_blocks(psalm_num: int, verses: list[tuple[int, str]]) -> list[dict]:
    """
    Create overlapping verse-block chunks for a single psalm.

    Strategy:
      - If psalm has <= WHOLE_IF_AT_MOST verses: 1 block (whole psalm)
      - Else: blocks of BLOCK_VERSES with STRIDE_VERSES overlap

    Output dict fields match your psalm_data_main.json schema.
    """
    n = len(verses)
    if n == 0:
        return []

    blocks = []

    if n <= WHOLE_IF_AT_MOST:
        vs = verses[0][0]
        ve = verses[-1][0]
        block_text = _format_block_text(verses)
        blocks.append(
            {
                "psalm": psalm_num,
                "verse_start": vs,
                "verse_end": ve,
                "text": block_text,
            }
        )
        return blocks

    i = 0
    while i < n:
        j = min(i + BLOCK_VERSES, n)
        chunk = verses[i:j]
        vs = chunk[0][0]
        ve = chunk[-1][0]
        block_text = _format_block_text(chunk)

        blocks.append(
            {
                "psalm": psalm_num,
                "verse_start": vs,
                "verse_end": ve,
                "text": block_text,
            }
        )

        if j >= n:
            break
        i += STRIDE_VERSES

    return blocks


def _format_block_text(verses: list[tuple[int, str]]) -> str:
    if INCLUDE_VERSE_NUMBERS_IN_BLOCK_TEXT:
        return "\n".join([f"{v}. {t}" for v, t in verses])
    return "\n".join([t for _, t in verses])


def _write_psalms_json(block_rows: list[dict], out_path: str) -> None:
    """
    Overwrites psalm_data_main.json with ALL psalm blocks and sequential ids.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    out = []
    for idx, r in enumerate(block_rows, start=1):
        out.append(
            {
                "id": idx,
                "psalm": r["psalm"],
                "verse_start": r["verse_start"],
                "verse_end": r["verse_end"],
                "text": r["text"],
            }
        )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"✅ Wrote {len(out)} psalm blocks to: {out_path}")


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12
    return v / n


def main() -> None:
    print("=== PsalmSeeker: build_index.py ===")
    print(f"Bible input:  {BIBLE_PATH}")
    print(f"Psalms out:   {PSALMS_OUT_PATH}")
    print(f"Index out:    {INDEX_PATH}")
    print(f"Chunking: block={BLOCK_VERSES}, stride={STRIDE_VERSES}, whole_if<= {WHOLE_IF_AT_MOST}")
    print(f"Verse numbers in text: {INCLUDE_VERSE_NUMBERS_IN_BLOCK_TEXT}")
    print("")

    bible_rows = _load_json(BIBLE_PATH)
    by_psalm = _group_psalm_verses(bible_rows)

    if not by_psalm:
        raise RuntimeError(
            "No Psalms verses found in bible_kjv.json. "
            "Check that the 'book' field uses something like 'Psalms' and that chapters/verses are present."
        )

    # 1) Extract + block all Psalms into rows
    block_rows: list[dict] = []
    psalm_nums = sorted(by_psalm.keys())

    for p in psalm_nums:
        verses = by_psalm[p]
        blocks = _make_blocks(p, verses)
        block_rows.extend(blocks)
        print(f"Psalm {p:>3}: verses={len(verses):>3}  -> blocks={len(blocks):>2}")

    print("")
    # 2) Rewrite psalm_data_main.json with the full extracted dataset
    _write_psalms_json(block_rows, PSALMS_OUT_PATH)

    # 3) Build the embedding index (.npz)
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    client = OllamaClient()

    texts: list[str] = []
    meta: list[dict] = []
    emb_list: list[list[float]] = []

    print("\nEmbedding blocks (this can take a bit on first run)...\n")

    for i, r in enumerate(block_rows):
        ps = r["psalm"]
        vs = r["verse_start"]
        ve = r["verse_end"]
        block_text = r["text"]

        # Enrich slightly so embeddings remain anchored to Psalm identity
        enriched = f"Psalm {ps} ({vs}-{ve})\n{block_text}"

        emb = client.embed(enriched)

        texts.append(block_text)
        meta.append(
            {
                "id": i + 1,  # align with psalm_data_main.json ids
                "psalm": ps,
                "verse_start": vs,
                "verse_end": ve,
            }
        )
        emb_list.append(emb)

        if (i + 1) % 25 == 0:
            print(f"  Embedded {i+1}/{len(block_rows)}")

    emb_mat = np.array(emb_list, dtype=np.float32)

    # Optional normalization here (you can also normalize at retrieval time; either works if consistent)
    emb_mat = _normalize(emb_mat)

    np.savez_compressed(
        INDEX_PATH,
        texts=np.array(texts, dtype=object),
        meta=np.array(meta, dtype=object),
        emb=emb_mat,
    )

    print(f"\n✅ Index written to: {INDEX_PATH}")
    print(f"Total blocks indexed: {len(texts)}")
    print(f"Embedding dim: {emb_mat.shape[1] if emb_mat.ndim == 2 else 'unknown'}")
    print("\nDone.")


if __name__ == "__main__":
    main()