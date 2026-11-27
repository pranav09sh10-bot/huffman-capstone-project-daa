const $ = s => document.querySelector(s);
const fmt = n => n >= 1048576 ? (n/1048576).toFixed(2)+" MB" : n >= 1024 ? (n/1024).toFixed(2)+" KB" : n+" B";
const esc = s => String(s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
let huffB64 = null, huffName = "", restoredB64 = null, restoredName = "";

/* tabs */
document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
  document.querySelectorAll(".tab,.panel").forEach(e => e.classList.remove("active"));
  t.classList.add("active"); $("#" + t.dataset.tab).classList.add("active");
});

/* file name display + drag/drop */
$("#cFile").onchange = e => $("#cFileName").textContent = e.target.files[0]?.name || "Choose a text file, or drop it here";
$("#dFile").onchange = e => $("#dFileName").textContent = e.target.files[0]?.name || "Choose a .huff file";
const drop = $("#drop");
["dragover","dragenter"].forEach(ev => drop.addEventListener(ev, e => {e.preventDefault(); drop.classList.add("over");}));
["dragleave","drop"].forEach(ev => drop.addEventListener(ev, e => {e.preventDefault(); drop.classList.remove("over");}));
drop.addEventListener("drop", e => { $("#cFile").files = e.dataTransfer.files; $("#cFile").onchange({target:$("#cFile")}); });

function download(b64, name, type="application/octet-stream") {
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([bytes], {type}));
  a.download = name; a.click(); URL.revokeObjectURL(a.href);
}

/* ---------- COMPRESS ---------- */
$("#cBtn").onclick = async () => {
  const err = $("#cErr"); err.hidden = true;
  const fd = new FormData();
  if ($("#cFile").files[0]) fd.append("file", $("#cFile").files[0]);
  else fd.append("text", $("#cText").value);
  $("#cBtn").disabled = true;
  try {
    const r = await fetch("/api/compress", {method:"POST", body:fd});
    const d = await r.json();
    if (!r.ok) throw new Error(d.error);
    showCompress(d);
  } catch (e) { err.textContent = e.message; err.hidden = false; $("#cResult").hidden = true; }
  $("#cBtn").disabled = false;
};

function showCompress(d) {
  const s = d.stats;
  huffB64 = d.file_b64; huffName = d.filename.replace(/\.[^.]+$/, "") + ".huff";
  $("#cResult").hidden = false;
  $("#sOrig").textContent = fmt(s.original_size);
  $("#sComp").textContent = fmt(s.compressed_size);
  $("#barComp").style.width = Math.min(100, s.compressed_size / s.original_size * 100) + "%";
  const v = $("#verdict");
  if (s.saved_bytes > 0) { v.className = "verdict good"; v.textContent = `Saved ${fmt(s.saved_bytes)} (${s.savings_percent}%). Round-trip check: ${s.verified ? "passed, file restores exactly" : "FAILED"}.`; }
  else { v.className = "verdict bad"; v.textContent = `No saving. The ${fmt(s.header_size)} header is larger than the gain. Try a longer text.`; }

  const items = [
    ["Compression ratio", s.compression_ratio + " : 1"],
    ["Header (frequency table)", fmt(s.header_size)],
    ["Encoded data", fmt(s.payload_size)],
    ["Unique symbols (k)", s.unique_symbols],
    ["Fixed-length code", s.fixed_length_bits + " bits / symbol"],
    ["Average Huffman code", s.avg_code_length + " bits / symbol"],
    ["Entropy (theoretical limit)", s.entropy + " bits / symbol"],
    ["Total encoded bits", s.payload_bits.toLocaleString()],
  ];
  $("#stats").innerHTML = items.map(([a,b]) => `<div class="stat"><span>${a}</span><b>${b}</b></div>`).join("");

  $("#codeTable tbody").innerHTML = d.table.map(r => `<tr><td>${esc(r.symbol)}</td><td>${r.freq.toLocaleString()}</td>
    <td class="bits">${r.code.replace(/1/g,'<span class="one">1</span>')}</td><td>${r.length}</td><td>${r.bits_total.toLocaleString()}</td></tr>`).join("");

  $("#tree").innerHTML = "<ul>" + renderNode(d.tree, "root") + "</ul>";
  $("#tree").onclick = e => { const n = e.target.closest(".n"); if (n && n.nextElementSibling) n.nextElementSibling.hidden = !n.nextElementSibling.hidden; };

  const t = s.time_ms;
  $("#timing").innerHTML = [["Count frequencies",t.frequency],["Build tree",t.build_tree],["Generate codes",t.generate_codes],["Encode",t.encode],["Total",t.total]]
    .map(([a,b]) => `<div><span>${a}</span>${b} ms</div>`).join("");
  $("#cResult").scrollIntoView({behavior:"smooth"});
}

function renderNode(n, edge) {
  if (!n) return "";
  const e = edge === "root" ? "" : `<span class="edge">${edge}</span>`;
  if (n.symbol !== undefined) return `<li><span class="n leaf">${e}${esc(n.symbol)} (${n.freq})</span></li>`;
  return `<li><span class="n">${e}● ${n.freq}</span><ul>${renderNode(n.left,"0")}${renderNode(n.right,"1")}</ul></li>`;
}
$("#dlBtn").onclick = () => download(huffB64, huffName);

/* ---------- DECOMPRESS ---------- */
$("#dBtn").onclick = async () => {
  const err = $("#dErr"); err.hidden = true;
  const f = $("#dFile").files[0];
  if (!f) { err.textContent = "Choose a .huff file first."; err.hidden = false; return; }
  const fd = new FormData(); fd.append("file", f);
  try {
    const r = await fetch("/api/decompress", {method:"POST", body:fd});
    const d = await r.json();
    if (!r.ok) throw new Error(d.error);
    restoredB64 = d.file_b64; restoredName = d.filename;
    $("#dInfo").className = "verdict good";
    $("#dInfo").textContent = `Restored ${fmt(d.size)} from ${f.name}.`;
    $("#dPreview").textContent = d.preview;
    $("#dResult").hidden = false;
  } catch (e) { err.textContent = e.message; err.hidden = false; $("#dResult").hidden = true; }
};
$("#dlRestore").onclick = () => download(restoredB64, restoredName, "text/plain");
