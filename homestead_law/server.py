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

function loadMatters() {
  return fetch('/api/matters').then(function(r){return r.json()}).then(function(data){
    _matters={};
    var sel=document.getElementById('rmatter'); sel.innerHTML='';
    data.matters.forEach(function(m){
      _matters[m.name]=m;
      var o=document.createElement('option'); o.value=m.name; o.textContent=m.name; sel.appendChild(o);
    });
    fillFields();
  });
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
  var matter=document.getElementById('rmatter').value;
  var field=document.getElementById('rfield').value;
  var value=document.getElementById('rvalue').value.trim();
  var msg=document.getElementById('rmsg');
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
  var matter=document.getElementById('rmatter').value;
  var id=document.getElementById('did').value.trim();
  var date=document.getElementById('ddate').value.trim();
  var rung=document.getElementById('drung').value;
  var instr=document.getElementById('dinstr').value.trim();
  var msg=document.getElementById('dmsg');
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
  var matter=document.getElementById('rmatter').value;
  var div=document.getElementById('rlist');
  document.getElementById('rdetail').innerHTML='';
  if(!matter){div.innerHTML='';return;}
  fetch('/api/records?matter='+encodeURIComponent(matter)).then(function(r){return r.json()}).then(function(data){
    if(!data.rows||!data.rows.length){
      div.innerHTML='<p class="empty">Nothing on file for '+esc(matter)+' yet.</p>';return;}
    var html='';
    data.rows.forEach(function(row){
      var where=row.item_id==='primary'?row.item_type:row.item_type+' / '+row.item_id;
      html+='<div class="qi rw" onclick="openRecord(\''+esc(row.matter)+'\',\''+esc(row.item_type)+'\',\''+esc(row.item_id)+'\')">'
        +'<span class="rb r-'+row.rung+'">'+row.rung+'</span>'
        +'<span class="rk">'+esc(where.replace(/_/g,' '))+'</span>'
        +'<span class="qs">'+esc(row.text)+'</span>'
        +'</div>';
    });
    div.innerHTML=html;
  }).catch(function(){div.innerHTML='<p class="sm s-err">Failed to load records</p>';});
}

function openRecord(matter,item_type,item_id) {
  var div=document.getElementById('rdetail');
  fetch('/api/record?matter='+encodeURIComponent(matter)+'&item_type='+encodeURIComponent(item_type)
    +'&item_id='+encodeURIComponent(item_id)).then(function(r){return r.json()}).then(function(data){
    if(data.error){div.innerHTML='<p class="sm s-err">'+esc(data.error)+'</p>';return;}
    var html='<div class="dt"><strong>'+esc(item_type.replace(/_/g,' '))+'</strong> '
      +'<span class="rb r-'+data.rung+'">'+data.rung+'</span><div>'
      +(data.rendered?esc(data.value):'This record is sealed and is not shown here.')+'</div>';
    (data.advisories||[]).forEach(function(a){html+='<div class="adv">'+esc(a)+'</div>';});
    html+='</div>';
    div.innerHTML=html;
  });
}

loadMatters().then(loadRecords);

