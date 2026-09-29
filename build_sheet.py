"""Build a tabbed IS2053 lab sheet (sandbox prototype) from a lab JSON.

Reuses the live site's components.py renderers and labs.css so the Bat City
look carries over; only the layout changes.

Usage:
  python3 build_sheet.py <path-to-is2053-assets> <lab-json> <out.html>
"""
import copy
import html as H
import json
import re
import sys

ASSETS_URL = "https://jfnewsom.github.io/is2053-assets/"
HELP_VARIANTS = {"info", "pitfall", "tip", "bookex", "strategy"}

sys.path.insert(0, sys.argv[1])
import components as C  # noqa: E402

TAB_COLORS = {  # tab id prefix -> card color (matches labs.css .lc-card--*)
    "start": "blue", "cp": "green", "finish": "red", "outline": "cyan", "strings": "orange",
}
ACCENT = {"blue": "#0055FF", "green": "#39FF14", "red": "#FF1744", "cyan": "#00FFFF",
          "orange": "#FF6B1A", "purple": "#BF40FF"}


def inner(card_html):
    """Return the contents of a component card's lc-panel, dropping its topper."""
    start = card_html.index('<div class="lc-panel">') + len('<div class="lc-panel">')
    end = card_html.rstrip().rfind("</div>")
    end = card_html.rfind("</div>", 0, end)
    return card_html[start:end]


def cards_row(cards):
    """cards: list of (icon_svg, title, body_html). Sideways row + one shared panel."""
    if not cards:
        return ""
    btns, panels = "", ""
    for i, (icon, title, body) in enumerate(cards):
        btns += (f'<button class="sx-card" data-i="{i}" aria-expanded="false">'
                 f'<span class="sx-card__icon">{icon}</span><span>{title}</span></button>')
        panels += f'<div class="sx-cardpanel" data-i="{i}" hidden>{body}</div>'
    return f'<div class="sx-cards"><div class="sx-cards__row">{btns}</div>{panels}</div>'


def callout_card(b):
    icon = C.CALLOUT_ICONS.get(b.get("variant", "info"), C.CALLOUT_ICONS["info"]).strip()
    return (icon, b.get("title") or "More", C.render_callout(b))


def split_sections(content):
    """Group checkpoint blocks under their h3 label."""
    out, cur = {}, "_top"
    for b in content:
        if b["type"] == "h3":
            cur = b.get("label", "")
            out.setdefault(cur, [])
        else:
            out.setdefault(cur, []).append(b)
    return out


def render_blocks(blocks, cards):
    s = ""
    for b in blocks:
        if b["type"] == "callout" and b.get("variant") in HELP_VARIANTS:
            cards.append(callout_card(b))
        else:
            s += C.render_content_item(b, card_color="green")
    return s


def h3(label):
    return C.render_h3({"label": label}, "green")


def checkpoint_body(cp):
    sec = split_sections(cp["content"])
    cards = []
    s = ""
    wyb = sec.pop("what_youre_building", [])
    if wyb and wyb[0]["type"] == "text":
        s += f'<p class="sx-lead">{wyb[0]["body"]}</p>'
        wyb = wyb[1:]
    s += render_blocks(sec.pop("_top", []) + wyb, cards)
    for label in ("why_this_matters", "step_by_step", "named_constants", "expected_output",
                  "test_your_code", "what_you_should_have"):
        if label in sec:
            s += h3(label) + render_blocks(sec.pop(label), cards)
    for label in ("bookex_patterns", "tips_and_pitfalls"):
        if label in sec:
            blocks = sec.pop(label)
            icon = C.CALLOUT_ICONS["bookex" if label == "bookex_patterns" else "pitfall"].strip()
            title = C.H3_LABELS.get(label, label.replace("_", " ").title())
            body = "".join(C.render_content_item(b, card_color="green") for b in blocks)
            cards.insert(0 if label == "bookex_patterns" else 1, (icon, title, body))
    for label, blocks in sec.items():  # anything unexpected stays visible
        s += h3(label) + render_blocks(blocks, cards)
    return s + cards_row(cards)


