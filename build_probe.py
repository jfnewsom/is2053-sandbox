"""Build the IS2053 Canvas iframe probe from a lab JSON.

Navigation test only. Content is rendered plainly from the real JSON so tab
heights are realistic; visual design is NOT the point of this page.

Usage: python3 build_probe.py path/to/lab-1-3.json out/lab-1-3.html
"""
import html
import json
import sys

HELP_VARIANTS = {"info", "pitfall", "tip", "bookex", "strategy"}


def label(s):
    return " ".join(w.capitalize() for w in s.replace("youre", "you're").split("_"))


def block(b):
    t = b["type"]
    if t == "h3":
        return f'<h3>{html.escape(label(b.get("label", b.get("text", ""))))}</h3>'
    if t == "text":
        return f'<p>{b.get("body", "")}</p>'
    if t == "instructions":
        return "<ol>" + "".join(f"<li>{i}</li>" for i in b["items"]) + "</ol>"
    if t == "table":
        head = "".join(f"<th>{h}</th>" for h in b["headers"])
        rows = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in b["rows"])
        return f'<div class="tw"><table><tr>{head}</tr>{rows}</table></div>'
    if t == "code_block":
        return f'<pre class="code">{html.escape(b["code"])}</pre>'
    if t == "output_block":
        return f'<pre class="out">{html.escape(b["output"])}</pre>'
    if t == "mentor_quote":
        return f'<blockquote><p>{b["quote"]}</p><cite>{html.escape(b["character"])}</cite></blockquote>'
    if t == "callout":
        return f'<div class="warn"><b>{b.get("title", "")}</b><p>{b.get("body", "")}</p></div>'
    return ""


def checkpoint(cp):
    main, cards = [], []
    for b in cp["content"]:
        if b["type"] == "callout" and b.get("variant") in HELP_VARIANTS:
            cards.append(b)
        else:
            main.append(block(b))
    row = ""
    if cards:
        row = '<div class="cards">' + "".join(
            f'<details><summary>{c.get("title", "More")}</summary><p>{c.get("body", "")}</p></details>'
            for c in cards) + "</div>"
    return "".join(main) + row


def build(d):
    ov, fc, nh = d["overview"], d["finalChecklist"], d["needHelp"]
    tabs = []
    tabs.append(("start", "Start", "path",
                 f'<p class="lead">{ov["body"]}</p><p>{ov.get("filenameNote", "")}</p>'
                 f'<h3>Before You Begin</h3><p>{d["beforeYouBegin"]["intro"]}</p>'
                 f'<pre class="code">{html.escape(d["beforeYouBegin"]["architecture"])}</pre>'))
    for cp in d["checkpoints"]:
        tabs.append((f'cp{cp["number"]}', f'CP{cp["number"]}', "path",
                     f'<p class="lead">{html.escape(cp["title"])}</p>' + checkpoint(cp)))
    tabs.append(("finish", "Finish", "path",
                 "<h3>Before You Submit</h3><ul>" + "".join(f"<li>{i}</li>" for i in fc["beforeYouSubmit"]) + "</ul>"
                 + "<h3>Expected Output</h3>"
                 + f'<pre class="out">{html.escape(fc["finalCheck"].get("expectedOutput", ""))}</pre>'
                 + "<h3>If You Get Stuck</h3><ul>" + "".join(f"<li>{i}</li>" for i in nh["ifYouGetStuck"]) + "</ul>"))
    tabs.append(("outline", "Outline", "ref",
                 "<h3>Program Requirements</h3><ul>" + "".join(f"<li>{i}</li>" for i in ov["programRequirements"]) + "</ul>"
                 + "<h3>Named Constants</h3><ul>" + "".join(
                     f'<li><code>{c["name"]}</code>: {c["description"]}</li>' for c in ov["namedConstants"]) + "</ul>"
                 + "<h3>Objectives</h3><ul>" + "".join(f"<li>{i}</li>" for i in ov["objectives"]) + "</ul>"))
    md = fc["messageDigest"]
    tabs.append(("strings", "Strings", "ref",
                 f'<p>{md["intro"]}</p><div class="tw"><table><tr><th>Purpose</th><th>Exact Text</th><th>Shown In</th></tr>'
                 + "".join(f'<tr><td>{r["purpose"]}</td><td><code class="s">{html.escape(r["text"])}</code></td>'
                           f'<td>{r.get("shownIn", "")}</td></tr>' for r in md["rows"])
                 + "</table></div>"))
    return tabs


