"""
app.py - Flask backend for the Huffman compression project.

Run:  python app.py      then open http://127.0.0.1:5000
"""
import base64
from flask import Flask, jsonify, render_template, request
import huffman

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024   # 20 MB upload limit


def get_input_bytes():
    """Take input from an uploaded file OR from the text box."""
    f = request.files.get("file")
    if f and f.filename:
        return f.read(), f.filename
    text = request.form.get("text", "")
    return text.encode("utf-8"), "pasted_text.txt"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/compress", methods=["POST"])
def api_compress():
    data, name = get_input_bytes()
    if not data:
        return jsonify(error="Please upload a file or paste some text."), 400
    blob, stats, codes, root, freq = huffman.compress(data)
    # verify losslessness before returning
    stats["verified"] = huffman.decompress(blob) == data
    return jsonify(
        filename=name,
        stats=stats,
        table=huffman.code_table(codes, freq),
        tree=huffman.tree_to_dict(root),
        file_b64=base64.b64encode(blob).decode(),
    )


@app.route("/api/decompress", methods=["POST"])
def api_decompress():
    f = request.files.get("file")
    if not f:
        return jsonify(error="Please choose a .huff file."), 400
    try:
        data = huffman.decompress(f.read())
    except Exception as e:
        return jsonify(error=str(e)), 400
    name = f.filename[:-5] if f.filename.endswith(".huff") else f.filename
    return jsonify(
        filename=name + ".restored.txt",
        size=len(data),
        preview=data[:2000].decode("utf-8", errors="replace"),
        file_b64=base64.b64encode(data).decode(),
    )


if __name__ == "__main__":
    app.run(debug=True)
