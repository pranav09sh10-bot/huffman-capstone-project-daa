# Huffman File Compressor (DAA Project 3)

Lossless text-file compression using Huffman Coding, with a Flask backend and a browser front end.

## Structure
```
huffman_project/
├── app.py              Flask backend (API + serves the page)
├── huffman.py          Huffman algorithm (frequencies, tree, codes, encode, decode, .huff format)
├── test_huffman.py     Round-trip tests
├── requirements.txt
├── sample.txt          Try this file
├── templates/index.html
└── static/style.css, script.js
```

## Run
```
cd huffman_project
python -m venv venv
venv\Scripts\activate          (Windows)      source venv/bin/activate   (Mac/Linux)
pip install -r requirements.txt
python test_huffman.py         (optional: check the algorithm)
python app.py
```
Open http://127.0.0.1:5000

## Complexity
n = bytes in file, k = distinct symbols (<= 256)
| Step | Time | Space |
|---|---|---|
| Frequency count | O(n) | O(k) |
| Build tree (min-heap) | O(k log k) | O(k) |
| Generate codes | O(k) | O(k) |
| Encode / Decode | O(n) | O(n) |
| Total | O(n + k log k) | O(n + k) |

Huffman is optimal among prefix codes: entropy H <= average length < H + 1.
