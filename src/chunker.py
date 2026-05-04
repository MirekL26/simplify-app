import re
from typing import List


def preprocess_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^[ \t]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def split_text_into_chunks(
    text: str, chunk_size: int = 10_000, overlap: int = 0
) -> List[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current_chunk = []
    current_size = 0

    for sentence in sentences:
        size = len(sentence)

        if current_size + size > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))

            if overlap > 0 and len(current_chunk) > 1:
                overlap_sentences = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s) + 1
                    else:
                        break
                current_chunk = overlap_sentences + [sentence]
                current_size = overlap_len + size
            else:
                current_chunk = [sentence]
                current_size = size
        else:
            current_chunk.append(sentence)
            current_size += size

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks or [text]


def estimate_tokens(text: str) -> int:
    return len(text) // 4