def page(d, tabs):
    meta = d["meta"]
    path = [t for t in tabs if t[2] == "path"]
    order = [t[0] for t in path]
    buttons = "".join(
        f'<a class="tab {kind}" role="tab" href="#{tid}" data-tab="{tid}">{name}</a>' for tid, name, kind, _ in tabs)
    panels = ""
    for tid, name, kind, body in tabs:
        i = order.index(tid) if tid in order else None
        back = nxt = ""
        if i is not None and i > 0:
            p = path[i - 1]
            back = f'<a class="back" href="#{p[0]}" data-tab="{p[0]}">&larr; Back: {p[1]}</a>'
        if i is not None and i < len(path) - 1:
            n = path[i + 1]
            nxt = f'<a class="next" href="#{n[0]}" data-tab="{n[0]}">Next: {n[1]} &rarr;</a>'
        panels += (f'<section class="panel" id="p-{tid}" data-tab="{tid}" hidden>'
                   f'<div class="topnav">{back}</div>'
                   f'<h2><span class="kw">lab {meta["labId"][4:].replace("-", ".")}</span> {name}</h2>'
                   f'{body}<div class="botnav">{nxt}</div></section>')
    return TEMPLATE.replace("{{TITLE}}", html.escape(meta["title"])) \
        .replace("{{TABS}}", buttons).replace("{{PANELS}}", panels) \
        .replace("{{DEFAULT}}", order[0])


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Probe: {{TITLE}}</title>
<style>
:root{--bg:#0a0a0a;--text:#f5f5f5;--muted:#b0b8c4;--accent:#ffcc00;--ref:#39b2ff;--line:#2a2a2a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 Roboto,system-ui,sans-serif}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);display:flex;align-items:stretch}
.scroller{position:relative;flex:1;min-width:0}
.tabs{display:flex;gap:4px;overflow-x:auto;scroll-behavior:smooth;scrollbar-width:thin;padding:8px 8px 0}
.tab{flex:0 0 auto;padding:8px 14px;color:var(--muted);text-decoration:none;border-radius:6px 6px 0 0;font-weight:600;white-space:nowrap}
.tab.ref{color:var(--ref);font-weight:400}
.tab.ref:first-of-type{margin-left:auto}
.tab.path+.tab.ref{margin-left:18px;border-left:1px solid var(--line)}
.tab[aria-selected=true]{background:var(--accent);color:#000}
.tab.ref[aria-selected=true]{background:var(--ref);color:#000}
.fade{position:absolute;top:0;bottom:0;width:40px;display:none;align-items:center;justify-content:center;border:0;cursor:pointer;color:var(--accent);font-size:22px;font-weight:700}
.fade.l{left:0;background:linear-gradient(90deg,var(--bg) 55%,transparent)}
.fade.r{right:0;background:linear-gradient(270deg,var(--bg) 55%,transparent)}
.fade.on{display:flex}
.newtab{flex:0 0 auto;align-self:center;margin:0 8px;color:var(--muted);font-size:13px;white-space:nowrap}
.panel{padding:12px 20px 32px;max-width:900px}
.topnav,.botnav{min-height:24px}
.back,.next{display:inline-block;font-weight:700;color:var(--accent);text-decoration:none;padding:8px 0}
.botnav{margin-top:24px;border-top:1px solid var(--line);text-align:right}
.next{font-size:18px}
h2{margin:4px 0 12px;font-size:24px}.kw{color:var(--muted);font-weight:400;margin-right:6px}
.lead{font-size:20px}
pre{background:#000;border:1px solid var(--line);padding:10px;overflow-x:auto;font:13px/1.4 "Roboto Mono",monospace}
.out{color:#39ff14}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid var(--line);padding:6px;text-align:left;vertical-align:top}
code{font-family:"Roboto Mono",monospace;color:var(--accent)}code.s{white-space:pre-wrap;background:#1a1a1a}
.warn{border-left:4px solid #ff6b1a;padding:6px 12px;margin:12px 0;background:#1a0f08}
blockquote{margin:12px 0;padding:8px 14px;border:1px solid var(--line);border-radius:12px}cite{color:var(--muted)}
.cards{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}.cards details{border:1px solid var(--line);border-radius:6px;padding:6px 10px;flex:1 1 200px}
.cards summary{cursor:pointer;color:var(--muted)}
#diag{position:fixed;left:6px;bottom:6px;pointer-events:none;opacity:.85;z-index:9;background:#111;border:1px solid #444;color:#0f0;font:11px/1.35 monospace;padding:6px 8px;white-space:pre;max-width:60vw}
</style></head><body>
<div class="bar">
  <div class="scroller">
    <button class="fade l" aria-label="More tabs to the left">&lsaquo;</button>
    <nav class="tabs" role="tablist">{{TABS}}</nav>
    <button class="fade r" aria-label="More tabs to the right">&rsaquo;</button>
  </div>
  <a class="newtab" id="newtab" href="#" target="_blank" rel="noopener" hidden>Open in new tab &#8599;</a>
</div>
<main>{{PANELS}}</main>
<div id="diag" hidden></div>
<script>
(function(){
const qs=new URLSearchParams(location.search);
// ?extra=N adds dummy CP tabs to test a long tab row
const extra=parseInt(qs.get('extra')||'0',10);
const nav=document.querySelector('.tabs');
if(extra>0){const fin=nav.querySelector('[data-tab=finish]');
  const last=[...nav.querySelectorAll('.tab.path')].filter(t=>/^cp/.test(t.dataset.tab)).length;
  for(let i=1;i<=extra;i++){const a=document.createElement('a');a.className='tab path';a.textContent='CP'+(last+i);a.href='#dummy';a.dataset.tab='finish';nav.insertBefore(a,fin);}}
const inIframe=window.self!==window.top;
const scrollPos={};let current=null;
function show(id,push){
  const p=document.getElementById('p-'+id); if(!p) id='{{DEFAULT}}';
  if(current){scrollPos[current]=window.scrollY;}
  document.querySelectorAll('.panel').forEach(s=>s.hidden=s.dataset.tab!==id);
  document.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t.dataset.tab===id&&t.getAttribute('href')==='#'+id));
  current=id;
  const act=nav.querySelector('.tab[aria-selected=true]'); if(act) act.scrollIntoView({block:'nearest',inline:'center'});
  window.scrollTo(0,scrollPos[id]||0);
  if(push) history.replaceState(null,'','#'+id);
  const nt=document.getElementById('newtab'); nt.href=location.href.split('#')[0]+'#'+id;
  fades(); diag();
}
document.addEventListener('click',e=>{const a=e.target.closest('a[data-tab]');if(!a)return;e.preventDefault();show(a.dataset.tab,true);});
const L=document.querySelector('.fade.l'),R=document.querySelector('.fade.r');
function fades(){L.classList.toggle('on',nav.scrollLeft>4);R.classList.toggle('on',nav.scrollLeft+nav.clientWidth<nav.scrollWidth-4);}
nav.addEventListener('scroll',fades);window.addEventListener('resize',()=>{fades();diag();});
L.onclick=()=>nav.scrollBy({left:-nav.clientWidth*0.7});R.onclick=()=>nav.scrollBy({left:nav.clientWidth*0.7});
if(inIframe){document.getElementById('newtab').hidden=false;}
function diag(){
  if(qs.get('diag')==='0')return; const d=document.getElementById('diag'); d.hidden=false;
  const bar=document.querySelector('.bar').getBoundingClientRect();
  d.textContent=['iframe: '+inIframe,'viewport: '+innerWidth+' x '+innerHeight,'page height: '+document.documentElement.scrollHeight,
   'window.scrollY: '+Math.round(scrollY),'tab bar top: '+Math.round(bar.top)+' (0 = pinned)','tab row overflows: '+(nav.scrollWidth>nav.clientWidth),
   'tab: '+current+'   hash: '+location.hash].join('\n');
}
window.addEventListener('scroll',diag,{passive:true});
show((location.hash||'').slice(1)||'{{DEFAULT}}',false);
})();
</script></body></html>"""

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    open(sys.argv[2], "w").write(page(data, build(data)))
    print("wrote", sys.argv[2])
