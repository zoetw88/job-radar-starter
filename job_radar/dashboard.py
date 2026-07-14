from collections.abc import Sequence
from dataclasses import asdict
from html import escape
import json
from pathlib import Path
from urllib.parse import urlparse

from job_radar.adapters import Job


def _safe_url(value: str) -> str | None:
    parsed = urlparse(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _job_key(job: Job) -> str:
    return f"{job.source}:{job.external_id}"


def _csv_attr(values: Sequence[str]) -> str:
    return ",".join(value.strip().lower() for value in values if value.strip())


def _job_card(job: Job) -> str:
    source, company, title = map(escape, (job.source, job.company, job.title))
    location = escape(job.location or "Location not specified")
    country = escape(job.country or "other", quote=True)
    category = escape(job.category or "other", quote=True)
    tracks = escape(_csv_attr(job.tracks), quote=True)
    skills = escape(_csv_attr(job.skills), quote=True)
    first_seen = escape(job.first_seen or job.published_at, quote=True)
    key = escape(_job_key(job), quote=True)
    search = escape(
        " ".join(
            (
                job.company,
                job.title,
                job.location,
                job.category,
                " ".join(job.tracks),
                " ".join(job.skills),
                job.summary,
            )
        ),
        quote=True,
    )
    score = str(job.score) if job.score is not None else "—"
    details = []
    if job.salary:
        details.append(f'<p class="salary">{escape(job.salary)}</p>')
    if job.summary:
        details.append(f'<p class="why"><b>Why it may fit</b>{escape(job.summary)}</p>')
    if job.risk:
        details.append(f'<p class="risk"><b>Check before applying</b>{escape(job.risk)}</p>')

    tag_values = [job.source, job.category or "uncategorized", job.country or "location unknown"]
    tag_values.extend(job.tracks)
    tag_values.extend(job.skills)
    tags = "".join(f'<span class="tag">{escape(value)}</span>' for value in dict.fromkeys(tag_values) if value)
    visa = ""
    if job.visa_supported is True:
        visa = '<span class="signal visa">Visa support listed</span>'
    elif job.visa_supported is False:
        visa = '<span class="signal check">Work authorization required</span>'

    url = _safe_url(job.url)
    link = (
        f'<a class="primary-link" href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">Open official post <span aria-hidden="true">↗</span></a>'
        if url
        else '<span class="primary-link disabled" aria-disabled="true">Invalid source link</span>'
    )
    date = escape(job.first_seen or job.published_at or "Date not specified")

    return f"""
      <article class="job-card" data-key="{key}" data-source="{source}" data-country="{country}" data-category="{category}" data-tracks="{tracks}" data-skills="{skills}" data-first-seen="{first_seen}" data-search="{search}">
        <div class="score" aria-label="Match score">{score}</div>
        <div class="job-body">
          <header class="job-heading">
            <div><h3>{title}</h3><p class="company">{company} · {location}</p></div>
            {visa}
          </header>
          <div class="tags">{tags}</div>
          {''.join(details)}
          <footer class="job-actions">
            <div class="status-actions" aria-label="Tracking status">
              <button type="button" data-state="interested">☆ Interested</button>
              <button type="button" data-state="applied">✓ Applied</button>
              <button type="button" data-state="skip">Hide</button>
              <button type="button" data-state="dead">Expired</button>
            </div>
            <div class="source-actions">{link}<time>{date}</time></div>
          </footer>
        </div>
      </article>"""


_TEMPLATE = r"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="A local-first dashboard for reviewing, filtering, and tracking jobs from official sources.">
  <meta name="color-scheme" content="dark light">
  <title>Job Radar — daily review</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='%23d6a84b'/><path d='M15 39a17 17 0 0 1 17-17' fill='none' stroke='%23101418' stroke-width='5' stroke-linecap='round'/><path d='M15 50a28 28 0 0 1 28-28' fill='none' stroke='%23101418' stroke-width='5' stroke-linecap='round'/><circle cx='16' cy='49' r='5' fill='%23101418'/></svg>">
  <style>
    :root{--bg:#0f1216;--surface:#151a20;--surface-2:#1b2128;--surface-3:#222a33;--text:#edf1f5;--muted:#98a3af;--faint:#6f7b87;--line:#2b343e;--accent:#d6a84b;--accent-soft:#2d2618;--green:#65b88a;--green-soft:#16291f;--red:#db837c;--red-soft:#321d1c;--blue:#7fa9d8;--blue-soft:#182532;--shadow:rgba(4,8,12,.34);--focus:#e6bd69}
    :root[data-theme="light"]{--bg:#f4efe6;--surface:#fbf7ef;--surface-2:#f0e9dc;--surface-3:#e7dfd1;--text:#24211d;--muted:#69635a;--faint:#8b8276;--line:#d7cebf;--accent:#9a6b16;--accent-soft:#f2e5c6;--green:#26734a;--green-soft:#dcecdf;--red:#a44840;--red-soft:#f4deda;--blue:#356996;--blue-soft:#dce8f2;--shadow:rgba(77,62,41,.15);--focus:#8a5b06}
    *{box-sizing:border-box} [hidden]{display:none!important} html{scroll-behavior:smooth} body{margin:0;min-height:100dvh;background:radial-gradient(circle at 12% -10%,color-mix(in srgb,var(--accent) 8%,transparent),transparent 33rem),var(--bg);color:var(--text);font:15px/1.55 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif}
    button,input{font:inherit} button,a{touch-action:manipulation} button{color:inherit} :focus-visible{outline:3px solid color-mix(in srgb,var(--focus) 78%,transparent);outline-offset:3px}.skip-link{position:fixed;left:1rem;top:-5rem;z-index:30;background:var(--text);color:var(--bg);padding:.7rem 1rem;border-radius:.4rem}.skip-link:focus{top:1rem}
    .shell{width:min(1160px,calc(100% - 32px));margin:0 auto;padding:32px 0 72px}.eyebrow{margin:0 0 8px;color:var(--accent);font:600 .72rem/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.13em;text-transform:uppercase}.masthead{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:24px;align-items:start;padding-bottom:24px;border-bottom:1px solid var(--line)}h1{font-size:clamp(2rem,5vw,4.25rem);line-height:.94;letter-spacing:-.055em;margin:0;max-width:760px;text-wrap:balance}.lede{max-width:64ch;margin:18px 0 0;color:var(--muted);font-size:1rem}.header-actions{display:flex;gap:8px;align-items:center}.utility{border:1px solid var(--line);background:var(--surface);padding:8px 11px;border-radius:8px;cursor:pointer;transition:transform .18s ease,border-color .18s ease,background .18s ease}.utility:hover{border-color:var(--faint);background:var(--surface-2)}.utility:active{transform:translateY(1px)}
    .statbar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-bottom:1px solid var(--line);margin-bottom:24px}.stat{padding:19px 18px 17px;border-right:1px solid var(--line)}.stat:first-child{padding-left:0}.stat:last-child{border-right:0}.stat strong{display:block;color:var(--accent);font:700 1.55rem/1 ui-monospace,SFMono-Regular,Consolas,monospace;font-variant-numeric:tabular-nums}.stat span{display:block;margin-top:6px;color:var(--muted);font-size:.76rem}
    .recommendations{display:grid;grid-template-columns:220px minmax(0,1fr);gap:28px;padding:26px 0;border-bottom:1px solid var(--line)}.section-kicker{margin:0;color:var(--muted);font-size:.74rem}.recommendations h2{margin:5px 0 0;font-size:1.25rem;letter-spacing:-.025em}.recommendation-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.recommendation{min-width:0;background:var(--surface);border-top:2px solid var(--accent);padding:14px 15px 15px}.recommendation .rank{color:var(--accent);font:700 .72rem/1 ui-monospace,SFMono-Regular,Consolas,monospace}.recommendation strong{display:block;margin:9px 0 2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.recommendation span{display:block;color:var(--muted);font-size:.8rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.recommendation.empty{border-top-color:var(--line);color:var(--muted)}
    .command{position:sticky;top:0;z-index:10;margin:0 -12px;padding:14px 12px 12px;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}.command-row{display:grid;grid-template-columns:auto minmax(220px,1fr);gap:16px;align-items:center}.view-switcher{display:flex;gap:3px;padding:3px;background:var(--surface);border:1px solid var(--line);border-radius:10px}.view-switcher button{border:0;background:transparent;color:var(--muted);padding:7px 12px;border-radius:7px;cursor:pointer;font-size:.82rem;transition:background .18s ease,color .18s ease}.view-switcher button.active{background:var(--surface-3);color:var(--text)}.search{position:relative}.search input{width:100%;border:1px solid var(--line);background:var(--surface);color:var(--text);border-radius:10px;padding:10px 42px 10px 14px}.search input::placeholder{color:var(--faint)}.search kbd{position:absolute;right:10px;top:50%;transform:translateY(-50%);color:var(--faint);border:1px solid var(--line);border-bottom-width:2px;border-radius:5px;padding:1px 6px;font:500 .7rem ui-monospace,SFMono-Regular,Consolas,monospace}
    .filter-panel{padding:10px 0 0}.filter-panel summary{cursor:pointer;color:var(--muted);font-size:.8rem;width:max-content}.filter-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px 18px;padding:14px 0 3px}.filter-group label{display:block;margin-bottom:5px;color:var(--faint);font-size:.7rem}.chips{display:flex;gap:5px;overflow-x:auto;padding:1px 1px 6px;scrollbar-width:thin}.chip{flex:0 0 auto;border:1px solid var(--line);background:transparent;color:var(--muted);padding:4px 9px;border-radius:999px;cursor:pointer;font-size:.72rem;transition:background .18s ease,border-color .18s ease,color .18s ease,transform .18s ease}.chip:hover{border-color:var(--faint);color:var(--text)}.chip:active{transform:scale(.97)}.chip.active{background:var(--accent-soft);border-color:color-mix(in srgb,var(--accent) 55%,var(--line));color:var(--accent)}
    .panel{padding-top:12px}.panel[hidden]{display:none}.tier-head{display:flex;align-items:baseline;justify-content:space-between;padding:17px 0 8px;border-bottom:1px solid var(--line)}.tier-head h2{margin:0;font-size:1rem}.tier-head span{color:var(--muted);font-size:.78rem}.job-list{display:grid}.job-card{display:grid;grid-template-columns:64px minmax(0,1fr);gap:19px;padding:22px 4px;border-bottom:1px solid var(--line);transition:background .18s ease,opacity .18s ease}.job-card:hover{background:color-mix(in srgb,var(--surface) 48%,transparent)}.job-card[data-status="skip"],.job-card[data-status="dead"]{opacity:.47}.score{padding-top:3px;text-align:right;color:var(--accent);font:750 1.55rem/1 ui-monospace,SFMono-Regular,Consolas,monospace;font-variant-numeric:tabular-nums}.job-heading{display:flex;justify-content:space-between;gap:14px;align-items:start}.job-heading h3{margin:0;font-size:1.08rem;line-height:1.3;letter-spacing:-.018em}.company{margin:4px 0 0;color:var(--muted);font-size:.86rem}.signal{flex:0 0 auto;padding:3px 7px;border-radius:4px;font-size:.68rem}.signal.visa{background:var(--green-soft);color:var(--green)}.signal.check{background:var(--red-soft);color:var(--red)}.tags{display:flex;gap:5px;flex-wrap:wrap;margin-top:10px}.tag{color:var(--muted);border:1px solid var(--line);border-radius:5px;padding:2px 7px;font-size:.68rem}.salary{margin:11px 0 0;color:var(--green);font-weight:650}.why,.risk{margin:10px 0 0;max-width:76ch;font-size:.84rem}.why b,.risk b{display:block;margin-bottom:2px;color:var(--muted);font-size:.69rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase}.risk{color:var(--muted);border-left:2px solid color-mix(in srgb,var(--red) 50%,var(--line));padding-left:10px}.job-actions{display:flex;justify-content:space-between;gap:16px;align-items:end;margin-top:14px}.status-actions,.source-actions{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.status-actions button{border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:6px;padding:4px 8px;cursor:pointer;font-size:.72rem;transition:background .18s ease,color .18s ease,border-color .18s ease,transform .18s ease}.status-actions button:hover{color:var(--text);border-color:var(--faint)}.status-actions button:active{transform:translateY(1px)}.status-actions button.active[data-state="interested"]{background:var(--accent-soft);color:var(--accent);border-color:var(--accent)}.status-actions button.active[data-state="applied"]{background:var(--green-soft);color:var(--green);border-color:var(--green)}.status-actions button.active[data-state="skip"],.status-actions button.active[data-state="dead"]{background:var(--red-soft);color:var(--red);border-color:var(--red)}.primary-link{color:var(--blue);text-decoration:none;font-weight:650;font-size:.78rem}.primary-link:hover{text-decoration:underline}.primary-link.disabled{color:var(--faint)}time{color:var(--faint);font:500 .69rem ui-monospace,SFMono-Regular,Consolas,monospace}
    .deck-shell{min-height:540px;display:grid;place-items:center;padding:34px 0}.swipe-card{position:relative;width:min(620px,100%);min-height:410px;background:var(--surface);border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:18px;padding:28px;box-shadow:0 22px 70px var(--shadow);cursor:grab;user-select:none;transition:transform .22s ease,opacity .22s ease}.swipe-card:active{cursor:grabbing}.swipe-card .score{position:absolute;right:25px;top:27px}.swipe-card h2{max-width:80%;margin:34px 0 5px;font-size:clamp(1.6rem,4vw,2.7rem);line-height:1.02;letter-spacing:-.045em}.swipe-company{margin:0;color:var(--muted)}.swipe-card .why{margin-top:26px;font-size:.94rem}.swipe-card .risk{margin-top:17px}.stamp{position:absolute;top:24px;left:24px;opacity:0;border:2px solid currentColor;border-radius:7px;padding:5px 9px;font-weight:800;transform:rotate(-7deg)}.stamp.nope{left:auto;right:24px;color:var(--red);transform:rotate(7deg)}.deck-actions{display:flex;justify-content:center;gap:10px;margin-top:20px}.deck-actions button{width:48px;height:48px;border:1px solid var(--line);border-radius:50%;background:var(--surface);color:var(--muted);cursor:pointer;font-size:1.05rem;transition:transform .18s ease,border-color .18s ease,color .18s ease}.deck-actions button:hover{transform:translateY(-2px);border-color:var(--accent);color:var(--accent)}.deck-meta{text-align:center;color:var(--muted);font-size:.76rem;margin-top:12px}.matches-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding-top:14px}.match-card{background:var(--surface);border-top:2px solid var(--green);padding:18px}.match-card.applied{border-top-color:var(--blue)}.match-card h3{margin:0}.match-card p{margin:5px 0 12px;color:var(--muted);font-size:.82rem}.empty-state{grid-column:1/-1;padding:64px 24px;text-align:center;border:1px dashed var(--line);border-radius:14px;color:var(--muted)}.empty-state strong{display:block;color:var(--text);font-size:1.05rem;margin-bottom:6px}
    .footer{display:flex;justify-content:space-between;gap:20px;margin-top:42px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:.74rem}.footer p{margin:0;max-width:70ch}
    @media(max-width:820px){.masthead{grid-template-columns:1fr}.header-actions{justify-self:start}.recommendations{grid-template-columns:1fr}.recommendation-list{grid-template-columns:1fr}.filter-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.matches-grid{grid-template-columns:1fr}}
    @media(max-width:620px){.shell{width:min(100% - 22px,1160px);padding-top:22px}.statbar{grid-template-columns:repeat(2,1fr)}.stat:nth-child(2){border-right:0}.stat:nth-child(-n+2){border-bottom:1px solid var(--line)}.command{margin-inline:-11px}.command-row{grid-template-columns:1fr}.view-switcher{width:100%}.view-switcher button{flex:1;padding-inline:6px}.filter-grid{grid-template-columns:1fr}.job-card{grid-template-columns:42px 1fr;gap:12px;padding-block:18px}.score{font-size:1.15rem}.job-heading{display:block}.signal{display:inline-block;margin-top:8px}.job-actions{align-items:start;flex-direction:column}.swipe-card{min-height:430px;padding:22px}.swipe-card h2{margin-top:45px}.footer{flex-direction:column}}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition-duration:.01ms!important;animation-duration:.01ms!important}}
  </style>
</head>
<body>
  <a class="skip-link" href="#workspace">Skip to job review</a>
  <main class="shell" id="workspace">
    <header class="masthead">
      <div><p class="eyebrow">local-first / official sources</p><h1>Daily job review,<br>without the spreadsheet fog.</h1><p class="lede">Scan the strongest matches, inspect the trade-offs, and leave each role with a decision. Your profile and tracking history stay under your control.</p></div>
      <div class="header-actions"><button class="utility" id="exportStatus" type="button">Export status</button><button class="utility" id="themeToggle" type="button" aria-label="Change color theme">Theme</button></div>
    </header>
    <section class="statbar" aria-label="Scan summary"><div class="stat"><strong id="visibleCount">__JOB_COUNT__</strong><span>visible roles</span></div><div class="stat"><strong id="pendingCount">__JOB_COUNT__</strong><span>to review</span></div><div class="stat"><strong id="matchCount">0</strong><span>saved matches</span></div><div class="stat"><strong id="sourceCount">__SOURCE_COUNT__</strong><span>official sources</span></div></section>
    <section class="recommendations"><div><p class="section-kicker">Start here</p><h2>Highest-scored roles you have not handled</h2></div><div class="recommendation-list" id="recommendations"></div></section>
    <section class="command" aria-label="Review controls">
      <div class="command-row"><nav class="view-switcher" aria-label="Dashboard view"><button class="active" type="button" data-view="list">List</button><button type="button" data-view="deck">Swipe review</button><button type="button" data-view="matches">Saved matches</button></nav><div class="search"><input id="searchBox" type="search" aria-label="Search jobs" placeholder="Search company, role, skill, or location"><kbd>/</kbd></div></div>
      <details class="filter-panel"><summary>Filter this scan</summary><div class="filter-grid"><div class="filter-group"><label>Country / region</label><div class="chips" id="countryChips"></div></div><div class="filter-group"><label>Track</label><div class="chips" id="trackChips"></div></div><div class="filter-group"><label>Role category</label><div class="chips" id="categoryChips"></div></div><div class="filter-group"><label>Skill</label><div class="chips" id="skillChips"></div></div><div class="filter-group"><label>Freshness</label><div class="chips" id="freshnessChips"></div></div><div class="filter-group"><label>Official source</label><div class="chips" id="sourceChips"></div></div><div class="filter-group"><label>Tracking status</label><div class="chips" id="statusChips"></div></div></div></details>
    </section>
    <section class="panel" id="listPanel" data-panel="list"><div class="tier-head"><h2>Ranked matches</h2><span>Score comes from your local workflow</span></div><div class="job-list" id="jobList">__JOB_CARDS__</div></section>
    <section class="panel" id="deckPanel" data-panel="deck" hidden><div class="deck-shell"><div id="swipeDeck"></div></div></section>
    <section class="panel" id="matchesPanel" data-panel="matches" hidden><div class="tier-head"><h2>Saved matches</h2><span>Interested and applied roles</span></div><div class="matches-grid" id="matchesGrid"></div></section>
    <footer class="footer"><p>Job data and tracking state remain on this device by default. Always verify availability and work-authorization details on the official posting.</p><p>No applicant data is sent by this page.</p></footer>
  </main>
  <script>
    const JOBS=__JOBS_JSON__;
    const STORAGE_KEY='job-radar-status';
    const STATUS_META={interested:'☆ Interested',applied:'✓ Applied',skip:'Hidden',dead:'Expired'};
    const state=loadState();
    const filters={country:'',track:'',category:'',skill:'',freshness:'',source:'',status:''};
    let activeView='list';
    let undoStack=[];
    const cards=[...document.querySelectorAll('.job-card')];
    const byKey=new Map(JOBS.map(job=>[jobKey(job),job]));
    const newestDate=JOBS.map(job=>Date.parse(job.first_seen||job.published_at||'')).filter(Number.isFinite).sort((a,b)=>b-a)[0]||Date.now();

    function loadState(){try{const value=JSON.parse(localStorage.getItem(STORAGE_KEY)||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{}}catch{return {}}}
    function saveState(){localStorage.setItem(STORAGE_KEY,JSON.stringify(state))}
    function jobKey(job){return `${job.source}:${job.external_id}`}
    function esc(value){return String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]))}
    function safeUrl(value){try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)?url.href:''}catch{return ''}}
    function list(value){return Array.isArray(value)?value:[]}
    function statusOf(job){return state[jobKey(job)]||''}
    function setStatus(job,next){const key=jobKey(job),before=state[key]||'';undoStack.push({key,before});if(next&&next!==before)state[key]=next;else delete state[key];saveState();renderAll()}
    function ageDays(job){const value=Date.parse(job.first_seen||job.published_at||'');return Number.isFinite(value)?Math.max(0,Math.round((newestDate-value)/86400000)):9999}
    function matches(job){const text=[job.company,job.title,job.location,job.category,job.summary,...list(job.tracks),...list(job.skills)].join(' ').toLowerCase(),query=document.querySelector('#searchBox').value.trim().toLowerCase(),status=statusOf(job);return(!query||text.includes(query))&&(!filters.country||job.country===filters.country)&&(!filters.track||list(job.tracks).includes(filters.track))&&(!filters.category||job.category===filters.category)&&(!filters.skill||list(job.skills).includes(filters.skill))&&(!filters.freshness||ageDays(job)<=Number(filters.freshness))&&(!filters.source||job.source===filters.source)&&(!filters.status||status===filters.status)}
    function visibleJobs(){return JOBS.filter(matches).sort((a,b)=>(b.score??-1)-(a.score??-1))}
    function pendingJobs(){return visibleJobs().filter(job=>!statusOf(job))}

    function paintCard(card){const job=byKey.get(card.dataset.key),status=job?statusOf(job):'';card.dataset.status=status;card.querySelectorAll('[data-state]').forEach(button=>button.classList.toggle('active',button.dataset.state===status))}
    function renderList(){let visible=0;cards.forEach(card=>{const job=byKey.get(card.dataset.key),show=job&&matches(job);card.hidden=!show;if(show)visible++;paintCard(card)});document.querySelector('#visibleCount').textContent=visible}
    function renderStats(){const pending=pendingJobs().length,matchesCount=JOBS.filter(job=>['interested','applied'].includes(statusOf(job))).length;document.querySelector('#pendingCount').textContent=pending;document.querySelector('#matchCount').textContent=matchesCount}
    function renderRecommendations(){const picks=JOBS.filter(job=>!statusOf(job)).sort((a,b)=>(b.score??-1)-(a.score??-1)).slice(0,3),root=document.querySelector('#recommendations');root.innerHTML=picks.length?picks.map((job,index)=>`<article class="recommendation"><span class="rank">0${index+1} · ${esc(job.score??'—')} match</span><strong>${esc(job.title)}</strong><span>${esc(job.company)} · ${esc(job.location||job.country)}</span></article>`).join(''):'<div class="recommendation empty">No unhandled roles remain in this scan.</div>'}
    function detailMarkup(job){return `${job.salary?`<p class="salary">${esc(job.salary)}</p>`:''}${job.summary?`<p class="why"><b>Why it may fit</b>${esc(job.summary)}</p>`:''}${job.risk?`<p class="risk"><b>Check before applying</b>${esc(job.risk)}</p>`:''}`}
    function renderDeck(){const root=document.querySelector('#swipeDeck'),deck=pendingJobs();if(!deck.length){root.innerHTML='<div class="empty-state"><strong>Review queue complete</strong>Change a filter, clear a previous status, or import a new scan.</div>';return}const job=deck[0],url=safeUrl(job.url);root.innerHTML=`<article class="swipe-card" id="topSwipeCard"><span class="stamp like">INTERESTED</span><span class="stamp nope">HIDE</span><div class="score">${esc(job.score??'—')}</div><p class="eyebrow">${esc(job.source)} / ${esc(job.country||'other')}</p><h2>${esc(job.title)}</h2><p class="swipe-company">${esc(job.company)} · ${esc(job.location)}</p><div class="tags">${[job.category,...list(job.tracks),...list(job.skills)].filter(Boolean).map(value=>`<span class="tag">${esc(value)}</span>`).join('')}</div>${detailMarkup(job)}${url?`<p><a class="primary-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open official post ↗</a></p>`:''}</article><div class="deck-actions"><button type="button" data-deck="undo" aria-label="Undo">↩</button><button type="button" data-state="skip" aria-label="Hide">×</button><button type="button" data-state="dead" aria-label="Mark expired">!</button><button type="button" data-state="applied" aria-label="Mark applied">✓</button><button type="button" data-state="interested" aria-label="Mark interested">☆</button></div><p class="deck-meta">${deck.length} left · ← hide · → interested · ↑ applied</p>`;root.querySelectorAll('[data-state]').forEach(button=>button.addEventListener('click',()=>setStatus(job,button.dataset.state)));root.querySelector('[data-deck="undo"]').addEventListener('click',undo);attachSwipe(root.querySelector('#topSwipeCard'),job)}
    function attachSwipe(card,job){let start=0,delta=0,dragging=false;card.addEventListener('pointerdown',event=>{start=event.clientX;delta=0;dragging=true;card.setPointerCapture(event.pointerId)});card.addEventListener('pointermove',event=>{if(!dragging)return;delta=event.clientX-start;card.style.transform=`translateX(${delta}px) rotate(${delta/30}deg)`;card.querySelector('.stamp.like').style.opacity=Math.max(0,delta/100);card.querySelector('.stamp.nope').style.opacity=Math.max(0,-delta/100)});card.addEventListener('pointerup',()=>{dragging=false;if(Math.abs(delta)>110)setStatus(job,delta>0?'interested':'skip');else{card.style.transform='';card.querySelectorAll('.stamp').forEach(stamp=>stamp.style.opacity=0)}})}
    function undo(){const previous=undoStack.pop();if(!previous)return;if(previous.before)state[previous.key]=previous.before;else delete state[previous.key];saveState();renderAll()}
    function renderMatches(){const root=document.querySelector('#matchesGrid'),matches=JOBS.filter(job=>['interested','applied'].includes(statusOf(job))).sort((a,b)=>(b.score??-1)-(a.score??-1));if(!matches.length){root.innerHTML='<div class="empty-state"><strong>No saved matches yet</strong>Mark a role interested or applied from the list or swipe review.</div>';return}root.innerHTML=matches.map(job=>{const status=statusOf(job),url=safeUrl(job.url);return `<article class="match-card ${status==='applied'?'applied':''}" data-match-key="${esc(jobKey(job))}"><span class="eyebrow">${esc(STATUS_META[status])} · ${esc(job.score??'—')} match</span><h3>${esc(job.title)}</h3><p>${esc(job.company)} · ${esc(job.location)}</p>${url?`<a class="primary-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open official post ↗</a>`:''} <button class="utility" type="button" data-clear>Clear status</button></article>`}).join('');root.querySelectorAll('[data-match-key]').forEach(card=>card.querySelector('[data-clear]').addEventListener('click',()=>setStatus(byKey.get(card.dataset.matchKey),'')))}
    function renderAll(){renderList();renderStats();renderRecommendations();if(activeView==='deck')renderDeck();if(activeView==='matches')renderMatches()}

    function unique(field){const values=JOBS.flatMap(job=>Array.isArray(job[field])?job[field]:[job[field]]).filter(Boolean);return [...new Set(values)].sort((a,b)=>String(a).localeCompare(String(b)))}
    function buildChips(rootId,filterKey,values,allLabel='All'){const root=document.querySelector(`#${rootId}`),items=[['',allLabel],...values.map(value=>Array.isArray(value)?value:[value,value])];root.innerHTML=items.map(([value,label])=>`<button class="chip ${value===''?'active':''}" type="button" data-filter="${filterKey}" data-value="${esc(value)}">${esc(label)}</button>`).join('');root.querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>{filters[filterKey]=button.dataset.value;root.querySelectorAll('button').forEach(item=>item.classList.toggle('active',item===button));renderAll()}))}
    buildChips('countryChips','country',unique('country'));
    buildChips('trackChips','track',unique('tracks'));
    buildChips('categoryChips','category',unique('category'));
    buildChips('skillChips','skill',unique('skills'));
    buildChips('freshnessChips','freshness',[['1','24h'],['7','7 days'],['14','14 days']]);
    buildChips('sourceChips','source',unique('source'));
    buildChips('statusChips','status',Object.entries(STATUS_META));
    cards.forEach(card=>card.querySelectorAll('[data-state]').forEach(button=>button.addEventListener('click',()=>setStatus(byKey.get(card.dataset.key),button.dataset.state))));
    document.querySelector('#searchBox').addEventListener('input',renderAll);
    document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{activeView=button.dataset.view;document.querySelectorAll('[data-view]').forEach(item=>item.classList.toggle('active',item===button));document.querySelectorAll('[data-panel]').forEach(panel=>panel.hidden=panel.dataset.panel!==activeView);renderAll()}));
    document.addEventListener('keydown',event=>{if(event.key==='/'&&document.activeElement!==document.querySelector('#searchBox')){event.preventDefault();document.querySelector('#searchBox').focus()}if(activeView!=='deck'||['INPUT','BUTTON','A'].includes(document.activeElement.tagName))return;const job=pendingJobs()[0];if(!job)return;if(event.key==='ArrowLeft')setStatus(job,'skip');if(event.key==='ArrowRight')setStatus(job,'interested');if(event.key==='ArrowUp')setStatus(job,'applied')});
    document.querySelector('#exportStatus').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({exported_at:new Date().toISOString(),statuses:state},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='job-radar-status.json';link.click();URL.revokeObjectURL(url)});
    const root=document.documentElement,savedTheme=localStorage.getItem('job-radar-theme');if(savedTheme)root.dataset.theme=savedTheme;else if(matchMedia('(prefers-color-scheme: light)').matches)root.dataset.theme='light';document.querySelector('#themeToggle').addEventListener('click',()=>{root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';localStorage.setItem('job-radar-theme',root.dataset.theme)});
    renderAll();
  </script>
</body>
</html>
"""


def render_dashboard(jobs: Sequence[Job], output: Path) -> None:
    ordered_jobs = sorted(jobs, key=lambda job: job.score if job.score is not None else -1, reverse=True)
    cards = "\n".join(_job_card(job) for job in ordered_jobs)
    if not cards:
        cards = '<section class="empty-state"><strong>No jobs in this scan</strong>Edit your local profile and company catalog, then run the scanner again.</section>'
    payload_jobs = []
    for job in ordered_jobs:
        item = asdict(job)
        item["url"] = _safe_url(job.url) or ""
        payload_jobs.append(item)
    payload = json.dumps(payload_jobs, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    source_count = len({job.source for job in ordered_jobs})
    html = (
        _TEMPLATE.replace("__JOB_COUNT__", str(len(ordered_jobs)))
        .replace("__SOURCE_COUNT__", str(source_count))
        .replace("__JOB_CARDS__", cards)
        .replace("__JOBS_JSON__", payload)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
