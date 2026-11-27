"""
huffman.py - Core Huffman Coding engine (no web code here).

Pipeline:
    1. Count byte frequencies
    2. Build the Huffman tree with a min-heap
    3. Walk the tree to generate prefix-free binary codes
    4. Encode  : data  -> bit string -> packed bytes
    5. Decode  : packed bytes -> bit string -> data

Works on raw BYTES, so it compresses any file (UTF-8 text, code, CSV, ...).

Compressed file format (.huff):
    4 bytes  magic  b"HUF1"
    4 bytes  original length (unsigned int)
    1 byte   padding bits added to the last byte (0-7)
    2 bytes  number of unique symbols N
    N * 5    (1 byte symbol, 4 bytes frequency)   <- the frequency table
    ...      packed bit stream
"""
import heapq
import math
import struct
import time
from collections import Counter

MAGIC = b"HUF1"


class Node:
    """A node of the Huffman tree. Leaves hold a symbol; internal nodes do not."""
    __slots__ = ("freq", "symbol", "left", "right")

    def __init__(self, freq, symbol=None, left=None, right=None):
        self.freq = freq
        self.symbol = symbol
        self.left = left
        self.right = right

    def is_leaf(self):
        return self.left is None and self.right is None


# --------------------------------------------------------------------------
# Step 1: frequencies          O(n) time, O(k) space   (k = unique symbols <= 256)
# --------------------------------------------------------------------------
def calculate_frequencies(data: bytes) -> dict:
    return dict(Counter(data))


# --------------------------------------------------------------------------
# Step 2: build tree           O(k log k) time, O(k) space
# --------------------------------------------------------------------------
def build_huffman_tree(freq: dict):
    if not freq:
        return None
    # (frequency, tie_breaker, node). The tie_breaker keeps the result
    # deterministic, so the compressor and decompressor build the SAME tree.
    heap = [(f, s, Node(f, s)) for s, f in sorted(freq.items())]
    heapq.heapify(heap)
    counter = 256  # tie-breaker ids for internal nodes (leaves use the symbol)
    while len(heap) > 1:
        f1, _, n1 = heapq.heappop(heap)
        f2, _, n2 = heapq.heappop(heap)
        heapq.heappush(heap, (f1 + f2, counter, Node(f1 + f2, None, n1, n2)))
        counter += 1
    return heap[0][2]


# --------------------------------------------------------------------------
# Step 3: generate codes       O(k) time, O(k) space
# --------------------------------------------------------------------------
def generate_codes(root) -> dict:
    if root is None:
        return {}
    if root.is_leaf():            # file with one repeated symbol
        return {root.symbol: "0"}
    codes, stack = {}, [(root, "")]
    while stack:
        node, code = stack.pop()
        if node.is_leaf():
            codes[node.symbol] = code
        else:
            stack.append((node.right, code + "1"))
            stack.append((node.left, code + "0"))
    return codes


# --------------------------------------------------------------------------
# Step 4: encode               O(n) time, O(n) space
# --------------------------------------------------------------------------
def encode(data: bytes, codes: dict):
    bits = "".join(codes[b] for b in data)
    padding = (8 - len(bits) % 8) % 8
    bits += "0" * padding
    packed = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
    return packed, padding


# --------------------------------------------------------------------------
# Step 5: decode               O(n) time, O(n) space
# --------------------------------------------------------------------------
_BYTE_TO_BITS = [format(i, "08b") for i in range(256)]


def decode(packed: bytes, padding: int, freq: dict, original_len: int) -> bytes:
    if original_len == 0:
        return b""
    root = build_huffman_tree(freq)
    if root.is_leaf():
        return bytes([root.symbol]) * original_len
    out = bytearray()
    node = root
    bits = "".join(_BYTE_TO_BITS[b] for b in packed)
    if padding:
        bits = bits[:-padding]
    for bit in bits:
        node = node.left if bit == "0" else node.right
        if node.is_leaf():
            out.append(node.symbol)
            node = root
            if len(out) == original_len:
                break
    return bytes(out)


# --------------------------------------------------------------------------
# File-level API
# --------------------------------------------------------------------------
def compress(data: bytes):
    """Return (compressed_bytes, stats_dict, codes, tree_root, freq)."""
    t0 = time.perf_counter()
    freq = calculate_frequencies(data)
    t1 = time.perf_counter()
    root = build_huffman_tree(freq)
    t2 = time.perf_counter()
    codes = generate_codes(root)
    t3 = time.perf_counter()
    packed, padding = encode(data, codes)
    t4 = time.perf_counter()

    header = MAGIC + struct.pack(">IBH", len(data), padding, len(freq))
    table = b"".join(struct.pack(">BI", s, f) for s, f in sorted(freq.items()))
    blob = header + table + packed

    n = len(data)
    entropy = -sum((f / n) * math.log2(f / n) for f in freq.values()) if n else 0.0
    avg_len = sum(freq[s] * len(c) for s, c in codes.items()) / n if n else 0.0
    payload_bits = sum(freq[s] * len(c) for s, c in codes.items())

    stats = {
        "original_size": n,
        "compressed_size": len(blob),
        "header_size": len(header) + len(table),
        "payload_size": len(packed),
        "payload_bits": payload_bits,
        "saved_bytes": n - len(blob),
        "savings_percent": round((1 - len(blob) / n) * 100, 2) if n else 0.0,
        "compression_ratio": round(n / len(blob), 3) if blob else 0.0,
        "unique_symbols": len(freq),
        "entropy": round(entropy, 4),
        "avg_code_length": round(avg_len, 4),
        "fixed_length_bits": max(1, math.ceil(math.log2(len(freq)))) if freq else 0,
        "time_ms": {
            "frequency": round((t1 - t0) * 1000, 3),
            "build_tree": round((t2 - t1) * 1000, 3),
            "generate_codes": round((t3 - t2) * 1000, 3),
            "encode": round((t4 - t3) * 1000, 3),
            "total": round((t4 - t0) * 1000, 3),
        },
    }
    return blob, stats, codes, root, freq


def decompress(blob: bytes) -> bytes:
    if len(blob) < 11 or blob[:4] != MAGIC:
        raise ValueError("Not a valid .huff file (bad header).")
    original_len, padding, n_sym = struct.unpack(">IBH", blob[4:11])
    pos = 11
    freq = {}
    for _ in range(n_sym):
        s, f = struct.unpack(">BI", blob[pos:pos + 5])
        freq[s] = f
        pos += 5
    data = decode(blob[pos:], padding, freq, original_len)
    if len(data) != original_len:
        raise ValueError("File is corrupted: decoded length does not match.")
    return data


# --------------------------------------------------------------------------
# Helpers for the UI
# --------------------------------------------------------------------------
def char_label(b: int) -> str:
    return {10: "\\n", 13: "\\r", 9: "\\t", 32: "' ' (space)"}.get(
        b, chr(b) if 33 <= b < 127 else f"0x{b:02X}")


def tree_to_dict(node):
    """Convert tree to nested dict for JSON / front-end display."""
    if node is None:
        return None
    if node.is_leaf():
        return {"freq": node.freq, "symbol": char_label(node.symbol)}
    return {"freq": node.freq, "left": tree_to_dict(node.left),
            "right": tree_to_dict(node.right)}


def code_table(codes: dict, freq: dict):
    rows = [{"symbol": char_label(s), "byte": s, "freq": freq[s],
             "code": c, "length": len(c), "bits_total": freq[s] * len(c)}
            for s, c in codes.items()]
    rows.sort(key=lambda r: (-r["freq"], r["byte"]))
    return rows
