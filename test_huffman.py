"""Run:  python test_huffman.py"""
import os, huffman

cases = [b"", b"a", b"aaaaaaa", b"abracadabra", b"hello world " * 200,
         "नमस्ते दुनिया — héllo ✓".encode("utf-8"), os.urandom(5000),
         open("sample.txt", "rb").read()]
for d in cases:
    blob, st, *_ = huffman.compress(d)
    assert huffman.decompress(blob) == d
    print(f"OK  {len(d):>6} -> {len(blob):>6} bytes  ({st['savings_percent']}% saved)")
print("All tests passed.")
