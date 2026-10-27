"""Split long filing/transcript sections into overlapping, paragraph-aligned chunks."""

import re
from dataclasses import dataclass

TARGET_CHARS = 1400
OVERLAP_CHARS = 200
MIN_CHARS = 120


@dataclass
class Chunk:
    section: str
    ordinal: int
    text: str


def _paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    out: list[str] = []
    for part in parts:
        # Transcripts arrive as one huge line; fall back to sentence boundaries.
        if len(part) <= TARGET_CHARS:
            out.append(part)
            continue
        sentence_buf = ""
        for sentence in re.split(r"(?<=[.!?])\s+", part):
            if len(sentence_buf) + len(sentence) > TARGET_CHARS and sentence_buf:
                out.append(sentence_buf.strip())
                sentence_buf = ""
            sentence_buf += sentence + " "
        if sentence_buf.strip():
            out.append(sentence_buf.strip())
    return out


def _overlap(paragraphs: list[str]) -> list[str]:
    """The tail of a finished chunk, carried into the next so facts spanning a boundary stay retrievable."""
    carry: list[str] = []
    size = 0
    for prev in reversed(paragraphs):
        if size + len(prev) > OVERLAP_CHARS:
            break
        carry.insert(0, prev)
        size += len(prev)
    if not carry and paragraphs:
        # Last paragraph is too long to carry whole: keep its final words.
        tail = paragraphs[-1][-OVERLAP_CHARS:]
        carry = [tail[tail.find(" ") + 1 :] if " " in tail else tail]
    return carry


def chunk_text(text: str, section: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[str] = []
    size = 0

    def flush():
        body = "\n".join(current).strip()
        if len(body) >= MIN_CHARS or (body and not chunks):
            chunks.append(Chunk(section=section, ordinal=len(chunks), text=body))

    for para in _paragraphs(text):
        if size + len(para) > TARGET_CHARS and current:
            flush()
            current = _overlap(current)
            size = sum(len(p) for p in current)
        current.append(para)
        size += len(para)
    if current:
        flush()
    return chunks