def header(badge_word, badge_num, title, cp=False):
    cls = "lc-cp-badge" if cp else "lc-lab-badge"
    return (f'<div class="sx-head"><div class="{cls}"><div class="{cls}__word">{badge_word}</div>'
            f'<div class="{cls}__num">{badge_num}</div></div>'
            f'<div class="lc-topper-title">{H.escape(title)}</div>'
            f'<img class="sx-logo" src="{ASSETS_URL}branding/BatCity-logo-3D.png" alt="Bat City Collective"></div>')


def build(d):
    meta, ov, fc, nh = d["meta"], d["overview"], d["finalChecklist"], d["needHelp"]
    labnum = meta["labId"][4:].replace("-", ".")
    tabs = []

    # Start
    cards = []
    if d.get("timeGuide"):
        cards.append((C.CALLOUT_ICONS["clock"].strip(), "Time Guide", inner(C.render_time_guide(d["timeGuide"]))))
    if ov.get("keyConceptsText"):
        cards.append((C.CALLOUT_ICONS["info"].strip(), "Key Concepts", f'<p>{ov["keyConceptsText"]}</p>'))
    if ov.get("textbookReference"):
        cards.append((C.CALLOUT_ICONS["bookex"].strip(), "Textbook Reference", f'<p>{ov["textbookReference"]}</p>'))
    body = f'<p class="sx-lead">{ov["body"]}</p>'
    if ov.get("mentorQuote"):
        body += C.render_mentor_quote(ov["mentorQuote"])
    body += C.render_h3({"label": "Filename"}, "blue") + f'<p>{ov.get("filenameNote", "")}</p>'
    body += C.render_h3({"label": "What You'll Learn"}, "blue") + C.render_objectives(ov.get("objectives", []))
    body += ('<p class="sx-hint">Where does your new code go? The <a href="#outline" data-tab="outline">Outline</a> '
             'tab shows the whole program. Work with this sheet on one half of your screen and VS Code on the other.</p>')
    body += cards_row(cards)
    tabs.append(("start", "Start", "path", header("LAB", labnum, meta["title"]), body))

    # Checkpoints
    for cp in d["checkpoints"]:
        tabs.append((f'cp{cp["number"]}', f'CP{cp["number"]}', "path",
                     header("Checkpoint", cp["number"], cp["title"], cp=True), checkpoint_body(cp)))

    # Finish
    fc_nodigest = copy.deepcopy(fc)
    fc_nodigest.pop("messageDigest", None)
    finish = (C.render_h3({"label": "Program Requirements"}, "red") + C.render_program_requirements(ov.get("programRequirements", []))
              + C.render_h3({"label": "Named Constants"}, "red") + C.render_named_constants(ov.get("namedConstants", []))
              + inner(C.render_final_checklist(fc_nodigest)))
    help_inner = inner(C.render_need_help(nh, meta.get("module", 1)))
    finish += cards_row([(C.CALLOUT_ICONS["info"].strip(), "Need Help?", help_inner)])
    tabs.append(("finish", "Finish", "path", header("LAB", labnum, "Before You Submit"), finish))

    # Reference tabs
    tabs.append(("outline", "Outline", "ref", header("LAB", labnum, "Program Outline"),
                 inner(C.render_before_you_begin(d["beforeYouBegin"]))))
    tabs.append(("strings", "Strings", "ref", header("LAB", labnum, "Strings"),
                 C.render_message_digest(fc["messageDigest"])))
    return tabs


def color_of(tid):
    return next(v for k, v in TAB_COLORS.items() if tid.startswith(k))