function esc(s) {
  var d=document.createElement('div'); d.textContent=s; return d.innerHTML;
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
      +'<span class="kb k-'+item.kind+'">'+item.kind.replace('_',' ')+'</span>'
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
  var endpoint,body;
  if(field==='__deadline__'){
    endpoint='/api/deadline';
    body={matter:document.getElementById('rmatter').value||'custody',id:'intake-'+Date.now(),date:item.value,instruction:item.text};
  } else {
    endpoint='/api/store';
    body={matter:document.getElementById('rmatter').value||'custody',field:field,value:item.value};
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
        +'<span class="rb r-'+item.rung+'">'+item.rung+'</span>'
        +'<span class="qs">'+esc(item.shown)+'</span>'
        +'<span class="qu '+cls+'">'+txt+'</span>'
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
        +'<span class="os '+sc+'">'+d.status+'</span>'
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
    from homestead.keep.rungs import Disposition
    from homestead_law import nestor_seam
    from homestead_law import queue as queue_mod
    from homestead_law.app import advisories
    from homestead_law.app.window import Window
    from homestead_law.intake import extract
    from homestead_law.nestor_store import get_store
    from homestead_law.registry import all_matters, matter
    from homestead_law.store import Sidecar

    root = paths.home()
    root.mkdir(parents=True, exist_ok=True)
    (root / "keep").mkdir(parents=True, exist_ok=True)

    nestor_ok = nestor_seam.bind(root) is not None

    sidecar = Sidecar()

    def _derived(field: str, value: str) -> str:
        table = {
            "case_number": "A case number is on file",
            "docket": "A docket entry is on file",
            "opposing_party": "The other parent is named",
            "parenting_time": "A parenting-time obligation is on file",
            "child_name": "A minor child is named in this matter",
            "diagnosis": "A medical category is on file for a person",
            "notes": "An operator note is on file",
        }
        return table.get(field, f"A {field.replace('_', ' ')} is on file")

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
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n)) if n else {}

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
                    "fields": [
                        {"name": f, "rung": rung.value, "why": mt.schema[f].get("why", "")}
                        for f, rung in mt.fields.items()
                    ],
                })
            self._json({"matters": out})

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
                ref = (matter_name, item_type, item_id)
                if not sidecar.has(*ref):
                    return self._json({"error": "no such record"}, 404)
            except (KeyError, ValueError) as exc:
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
                {"matter": i.matter, "rung": i.rung.value, "shown": i.shown,
                 "overdue": i.overdue, "days_until": i.days_until, "gap": i.gap}
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
            except Exception as exc:
                self._json({"error": str(exc)}, 500)

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
            except Exception as exc:
                self._json({"decisions": [], "error": str(exc)})

        # ── POST ──────────────────────────────────────────────────────

        def do_POST(self):
            p = urllib.parse.urlparse(self.path).path
            body = self._body()

            if p == "/api/extract":
                return self._post_extract(body)
            if p == "/api/store":
                return self._post_store(body)
            if p == "/api/deadline":
                return self._post_deadline(body)
            self.send_error(404)

        def _post_extract(self, body):
            text = body.get("text", "")
            items = extract(text)
            self._json({"items": [
                {"kind": e.kind, "text": e.text, "value": e.value,
                 "start": e.start, "end": e.end, "field": e.field}
                for e in items
            ]})

        def _post_store(self, body):
            from homestead.keep.rungs import Classified, Rung

            matter_name = body.get("matter", "custody")
            field = body.get("field", "")
            value = body.get("value", "")

            try:
                mt = matter(matter_name)
            except KeyError:
                return self._json(
                    {"ok": False, "error": f"unknown matter {matter_name!r}"}, 400)

            if field not in mt.fields:
                return self._json(
                    {"ok": False, "error": f"unknown field {field!r}"}, 400)

            value = str(value).strip()
            if not value:
                return self._json({"ok": False, "error": "a value is required"}, 400)

            rung = mt.fields[field]
            derived = _derived(field, value) if rung.value in ("L3", "L4") else None
            item = Classified(rung, value, derived)
            replaced = sidecar.put(matter_name, field, "primary", item, overwrite=True)

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
            from homestead.keep.store import InvalidKey

            matter_name = body.get("matter", "custody")
            item_id = str(body.get("id", "")).strip()
            date = str(body.get("date", "")).strip()
            instruction = body.get("instruction") or None
            rung_value = body.get("rung", "L1")

            try:
                matter(matter_name)
            except KeyError:
                return self._json(
                    {"ok": False, "error": f"unknown matter {matter_name!r}"}, 400)
            if not item_id:
                return self._json({"ok": False, "error": "an id is required"}, 400)
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

    return http.server.HTTPServer((host, port), _H)


def serve(*, host: str = "127.0.0.1", port: int = 8383) -> None:
    """Start the UI on localhost, open a browser on it, and block until Ctrl+C."""
    import webbrowser

    srv = build_server(host=host, port=port)
    url = f"http://{host}:{srv.server_address[1]}"
    print(f"  homestead-law ui: {url}")
    print(f"  press Ctrl+C to stop")

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
