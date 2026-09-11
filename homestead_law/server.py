"""Localhost web UI for homestead-law — intake and dashboard.

Serves on 127.0.0.1 only.  All HTML/CSS/JS is embedded (no external files,
no CDN).  Imports of ``http.server`` and ``urllib.parse`` are **local** to
``serve()`` — this module's top level touches nothing network-shaped, so
``import homestead_law`` stays import-pure.

The server is a thin dispatch over existing modules: ``intake.extract()``
for text extraction, the sidecar store for persisting, ``app.window.Window``
for reading records back, ``queue`` for the deadline dashboard, and the
Nestor seam — optional, and absent without the ``entity`` extra — for
entity lookup and court orders.

**This is where a household enters its own information.** The *Records* tab
is a plain form: pick the matter and the field, type the value, store it at
the rung the pack declares (never a rung chosen here); a second form adds a
deadline.  The same tab lists what is on file, composed through the gate —
the list pane's view of each record, and the detail pane's on a click.  The
*Intake* tab is the other way in: paste a notice and store what the
extractor finds.

**Chokepoint**: this module never accesses ``.payload``.  Records reach the
browser as ``Row.text`` / ``Served.value`` from ``Window``, queue items as
``Due.shown``, and entity/decision data as dicts from Nestor's public API.

``build_server()`` returns the bound ``HTTPServer`` without serving, so a
test can drive the real handlers on an ephemeral port; ``serve()`` is the
operator's door and blocks until Ctrl+C.
"""
from __future__ import annotations

__all__ = ["build_server", "serve"]

#: The largest request body this server will read into memory. A localhost UI
#: has no use for a megabyte of JSON, and reading whatever ``Content-Length``
#: claims is the one place a local page can spend the household's RAM.
MAX_BODY_BYTES = 1 << 20

#: How long a refused request's leftover bytes get to arrive before the
#: connection is closed anyway.  Short: the client sent them already or never
#: will; this waits for a segment in flight, not for a slow sender.
DRAIN_TIMEOUT_SECONDS = 0.2


def _drain(sock, *, limit=MAX_BODY_BYTES, timeout=DRAIN_TIMEOUT_SECONDS):
    """Read and discard whatever the client already sent of a body the
    handler refused to read, so the socket closes with an empty receive
    buffer.

    Closing a socket that still holds unread bytes makes the kernel answer
    with a reset instead of an orderly close, and on Windows a reset discards
    data the peer has received but not yet read — the 400 the client was
    about to parse (``WinError 10053``).  The bytes are bounded by ``limit``
    and the wait by ``timeout``; a slow or silent client is not waited for,
    and nothing read here is looked at (I-15).  Returns the count discarded.
    """
    discarded = 0
    try:
        sock.settimeout(timeout)
        while discarded < limit:
            chunk = sock.recv(min(65536, limit - discarded))
            if not chunk:
                break
            discarded += len(chunk)
    except OSError:
        pass
    return discarded


class _BadRequest(Exception):
    """A request this handler refuses to read — a malformed or oversized body, a
    ``Content-Length`` that is not a number, a field that is not a string.

    Carries the status to answer with and a one-line reason that names the
    *shape* of the problem (which field, which limit) and never a stored value
    (I-15). Raised rather than returned so every POST path is covered by one
    ``except`` in ``do_POST`` — the alternative is a traceback on the console
    and a reset connection, which is what an unreadable body used to produce.
    """

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _text(body: dict, name: str, default: str = "") -> str:
    """One string field out of a decoded JSON object, or a refusal naming it.

    A number, a list or an object is **refused, never coerced**: ``str(value)``
    turns ``["custody"]`` into ``"['custody']"`` and a dict into a key the store
    would happily accept, and a surface that coerces has decided something the
    operator did not type.  ``None`` reads as the default (the page sends
    ``instruction: null`` for "no instruction").
    """
    value = body.get(name, default)
    if value is None:
        value = default
    if not isinstance(value, str):
        raise _BadRequest(f"{name} must be a string")
    return value


# ── the page ──────────────────────────────────────────────────────────────

_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>homestead-law</title>
<style>
:root {
  --bg: #f8f6f3;
  --surface: #ffffff;
  --text: #2c2c2c;
  --text-2: #6b6560;
  --border: #e0dbd5;
  --accent: #4a6fa5;
  --accent-h: #3d5d8a;
  --accent-l: #e8eff8;
  --ok: #3d7a4f;
  --ok-l: #e8f5ec;
  --warn: #b8862d;
  --warn-l: #fdf3e3;
  --danger: #b54a4a;
  --danger-l: #fce8e8;
  --r: 6px;
}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--text);margin:0;line-height:1.5}
header{background:var(--surface);border-bottom:1px solid var(--border);
  padding:12px 24px;display:flex;align-items:center;gap:16px}
header h1{font-size:18px;font-weight:600;margin:0}
header .sub{font-size:13px;color:var(--text-2)}
nav{background:var(--surface);border-bottom:1px solid var(--border);
  padding:0 24px;display:flex;gap:0}
.tb{background:none;border:none;border-bottom:2px solid transparent;
  padding:10px 16px;font-size:14px;color:var(--text-2);cursor:pointer}
.tb:hover{color:var(--text)}
.tb.on{color:var(--accent);border-bottom-color:var(--accent);font-weight:500}
main{max-width:900px;margin:24px auto;padding:0 24px}
.tab{display:none}.tab.on{display:block}
h2{font-size:16px;font-weight:600;margin:0 0 16px}
textarea{width:100%;min-height:180px;padding:12px;border:1px solid var(--border);
  border-radius:var(--r);font-family:inherit;font-size:14px;line-height:1.6;
  resize:vertical;background:var(--surface)}
textarea:focus{outline:2px solid var(--accent);border-color:transparent}
.btn{display:inline-block;padding:8px 16px;border:none;border-radius:var(--r);
  font-size:14px;font-weight:500;cursor:pointer}
