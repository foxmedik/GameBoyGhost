from __future__ import annotations

import hashlib
import re


def _shingles(text: str, n: int = 5) -> list[str]:
    tokens = re.findall(r"\w+", text.lower())
    if len(tokens) < n:
        return [" ".join(tokens)] if tokens else []
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def simhash(text: str, bits: int = 64) -> int:
    vector = [0] * bits
    for shingle in _shingles(text):
        h = int.from_bytes(hashlib.blake2b(shingle.encode(), digest_size=8).digest(), "big")
        for b in range(bits):
            vector[b] += 1 if (h >> b) & 1 else -1
    value = 0
    for b in range(bits):
        if vector[b] > 0:
            value |= 1 << b
    return value


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def is_near_duplicate(a: int, b: int, threshold: int = 3) -> bool:
    return hamming(a, b) <= threshold