def page(d, tabs):
    path = [t for t in tabs if t[2] == "path"]
    order = [t[0] for t in path]
    buttons, panels = "", ""
    for tid, name, kind, head, body in tabs:
        col = color_of(tid)
        buttons += (f'<a class="sx-tab sx-tab--{kind}" role="tab" href="#{tid}" data-tab="{tid}" '
                    f'style="--tab:{ACCENT[col]}">{name}</a>')
        i = order.index(tid) if tid in order else None
        back = nxt = ""
        if i is not None and i > 0:
            back = f'<a class="sx-back" href="#{path[i-1][0]}" data-tab="{path[i-1][0]}">&larr; Back: {path[i-1][1]}</a>'
        if i is not None and i < len(path) - 1:
            nxt = f'<a class="sx-next" href="#{path[i+1][0]}" data-tab="{path[i+1][0]}">Next: {path[i+1][1]} &rarr;</a>'
        panels += (f'<section class="sx-panel" id="p-{tid}" data-tab="{tid}" hidden>'
                   f'<div class="lc-card lc-card--{col}"><div class="lc-topper">{head}</div>'
                   f'<div class="lc-panel">{back}{body}<div class="sx-botnav">{nxt}</div></div></div></section>')
    out = TEMPLATE.replace("{{TITLE}}", H.escape(d["meta"]["title"])).replace("{{TABS}}", buttons) \
        .replace("{{PANELS}}", panels).replace("{{DEFAULT}}", order[0])
    return out.replace('src="../../', f'src="{ASSETS_URL}').replace("src='../../", f"src='{ASSETS_URL}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}} | IS2053 (sandbox)</title>
<link rel="icon" type="image/png" href="https://jfnewsom.github.io/is2053-assets/favicon.png">
<link rel="stylesheet" href="https://jfnewsom.github.io/is2053-assets/labs.css">
<style>
body{margin:0}
.sx-bar{position:sticky;top:0;z-index:20;background:#0a0a0a;display:flex;align-items:flex-end;padding:8px 8px 0;margin-bottom:2px}
.sx-scroller{position:relative;flex:1;min-width:0}
.sx-tabs{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none}
.sx-tabs::-webkit-scrollbar{display:none}
.sx-tab{flex:0 0 auto;padding:9px 16px;font:700 15px/1 Roboto,sans-serif;color:#B0B8C4;text-decoration:none;
  border:2px solid #2a2a2a;border-bottom:0;border-radius:6px 6px 0 0;white-space:nowrap}
.sx-tab:hover{color:#F5F5F5;border-color:var(--tab)}
.sx-tab--ref{font-weight:400;border-style:dashed}
.sx-tab--path+.sx-tab--ref{margin-left:20px}
.sx-tab[aria-selected=true]{background:var(--tab);border-color:var(--tab);color:#000}
.sx-fade{position:absolute;top:0;bottom:0;width:44px;display:none;align-items:center;border:0;cursor:pointer;
  color:#FFCC00;font:700 26px/1 Roboto,sans-serif;z-index:2}
.sx-fade.l{left:0;justify-content:flex-start;background:linear-gradient(90deg,#0a0a0a 60%,transparent)}
.sx-fade.r{right:0;justify-content:flex-end;background:linear-gradient(270deg,#0a0a0a 60%,transparent)}
.sx-fade.on{display:flex}
.sx-newtab{flex:0 0 auto;align-self:center;margin:0 4px 6px 10px;color:#B0B8C4;font:13px Roboto,sans-serif;white-space:nowrap}
.lc-wrapper,.sx-main{padding:0}
.sx-panel .lc-card{margin:0;border-radius:0 0 8px 8px}
.sx-head{display:flex;align-items:center;gap:16px}
.sx-head .lc-topper-title{flex:1;min-width:0}
.sx-logo{height:56px;width:auto}
.sx-lead{font-size:1.25em;line-height:1.45}
.sx-back{display:inline-block;margin:0 0 10px;font-weight:700;color:#FFCC00;text-decoration:none}
.sx-botnav{margin-top:28px;padding-top:14px;border-top:2px solid rgba(255,255,255,.15);text-align:right;min-height:10px}
.sx-next{display:inline-block;font:700 20px Roboto,sans-serif;color:#000;background:#FFCC00;padding:10px 18px;border-radius:4px;
  box-shadow:4px 4px 0 #000;text-decoration:none}
.sx-hint{opacity:.85}
.sx-hint a{color:#00FFFF}
.sx-cards{margin-top:24px}
.sx-cards__row{display:flex;gap:10px;overflow-x:auto;padding-bottom:6px}
.sx-card{flex:0 0 auto;display:flex;align-items:center;gap:8px;padding:8px 14px 8px 8px;cursor:pointer;
  background:rgba(0,0,0,.55);color:#F5F5F5;border:2px solid rgba(255,255,255,.25);border-radius:6px;font:600 14px Roboto,sans-serif}
.sx-card__icon svg{width:28px;height:28px;display:block}
.sx-card[aria-expanded=true]{border-color:#FFCC00;color:#FFCC00}
.sx-cardpanel{margin-top:10px}
#sx-diag{position:fixed;left:6px;bottom:6px;z-index:30;pointer-events:none;opacity:.85;background:#111;border:1px solid #444;
  color:#0f0;font:11px/1.35 monospace;padding:6px 8px;white-space:pre}
</style></head><body>
<div class="sx-bar">
  <div class="sx-scroller">
    <button class="sx-fade l" aria-label="More tabs to the left">&lsaquo;</button>
    <nav class="sx-tabs" role="tablist">{{TABS}}</nav>
    <button class="sx-fade r" aria-label="More tabs to the right">&rsaquo;</button>
  </div>
  <a class="sx-newtab" id="sx-newtab" href="#" target="_blank" rel="noopener" hidden>Open in new tab &#8599;</a>
</div>
<main class="sx-main">{{PANELS}}</main>
<div id="sx-diag" hidden></div>
<script>
(function(){
const qs=new URLSearchParams(location.search), nav=document.querySelector('.sx-tabs');
const inIframe=window.self!==window.top, pos={}; let cur=null;
function show(id,push){
  if(!document.getElementById('p-'+id)) id='{{DEFAULT}}';
  if(cur) pos[cur]=scrollY;
  document.querySelectorAll('.sx-panel').forEach(p=>p.hidden=p.dataset.tab!==id);
  document.querySelectorAll('.sx-tab').forEach(t=>t.setAttribute('aria-selected',t.dataset.tab===id));
  cur=id;
  const a=nav.querySelector('[aria-selected=true]'); if(a) a.scrollIntoView({block:'nearest',inline:'center'});
  scrollTo(0,pos[id]||0);
  if(push) history.replaceState(null,'','#'+id);
  document.getElementById('sx-newtab').href=location.href.split('#')[0]+'#'+id;
  fades(); diag();
}
document.addEventListener('click',e=>{
  const a=e.target.closest('a[data-tab]'); if(a){e.preventDefault();show(a.dataset.tab,true);return;}
  const c=e.target.closest('.sx-card'); if(!c)return;
  const box=c.closest('.sx-cards'), open=c.getAttribute('aria-expanded')==='true';
  box.querySelectorAll('.sx-card').forEach(b=>b.setAttribute('aria-expanded','false'));
  box.querySelectorAll('.sx-cardpanel').forEach(p=>p.hidden=true);
  if(!open){c.setAttribute('aria-expanded','true');box.querySelector('.sx-cardpanel[data-i="'+c.dataset.i+'"]').hidden=false;}
});
const L=document.querySelector('.sx-fade.l'),R=document.querySelector('.sx-fade.r');
function fades(){L.classList.toggle('on',nav.scrollLeft>4);R.classList.toggle('on',nav.scrollLeft+nav.clientWidth<nav.scrollWidth-4);}
nav.addEventListener('scroll',fades); addEventListener('resize',()=>{fades();diag();});
L.onclick=()=>nav.scrollBy({left:-nav.clientWidth*.7,behavior:'smooth'});R.onclick=()=>nav.scrollBy({left:nav.clientWidth*.7,behavior:'smooth'});
if(inIframe) document.getElementById('sx-newtab').hidden=false;
function diag(){ if(qs.get('diag')!=='1')return; const d=document.getElementById('sx-diag'); d.hidden=false;
  d.textContent=['iframe: '+inIframe,'viewport: '+innerWidth+' x '+innerHeight,'page height: '+document.documentElement.scrollHeight,
  'bar top: '+Math.round(document.querySelector('.sx-bar').getBoundingClientRect().top),'tab: '+cur].join('\n');}
addEventListener('scroll',diag,{passive:true});
show(location.hash.slice(1)||'{{DEFAULT}}',false);
})();
</script></body></html>"""

if __name__ == "__main__":
    data = json.load(open(sys.argv[2]))
    open(sys.argv[3], "w").write(page(data, build(data)))
    print("wrote", sys.argv[3])