.bp{background:var(--accent);color:#fff}.bp:hover{background:var(--accent-h)}
.bg{background:var(--ok);color:#fff}.bg:hover{background:#336a42}
.bs{padding:4px 10px;font-size:13px}
.btn:disabled{opacity:.5;cursor:not-allowed}
.acts{margin-top:12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.cr{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.kb{display:inline-block;padding:2px 8px;border-radius:12px;font-size:12px;
  font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.k-date{background:var(--accent-l);color:var(--accent)}
.k-party{background:var(--warn-l);color:var(--warn)}
.k-citation{background:#f0e8f8;color:#6b4fa0}
.k-case_number{background:#e8f0f8;color:#4a7fa5}
.k-court{background:var(--ok-l);color:var(--ok)}
.mt{font-size:14px;flex:1;min-width:120px}
.mv{font-size:13px;color:var(--text-2)}
.fs{padding:4px 8px;border:1px solid var(--border);border-radius:4px;font-size:13px;
  background:var(--surface)}
.stored{opacity:.6}.stored .btn,.stored .fs{display:none}
.sm{display:inline-block;padding:4px 10px;border-radius:4px;font-size:13px;font-weight:500}
.s-ok{background:var(--ok-l);color:var(--ok)}
.s-err{background:var(--danger-l);color:var(--danger)}
.qi{display:flex;align-items:center;gap:12px;padding:10px 16px;background:var(--surface);
  border:1px solid var(--border);border-radius:var(--r);margin-bottom:8px;
  box-shadow:0 1px 3px rgba(0,0,0,.08)}
.qu{font-size:13px;font-weight:600;min-width:90px;text-align:right}
.u-over{color:var(--danger)}.u-soon{color:var(--warn)}.u-later{color:var(--ok)}
.qs{flex:1;font-size:14px}
.rb{font-size:12px;padding:2px 6px;border-radius:4px;font-weight:500}
.r-L1,.r-L2{background:#f0eeec;color:#888}
.r-L3{background:#f0eeec;color:#333}
.r-L4{background:var(--warn-l);color:var(--warn)}
.rf{display:flex;gap:8px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
.rf select,.rf input{padding:8px 12px;border:1px solid var(--border);border-radius:var(--r);
  font-size:14px;background:var(--surface)}
.rf input{flex:1;min-width:150px}
.rr{padding:16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--r)}
.oi{padding:12px 16px;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r);margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.oq{font-weight:500}.oc{color:var(--text-2);margin-top:4px}
.os{display:inline-block;font-size:12px;padding:2px 8px;border-radius:12px;margin-top:6px}
.sealed{background:var(--ok-l);color:var(--ok)}
.draft{background:var(--warn-l);color:var(--warn)}
.empty{color:var(--text-2);font-style:italic;padding:24px 0;text-align:center}
.why{font-size:12px;color:var(--text-2);margin-top:6px}
.rw{cursor:pointer}.rw:hover{background:var(--accent-l)}
.rk{font-size:13px;color:var(--text-2);min-width:140px}
.dt{padding:14px 16px;background:var(--accent-l);border-radius:var(--r);margin-top:8px}
.dt .adv{font-size:13px;color:var(--warn);margin-top:6px}
</style>
</head>
<body>
<header>
  <h1>homestead-law</h1>
  <span class="sub">intake &amp; dashboard</span>
</header>
<nav>
  <button class="tb on" onclick="show('records',this)">Records</button>
  <button class="tb" onclick="show('intake',this)">Intake</button>
  <button class="tb" onclick="show('queue',this)">Queue</button>
  <button class="tb" onclick="show('entities',this)">Entities</button>
  <button class="tb" onclick="show('orders',this)">Orders</button>
</nav>
<main>

<section id="t-records" class="tab on">
  <!-- L2b-instances: /api/store and /api/deadline accept id/sub (matter
       instance / repeatable sub-id) below the surface (decision 2); this
       form still always writes the "primary" instance — an instance picker
       here, and /api/instances + /api/matter/open wired into it, are
       L4-surfaces work, deferred to keep this bite's page diff small. -->
  <h2>Enter a record</h2>
  <div class="card">
    <div class="rf">
      <select id="rmatter" onchange="fillFields()"></select>
      <select id="rfield" onchange="showRung()"></select>
      <span class="rb" id="rrung"></span>
    </div>
    <div class="rf">
      <input id="rvalue" placeholder="Value&#8230;" onkeydown="if(event.key==='Enter')storeField()">
      <button class="btn bg" onclick="storeField()">Store</button>
    </div>
    <div class="why" id="rwhy"></div>
    <div id="rmsg"></div>
  </div>

  <h2>Add a deadline</h2>
  <div class="card">
    <div class="rf">
      <input id="did" placeholder="Short id (e.g. hearing, answer)" style="max-width:220px">
      <input id="ddate" placeholder="YYYY-MM-DD" style="max-width:150px">
      <select id="drung">
        <option value="L1">L1 &#8212; public date</option>
        <option value="L3">L3 &#8212; resolves to the parties</option>
        <option value="L4">L4 &#8212; protected; queue shows the instruction</option>
      </select>
    </div>
    <div class="rf">
      <input id="dinstr" placeholder="Instruction shown on the queue (e.g. Custody hearing)" onkeydown="if(event.key==='Enter')storeDeadline()">
      <button class="btn bg" onclick="storeDeadline()">Add</button>
    </div>
    <div id="dmsg"></div>
  </div>

  <h2>On file</h2>
  <div id="rlist"></div>
  <div id="rdetail"></div>
</section>

<section id="t-intake" class="tab">
  <h2>Dump text</h2>
  <textarea id="raw" placeholder="Paste a court notice, call notes, a letter &#8212; anything with dates, names, case numbers, or citations.  The system extracts what it finds."></textarea>
  <div class="acts">
    <button class="btn bp" onclick="doExtract()">Extract</button>
  </div>
  <div id="res" style="margin-top:16px"></div>
</section>

<section id="t-queue" class="tab">
  <h2>What's due</h2>
  <div id="qlist"></div>
</section>

<section id="t-entities" class="tab">
  <h2>Entity lookup</h2>
  <div class="rf">
    <select id="edom">
      <option value="party">Party</option>
      <option value="court">Court</option>
      <option value="citation">Citation</option>
      <option value="jurisdiction">Jurisdiction</option>
    </select>
    <input id="eqry" placeholder="Name or term to resolve&#8230;"
           onkeydown="if(event.key==='Enter')doResolve()">
    <button class="btn bp" onclick="doResolve()">Resolve</button>
  </div>
  <div id="eres"></div>
</section>

<section id="t-orders" class="tab">
  <h2>Court orders &amp; decisions</h2>
  <div id="olist"></div>
</section>

</main>
<script>
function show(name, btn) {
  document.querySelectorAll('.tab').forEach(function(el){el.classList.remove('on')});
  document.querySelectorAll('.tb').forEach(function(el){el.classList.remove('on')});
  document.getElementById('t-'+name).classList.add('on');
  btn.classList.add('on');
  if(name==='records') loadRecords();
  if(name==='queue') loadQueue();
  if(name==='orders') loadOrders();
}

var _matters={};
var _matterNames=[];

function loadMatters() {
  return fetch('/api/matters').then(function(r){return r.json()}).then(function(data){
    _matters={}; _matterNames=[];
    var sel=document.getElementById('rmatter'); sel.innerHTML='';
    data.matters.forEach(function(m){
      _matters[m.name]=m; _matterNames.push(m.name);
      var o=document.createElement('option'); o.value=m.name; o.textContent=m.name; sel.appendChild(o);
    });
    fillFields();
  });
}

// The matter every form posts under.  The selected one, else the first the
// registry returned (I-23 — the enumeration is the registry's, never a literal
// in this file), else nothing: the server refuses a missing matter with a 400
// rather than filing the record under a default one.
function currentMatter() {
  var sel=document.getElementById('rmatter');
  if(sel&&sel.value) return sel.value;
  return _matterNames.length?_matterNames[0]:'';
}

function fillFields() {
  var m=_matters[document.getElementById('rmatter').value];
  var sel=document.getElementById('rfield'); sel.innerHTML='';
  if(!m) return;
  m.fields.forEach(function(f){
    var o=document.createElement('option'); o.value=f.name;
    o.textContent=f.name.replace(/_/g,' ')+' ('+f.rung+')'; sel.appendChild(o);
  });
  showRung();
}

function showRung() {
  var m=_matters[document.getElementById('rmatter').value];
  var fname=document.getElementById('rfield').value;
  var f=m?m.fields.filter(function(x){return x.name===fname})[0]:null;
  var badge=document.getElementById('rrung');
  badge.className='rb r-'+(f?f.rung:'');
  badge.textContent=f?f.rung:'';
  document.getElementById('rwhy').textContent=f?f.why:'';
}

function storeField() {
  var matter=currentMatter();
  var field=document.getElementById('rfield').value;
  var value=document.getElementById('rvalue').value.trim();
  var msg=document.getElementById('rmsg');
  if(!matter){msg.innerHTML='<span class="sm s-err">No matter is registered</span>';return;}
  if(!value){msg.innerHTML='<span class="sm s-err">Type a value first</span>';return;}
  fetch('/api/store',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({matter:matter,field:field,value:value})})
  .then(function(r){return r.json()}).then(function(data){
    if(data.ok){
      msg.innerHTML='<span class="sm s-ok">Stored '+esc(field)+' ('+data.rung+')'
        +(data.replaced?' &#8212; replaced the previous value':'')+'</span>';
      document.getElementById('rvalue').value='';
      loadRecords();
    } else {msg.innerHTML='<span class="sm s-err">'+esc(data.error||'Failed')+'</span>';}
  }).catch(function(){msg.innerHTML='<span class="sm s-err">Error</span>';});
}

function storeDeadline() {
  var matter=currentMatter();
  var id=document.getElementById('did').value.trim();
  var date=document.getElementById('ddate').value.trim();
  var rung=document.getElementById('drung').value;
  var instr=document.getElementById('dinstr').value.trim();
  var msg=document.getElementById('dmsg');
  if(!matter){msg.innerHTML='<span class="sm s-err">No matter is registered</span>';return;}
  if(!id||!date){msg.innerHTML='<span class="sm s-err">An id and a date are needed</span>';return;}
  fetch('/api/deadline',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({matter:matter,id:id,date:date,rung:rung,instruction:instr||null})})
  .then(function(r){return r.json()}).then(function(data){
    if(data.ok){
      msg.innerHTML='<span class="sm s-ok">Deadline '+esc(id)+' added ('+data.rung+')</span>';
      document.getElementById('did').value='';document.getElementById('ddate').value='';
      document.getElementById('dinstr').value='';
      loadRecords();
    } else {msg.innerHTML='<span class="sm s-err">'+esc(data.error||'Failed')+'</span>';}
  }).catch(function(){msg.innerHTML='<span class="sm s-err">Error</span>';});
}

function loadRecords() {
  var matter=currentMatter();
  var div=document.getElementById('rlist');
  document.getElementById('rdetail').innerHTML='';
  if(!matter){div.innerHTML='';return;}
  fetch('/api/records?matter='+encodeURIComponent(matter)).then(function(r){return r.json()}).then(function(data){
    if(!data.rows||!data.rows.length){
      div.innerHTML='<p class="empty">Nothing on file for '+esc(matter)+' yet.</p>';return;}
    var html='';
    data.rows.forEach(function(row){
      var where=row.item_id==='primary'?row.item_type:row.item_type+' / '+row.item_id;
      // The key goes into data- attributes and the click is bound afterwards.
      // It is never spliced into a JS string literal inside an onclick: an
      // attribute value is entity-decoded *before* the script is parsed, so an
      // item id carrying a quote would close the literal no matter how the
      // quote was escaped.  A store key may contain a quote (the engine's
      // `key()` refuses only separators, NUL and whitespace), so this is a
      // reachable id, not a hypothetical one.
      html+='<div class="qi rw" data-matter="'+esc(row.matter)+'"'
        +' data-type="'+esc(row.item_type)+'" data-id="'+esc(row.item_id)+'">'
        +'<span class="rb r-'+esc(row.rung)+'">'+esc(row.rung)+'</span>'
        +'<span class="rk">'+esc(where.replace(/_/g,' '))+'</span>'
        +'<span class="qs">'+esc(row.text)+'</span>'
        +'</div>';
    });
    div.innerHTML=html;
    Array.prototype.forEach.call(div.querySelectorAll('.rw'), function(el){
      el.addEventListener('click', function(){
        openRecord(el.getAttribute('data-matter'), el.getAttribute('data-type'),
                   el.getAttribute('data-id'));
      });
    });
  }).catch(function(){div.innerHTML='<p class="sm s-err">Failed to load records</p>';});
}

function openRecord(matter,item_type,item_id) {
  var div=document.getElementById('rdetail');
  fetch('/api/record?matter='+encodeURIComponent(matter)+'&item_type='+encodeURIComponent(item_type)
    +'&item_id='+encodeURIComponent(item_id)).then(function(r){return r.json()}).then(function(data){
    if(data.error){div.innerHTML='<p class="sm s-err">'+esc(data.error)+'</p>';return;}
    var html='<div class="dt"><strong>'+esc(item_type.replace(/_/g,' '))+'</strong> '
      +'<span class="rb r-'+esc(data.rung)+'">'+esc(data.rung)+'</span><div>'
      +(data.rendered?esc(data.value):'This record is sealed and is not shown here.')+'</div>';
    (data.advisories||[]).forEach(function(a){html+='<div class="adv">'+esc(a)+'</div>';});
    html+='</div>';
    div.innerHTML=html;
  });
}

loadMatters().then(loadRecords);

// Escapes for *both* places a value lands: element text and a double-quoted
// attribute value.  The textContent/innerHTML round-trip this replaced escaped
// & < > and nothing else, so a value carrying a quote escaped an attribute —
// which is how an item id reached the page's own JS.
var _ESC={'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
function esc(s) {
  return String(s===null||s===undefined?'':s).replace(/[&<>"']/g,function(c){return _ESC[c]});
}

var _items=[];

function doExtract() {
  var text=document.getElementById('raw').value.trim();
  if(!text) return;
  fetch('/api/extract',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:text})})
  .then(function(r){return r.json()})
  .then(function(data){_items=data.items; renderItems()})
  .catch(function(){document.getElementById('res').innerHTML=
    '<p class="sm s-err">Extraction failed</p>'});
}

function renderItems() {
  var div=document.getElementById('res');
  if(!_items.length){div.innerHTML='<p class="empty">No structured items found.</p>';return;}
  var html='<h2>Found '+_items.length+' item(s)</h2>';
  _items.forEach(function(item,i){
    var opts='';
    if(item.kind==='date'){
      opts='<option value="hearing_date">Hearing date</option><option value="__deadline__">Deadline</option>';
    } else if(item.kind==='party'){
      opts='<option value="opposing_party">Opposing party</option><option value="child_name">Child name</option>';
    } else if(item.kind==='case_number'){
      opts='<option value="case_number">Case number</option><option value="docket">Docket</option>';
    } else if(item.kind==='court'){
      opts='<option value="courthouse">Courthouse</option>';
    } else {
      opts='<option value="">&#8212;</option><option value="notes">Notes</option>';
    }
    html+='<div class="card" id="c'+i+'"><div class="cr">'
      +'<span class="kb k-'+esc(item.kind)+'">'+esc(item.kind.replace('_',' '))+'</span>'
      +'<span class="mt">'+esc(item.text)+'</span>'
      +'<span class="mv">'+esc(item.value)+'</span>'
      +'<select class="fs" id="f'+i+'">'+opts+'</select>'
      +'<button class="btn bg bs" onclick="storeItem('+i+')">Store</button>'
      +'</div></div>';
  });
  div.innerHTML=html;
}

function storeItem(idx) {
  var item=_items[idx];
  var field=document.getElementById('f'+idx).value;
  if(!field) return;
  var card=document.getElementById('c'+idx);
  // No hardcoded fallback matter: a matter name written down outside the
  // registry is BUG-6's shape.  The selected matter, else the first the
  // registry returned, else refuse here.
  var matter=currentMatter();
  if(!matter){card.innerHTML+='<span class="sm s-err">No matter is registered</span>';return;}
  var endpoint,body;
  if(field==='__deadline__'){
    endpoint='/api/deadline';
    body={matter:matter,id:'intake-'+Date.now(),date:item.value,instruction:item.text};
  } else {
    endpoint='/api/store';
    body={matter:matter,field:field,value:item.value};
  }
  fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)})
  .then(function(r){return r.json()})
  .then(function(data){
    if(data.ok){card.classList.add('stored');
      card.innerHTML+='<span class="sm s-ok">Stored ('+data.rung+')</span>';}
    else{card.innerHTML+='<span class="sm s-err">'+esc(data.error||'Failed')+'</span>';}
  })
  .catch(function(){card.innerHTML+='<span class="sm s-err">Error</span>';});
}

function loadQueue() {
  var div=document.getElementById('qlist');
  div.innerHTML='<p class="empty">Loading&#8230;</p>';
  fetch('/api/queue').then(function(r){return r.json()}).then(function(data){
    if(!data.items.length){div.innerHTML='<p class="empty">Nothing due.</p>';return;}
    var html='';
    data.items.forEach(function(item){
      var cls='u-later',txt='';
      if(item.gap){cls='u-over';txt='date unreadable';}
      else if(item.overdue){cls='u-over';txt=Math.abs(item.days_until)+'d overdue';}
      else if(item.days_until<=14){cls='u-soon';txt='in '+item.days_until+'d';}
      else{txt='in '+item.days_until+'d';}
      html+='<div class="qi">'
        +'<span class="rb r-'+esc(item.rung)+'">'+esc(item.rung)+'</span>'
        +'<span class="qs">'+esc(item.shown)+'</span>'
        +'<span class="qu '+cls+'">'+esc(txt)+'</span>'
        +'</div>';
    });
    div.innerHTML=html;
  }).catch(function(){div.innerHTML='<p class="sm s-err">Failed to load queue</p>';});
}

function doResolve() {
  var domain=document.getElementById('edom').value;
  var query=document.getElementById('eqry').value.trim();
  if(!query) return;
  var div=document.getElementById('eres');
  div.innerHTML='<p class="empty">Resolving&#8230;</p>';
  fetch('/api/resolve?domain='+encodeURIComponent(domain)+'&surface='+encodeURIComponent(query))
  .then(function(r){return r.json()}).then(function(data){
    if(data.error){div.innerHTML='<p class="sm s-err">'+esc(data.error)+'</p>';return;}
    var r=data.result, html='<div class="rr">';
    html+='<p><strong>Query:</strong> '+esc(query)+'</p>';
    if(r.sealed){
      html+='<p><strong>Canonical:</strong> '+esc(r.canonical)
        +' <span class="os sealed">sealed</span></p>';
      html+='<p><strong>Confidence:</strong> '+r.confidence.toFixed(2)+'</p>';
      if(r.provenance&&r.provenance.verifier)
        html+='<p><strong>Verified by:</strong> '+esc(r.provenance.verifier)+'</p>';
    } else if(r.provenance&&r.provenance.suggestion){
      html+='<p><strong>Suggestion:</strong> '+esc(r.provenance.suggestion)
        +' <span class="os draft">draft</span></p>';
      html+='<p><strong>Confidence:</strong> '+r.confidence.toFixed(2)+'</p>';
      html+='<p style="color:var(--text-2)">Not sealed &#8212; seal with <code>nestor ui</code></p>';
    } else {
      html+='<p class="empty">No match found.</p>';
    }
    html+='</div>';
    div.innerHTML=html;
  }).catch(function(){div.innerHTML='<p class="sm s-err">Failed to resolve</p>';});
}

function loadOrders() {
  var div=document.getElementById('olist');
  div.innerHTML='<p class="empty">Loading&#8230;</p>';
  fetch('/api/orders').then(function(r){return r.json()}).then(function(data){
    if(!data.decisions||!data.decisions.length){
      div.innerHTML='<p class="empty">No court orders recorded.</p>';return;}
    var html='';
    data.decisions.forEach(function(d,i){
      var sc=d.status==='sealed'?'sealed':'draft';
      html+='<div class="oi">'
        +'<div class="oq">'+(i+1)+'. '+esc(d.question)+'</div>'
        +'<div class="oc">&rarr; '+esc(d.commitment)+'</div>'
        +'<span class="os '+sc+'">'+esc(d.status)+'</span>'
        +'</div>';
    });
    div.innerHTML=html;
  }).catch(function(){div.innerHTML='<p class="sm s-err">Failed to load orders</p>';});
}
</script>
</body>
</html>
"""


# ── server ────────────────────────────────────────────────────────────────

def build_server(*, host: str = "127.0.0.1", port: int = 8383):
    """Bind the UI's ``HTTPServer`` on ``host:port`` and return it, unserved.

    Everything the handlers need is bound here — the household root, the
    sidecar, the (optional) Nestor seam — so ``serve()`` and a test share one
    construction. ``port=0`` asks the OS for a free port; read it back from
    ``server.server_address``.
    """
    import datetime as dt
    import http.server
    import json
    import urllib.parse

    from homestead.keep import paths
    from homestead.keep.rungs import Disposition, derived_of
    from homestead.keep.store import InvalidKey, RecordExists
    from homestead_law import instances
    from homestead_law import nestor_seam
    from homestead_law import queue as queue_mod
    from homestead_law.app import advisories
    from homestead_law.app.window import Window
    from homestead_law.intake import extract
    from homestead_law.jurisdiction import (
        JurisdictionAbsent,
        UnsupportedJurisdiction,
        jurisdiction_of,
        set_jurisdiction,
    )
    from homestead_law.nestor_store import get_store
    from homestead_law.registry import all_matters, matter
    from homestead_law.store import Sidecar

    root = paths.home()
    root.mkdir(parents=True, exist_ok=True)
    (root / "keep").mkdir(parents=True, exist_ok=True)

    nestor_ok = nestor_seam.bind(root) is not None

    sidecar = Sidecar()

    class _H(http.server.BaseHTTPRequestHandler):

        def log_message(self, fmt, *args):
            pass

        def _json(self, obj, status=200):
            body = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _html(self, content):
            body = content.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            """The decoded JSON object of a POST, or ``_BadRequest``.

            Every step refuses rather than raises through: an absent or
            unreadable ``Content-Length``, a body over ``MAX_BODY_BYTES``, a
            short read, bytes that are not UTF-8 JSON, and JSON that is not an
            object.  Before this, a malformed body reached ``json.loads``
            unguarded and the handler died with a traceback on the console and
            a reset connection instead of a 400.
            """
            raw = self.headers.get("Content-Length")
            if raw is None:
                return {}
            try:
                n = int(raw)
            except (TypeError, ValueError):
                raise _BadRequest("Content-Length is not a number")
            if n < 0:
                raise _BadRequest("Content-Length is negative")
            if n > MAX_BODY_BYTES:
                raise _BadRequest(
                    f"the request body is larger than {MAX_BODY_BYTES} bytes", 413
                )
            if n == 0:
                return {}
            data = self.rfile.read(n)
            if len(data) != n:
                raise _BadRequest("the request body ended before Content-Length")
            try:
                body = json.loads(data)
            except (UnicodeDecodeError, ValueError):
                raise _BadRequest("the request body is not readable JSON")
            if not isinstance(body, dict):
                raise _BadRequest("the request body must be a JSON object")
            return body

        # ── GET ───────────────────────────────────────────────────────

        def do_GET(self):
            p = urllib.parse.urlparse(self.path)
            qs = dict(urllib.parse.parse_qsl(p.query))

            if p.path == "/":
                return self._html(_PAGE)
            if p.path == "/api/status":
                return self._json({"nestor": nestor_ok, "matters": list(all_matters())})
            if p.path == "/api/matters":
                return self._get_matters()
            if p.path == "/api/instances":
                return self._get_instances(qs)
            if p.path == "/api/records":
                return self._get_records(qs)
            if p.path == "/api/record":
                return self._get_record(qs)
            if p.path == "/api/queue":
                return self._get_queue()
            if p.path == "/api/resolve":
                return self._get_resolve(qs)
            if p.path == "/api/orders":
                return self._get_orders()
            self.send_error(404)

        def _get_matters(self):
            # The registry, live (I-23) — the form's matter and field lists
            # come from the packs, never from a copy kept in this file.
            out = []
            for name in all_matters():
                mt = matter(name)
                out.append({
                    "name": name,
                    "jurisdiction": mt.jurisdiction,
                    "jurisdictions": list(mt.jurisdictions),
                    "fields": [
                        {"name": f, "rung": rung.value, "why": mt.schema[f].get("why", "")}
                        for f, rung in mt.fields.items()
                    ],
                })
            self._json({"matters": out})

        def _get_instances(self, qs):
            """`GET /api/instances?matter=` — this matter's instances, each
            with its jurisdiction code (or `None` if unset) — codes only,
            never a payload: an instance id is a reference (I-15), and a
            jurisdiction code is the pack's own L1 public-forum field, read
            through the same gate every other reader in this module uses."""
            matter_name = qs.get("matter", "")
            try:
                matter(matter_name)
            except KeyError:
                return self._json({"error": f"unknown matter {matter_name!r}"}, 400)
            try:
                found = instances.instances_of(sidecar, matter_name)
            except instances.UnreadableStoredId as exc:
                return self._json({"error": str(exc)}, 400)
            out = []
            for inst in found:
                try:
                    code = jurisdiction_of(sidecar, matter_name, inst)
                except JurisdictionAbsent:
                    code = None
                out.append({"id": inst, "jurisdiction": code})
            self._json({"instances": out})

        def _get_records(self, qs):
            matter_name = qs.get("matter", "")
            try:
                matter(matter_name)
            except KeyError:
                return self._json({"error": f"unknown matter {matter_name!r}"}, 400)
            # Composed through the gate exactly as the window's list pane is:
            # L1–L3 render, L4 shows its derived form, L5 leaves no row.
            window = Window()
            rows = window.open_list(sidecar.records(matter_name))
            self._json({"rows": [
                {"matter": r.ref[0], "item_type": r.ref[1], "item_id": r.ref[2],
                 "rung": r.rung.value, "text": r.text}
                for r in rows
            ]})

        def _get_record(self, qs):
            matter_name = qs.get("matter", "")
            item_type = qs.get("item_type", "")
            item_id = qs.get("item_id", "primary")
            try:
                matter(matter_name)
            except KeyError:
                return self._json({"error": f"unknown matter {matter_name!r}"}, 400)
            ref = (matter_name, item_type, item_id)
            try:
                if not sidecar.has(*ref):
                    return self._json({"error": "no such record"}, 404)
            except InvalidKey as exc:
                # The engine's key validation, surfaced as a refusal. `str(exc)`
                # names the component and echoes what the caller typed — never a
                # stored value (I-15).
                return self._json({"error": str(exc)}, 400)
            window = Window()
            window.open_list(sidecar.records(matter_name))
            served = window.open_detail(ref)
            rendered = served.disposition is Disposition.RENDER
            self._json({
                "rung": served.rung.value,
                "rendered": rendered,
                "value": served.value if rendered else None,
                "advisories": list(advisories.advisory_lines(sidecar, ref)),
            })

        def _get_queue(self):
            today = dt.date.today().isoformat()
            items = queue_mod.queue(sidecar, today=today)
            self._json({"items": [
                {"matter": i.matter, "instance": i.instance, "rung": i.rung.value,
                 "shown": i.shown, "overdue": i.overdue, "days_until": i.days_until,
                 "gap": i.gap}
                for i in items
            ]})

        def _get_resolve(self, qs):
            if not nestor_ok:
                return self._json({"error": "nestor-meaning not installed"}, 503)
            domain = qs.get("domain", "party")
            surface = qs.get("surface", "")
            if not surface:
                return self._json({"error": "surface is required"}, 400)
            valid = ("party", "court", "citation", "jurisdiction")
            if domain not in valid:
                return self._json({"error": f"unknown domain {domain!r}"}, 400)
            try:
                store = get_store()
                resolver = nestor_seam.resolver_for(domain, store)
                result = resolver.resolve(surface)
                self._json({"result": result})
            except Exception:
                # The failure is named by *where* it happened, not by the
                # exception's text (I-15). Nestor's store holds the household's
                # own party and court names, so an exception message from it can
                # carry one — `str(exc)` in a JSON body is a value crossing a
                # surface that never scored it.
                self._json(
                    {"error": f"the {domain} resolver could not be read"}, 500)

        def _get_orders(self):
            if not nestor_ok:
                return self._json({"decisions": []})
            try:
                store = get_store()
                dm = nestor_seam.decisions_for("court", store)
                decisions = dm.all_decisions()
                self._json({"decisions": [
                    {"question": d.get("source_text", "?"),
                     "commitment": d.get("target_text", "?"),
                     "status": d.get("status", "draft")}
                    for d in decisions
                ]})
            except Exception:
                # References, never content (I-15) — see `_get_resolve`.
                self._json(
                    {"decisions": [], "error": "the decision store could not be read"})

        # ── POST ──────────────────────────────────────────────────────

        def do_POST(self):
            p = urllib.parse.urlparse(self.path).path
            try:
                body = self._body()
                if p == "/api/extract":
                    return self._post_extract(body)
                if p == "/api/store":
                    return self._post_store(body)
                if p == "/api/deadline":
                    return self._post_deadline(body)
                if p == "/api/deadline/compute":
                    return self._post_deadline_compute(body)
                if p == "/api/deadline/accept":
                    return self._post_deadline_accept(body)
                if p == "/api/matter/open":
                    return self._post_matter_open(body)
            except _BadRequest as exc:
                # An unread body (a refused Content-Length) leaves bytes on the
                # socket, so this connection does not get reused — and the
                # bytes are drained first, or the close becomes a reset.
                self.close_connection = True
                self._json({"ok": False, "error": str(exc)}, exc.status)
                _drain(self.connection)
                return
            self.send_error(404)

        def _post_extract(self, body):
            text = _text(body, "text")
            items = extract(text)
            self._json({"items": [
                {"kind": e.kind, "text": e.text, "value": e.value,
                 "start": e.start, "end": e.end, "field": e.field}
                for e in items
            ]})

        def _post_store(self, body):
            from homestead.keep.rungs import Classified

            # No default matter. A matter name written down outside the registry
            # is BUG-6's shape, and defaulting here would file a bankruptcy
            # record under custody without ever saying so (I-11: refuse by name,
            # never default).
            matter_name = _text(body, "matter").strip()
            field = _text(body, "field").strip()
            value = _text(body, "value").strip()
            # `id` names the instance (default `primary`, unchanged from before
            # this bite); `sub` is only for a field the pack declares
            # REPEATABLE.
            id_value = _text(body, "id", instances.DEFAULT_INSTANCE).strip() or instances.DEFAULT_INSTANCE
            sub_value = _text(body, "sub").strip() or None

            if not matter_name:
                return self._json(
                    {"ok": False, "error": "a matter is required"}, 400)
            try:
                mt = matter(matter_name)
            except KeyError:
                return self._json(
                    {"ok": False, "error": f"unknown matter {matter_name!r}"}, 400)

            if field not in mt.fields:
                return self._json(
                    {"ok": False, "error": f"unknown field {field!r}"}, 400)

            if not value:
                return self._json({"ok": False, "error": "a value is required"}, 400)

            if sub_value is not None and field not in mt.repeatable:
                return self._json(
                    {"ok": False, "error": f"field {field!r} does not accept a sub id"}, 400)

            try:
                item_id = instances.item_id(id_value, sub_value)
            except instances.InvalidId as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)

            rung = mt.fields[field]
            # The pack's own declaration (decision 3), not a second table — see
            # cli.py's `_cmd_put`, which reads the same function on the same pack.
            derived = derived_of(mt.schema, field) if rung.value in ("L3", "L4") else None
            item = Classified(rung, value, derived)
            try:
                replaced = sidecar.put(matter_name, field, item_id, item, overwrite=True)
            except InvalidKey as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)

            if field in ("opposing_party", "child_name") and nestor_ok:
                try:
                    store = get_store()
                    resolver = nestor_seam.resolver_for("party", store)
                    resolver.propose(value, value, reason=f"entered as {field}")
                except Exception:
                    pass

            self._json({"ok": True, "rung": rung.value, "replaced": replaced is not None})

        def _post_deadline(self, body):
            from homestead.keep.dates import UnparseableDate, parse_deadline
            from homestead.keep.rungs import Classified, Rung

            # No default matter here either — see `_post_store`.
            matter_name = _text(body, "matter").strip()
            id_value = _text(body, "id").strip()
            # Every deadline is addressed to an instance (decision 2): what is
            # stored is always `instances.item_id(instance, name)`. Unset,
            # `sub` leaves `id` as the deadline's *name* under the default
            # instance — `primary.<id>`, so the page's existing form is
            # unchanged — and given, `id` names the instance and `sub` the
            # deadline within it. A free-form id is refused, never stored:
            # `instances_of` is a key scan, and an id it cannot split is a
            # phantom instance no door can address.
            sub_value = _text(body, "sub").strip() or None
            date = _text(body, "date").strip()
            instruction = _text(body, "instruction").strip() or None
            rung_value = _text(body, "rung", "L1").strip() or "L1"

            if not matter_name:
                return self._json(
                    {"ok": False, "error": "a matter is required"}, 400)
            try:
                matter(matter_name)
            except KeyError:
                return self._json(
                    {"ok": False, "error": f"unknown matter {matter_name!r}"}, 400)
            if not id_value:
                return self._json({"ok": False, "error": "an id is required"}, 400)
            instance, name = (
                (id_value, sub_value) if sub_value is not None
                else (instances.DEFAULT_INSTANCE, id_value)
            )
            try:
                item_id = instances.item_id(instance, name)
            except instances.InvalidId as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
            try:
                rung = Rung(rung_value)
            except ValueError:
                return self._json({"ok": False, "error": f"unknown rung {rung_value!r}"}, 400)
            if rung is Rung.L5:
                return self._json(
                    {"ok": False, "error": "an L5 deadline would never appear on the queue"}, 400)
            # The one strict parser (BUG-1): a date the queue could not read
            # is refused here, where the operator can fix it, not stored as a
            # gap they will meet later.
            try:
                date = parse_deadline(date).iso
            except UnparseableDate as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
            if rung in (Rung.L3, Rung.L4) and not instruction:
                instruction = "A deadline is on file"

            item = Classified(rung, date, instruction)
            try:
                sidecar.put(matter_name, "deadline", item_id, item, overwrite=True)
            except InvalidKey as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
            self._json({"ok": True, "rung": rung.value})

        def _post_deadline_compute(self, body):
            """`POST /api/deadline/compute` `{matter, id, template, mail?}` —
            L3-deadline-templates' preview door. **Stores nothing**; `id`
            names the instance, the same field `_post_deadline` already uses
            that way. On success, `rules.Computed`'s own fields plus the
            preview token; on refusal, a 400 naming what failed (I-15 — every
            refusal `rules.compute` raises names a field, never an anchor
            value above L1 or a jurisdiction planted outside the gate)."""
            from homestead.keep.dates import UnparseableDate
            from homestead_law import rules
            from homestead_law.jurisdiction import JurisdictionAbsent

            matter_name = _text(body, "matter").strip()
            id_value = _text(body, "id").strip()
            template_name = _text(body, "template").strip()
            mail = body.get("mail", False)
            if not isinstance(mail, bool):
                raise _BadRequest("mail must be true or false")

            if not matter_name:
                return self._json({"ok": False, "error": "a matter is required"}, 400)
            try:
                matter(matter_name)
            except KeyError:
                return self._json(
                    {"ok": False, "error": f"unknown matter {matter_name!r}"}, 400)
            if not id_value:
                return self._json({"ok": False, "error": "an id is required"}, 400)
            if not template_name:
                return self._json({"ok": False, "error": "a template is required"}, 400)

            try:
                computed = rules.compute(
                    sidecar, matter_name, id_value, template_name, mail=mail)
            except (
                instances.InvalidId,
                JurisdictionAbsent,
                UnparseableDate,
                rules.TemplateNotFound,
                rules.AnchorUnavailable,
                rules.TemplateJurisdictionMismatch,
                rules.UncertainTemplate,
                rules.MailUnsupported,
            ) as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)

            self._json({
                "ok": True,
                "matter": computed.matter,
                "instance": computed.instance,
                "template": computed.template,
                "anchor_field": computed.anchor_field,
                "anchor_iso": computed.anchor_iso,
                "result_iso": computed.result_iso,
                "source": computed.source,
                "jurisdiction": computed.jurisdiction,
                "mail": computed.mail,
                "token": computed.preview_token,
            })

        def _post_deadline_accept(self, body):
            """`POST /api/deadline/accept` `{matter, id, template, token,
            mail?, replace?}` — recomputes fresh (the same `mail` the preview
            was shown with) and compares `token` against *that*
            computation's own `preview_token`, so a token minted against an
            anchor or a jurisdiction that has since changed is refused by
            name (`rules.StaleToken`) rather than accepted against content
            the browser never actually saw."""
            from homestead.keep.dates import UnparseableDate
            from homestead_law import rules
            from homestead_law.jurisdiction import JurisdictionAbsent
            from homestead_law.store import RecordExists

            matter_name = _text(body, "matter").strip()
            id_value = _text(body, "id").strip()
            template_name = _text(body, "template").strip()
            token = _text(body, "token").strip()
            mail = body.get("mail", False)
            if not isinstance(mail, bool):
                raise _BadRequest("mail must be true or false")
            replace = body.get("replace", False)
            if not isinstance(replace, bool):
                raise _BadRequest("replace must be true or false")

            if not matter_name:
                return self._json({"ok": False, "error": "a matter is required"}, 400)
            try:
                matter(matter_name)
            except KeyError:
                return self._json(
                    {"ok": False, "error": f"unknown matter {matter_name!r}"}, 400)
            if not id_value:
                return self._json({"ok": False, "error": "an id is required"}, 400)
            if not template_name:
                return self._json({"ok": False, "error": "a template is required"}, 400)
            if not token:
                return self._json({"ok": False, "error": "a token is required"}, 400)

            try:
                computed = rules.compute(
                    sidecar, matter_name, id_value, template_name, mail=mail)
            except (
                instances.InvalidId,
                JurisdictionAbsent,
                UnparseableDate,
                rules.TemplateNotFound,
                rules.AnchorUnavailable,
                rules.TemplateJurisdictionMismatch,
                rules.UncertainTemplate,
                rules.MailUnsupported,
            ) as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)

            try:
                replaced = rules.accept(
                    sidecar, computed, token=token, replace=replace)
            except rules.StaleToken as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
            except RecordExists:
                return self._json(
                    {"ok": False,
                     "error": f"{matter_name}/{id_value}.{template_name} is "
                              "already on file — pass replace to overwrite it"},
                    409,
                )
            self._json({"ok": True, "replaced": replaced is not None})

        def _post_matter_open(self, body):
            """`POST /api/matter/open` `{matter, id, jurisdiction, replace?}` —
            declare an instance's jurisdiction, opening it (decision 1). No
            default matter or id (I-11); a `jurisdiction` outside the pack's
            own set is refused by name, never a guess."""
            matter_name = _text(body, "matter").strip()
            id_value = _text(body, "id").strip()
            jurisdiction_value = _text(body, "jurisdiction").strip()
            replace = body.get("replace", False)
            if not isinstance(replace, bool):
                # The same refusal `_text` makes for a coerced string: `replace`
                # is the operator's consent to overwrite (I-9), and
                # `bool("false")` is `True`. A surface that coerces has decided
                # something the operator did not say.
                raise _BadRequest("replace must be true or false")

            if not matter_name:
                return self._json(
                    {"ok": False, "error": "a matter is required"}, 400)
            try:
                matter(matter_name)
            except KeyError:
                return self._json(
                    {"ok": False, "error": f"unknown matter {matter_name!r}"}, 400)
            if not id_value:
                return self._json({"ok": False, "error": "an id is required"}, 400)
            if not jurisdiction_value:
                return self._json(
                    {"ok": False, "error": "a jurisdiction is required"}, 400)

            try:
                replaced = set_jurisdiction(
                    sidecar, matter_name, id_value, jurisdiction_value, replace=replace
                )
            except instances.InvalidId as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
            except UnsupportedJurisdiction as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
            except RecordExists:
                return self._json(
                    {"ok": False,
                     "error": f"{matter_name}/{id_value} is already open — pass "
                              "replace to change its jurisdiction"},
                    409,
                )
            self._json({"ok": True, "replaced": replaced is not None})

    return http.server.HTTPServer((host, port), _H)


def serve(*, host: str = "127.0.0.1", port: int = 8383) -> None:
    """Start the UI on localhost, open a browser on it, and block until Ctrl+C."""
    import webbrowser

    srv = build_server(host=host, port=port)
    url = f"http://{host}:{srv.server_address[1]}"
    print(f"  homestead-law ui: {url}")
    print("  press Ctrl+C to stop")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        print("\n  stopped")
