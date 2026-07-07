"""Generate a self-contained HTML visualization of the full curriculum:
a course-level dependency diagram plus one prerequisite graph per course.

Usage:  ../.venv/bin/python scripts/export_course_map.py  (from backend/)
Writes: docs/course-map.html at the project root.
"""

import html
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.content.loader import load_seed
from app.db import Base
from app.models import Course, Topic, TopicEdge

NODE_W, NODE_H = 200, 58
GAP_X, GAP_Y = 70, 16
PAD = 24


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def build_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    load_seed(db)
    return db


def local_depths(topics: dict[int, Topic], edges: list[tuple[int, int]]) -> dict[int, int]:
    """Longest-path layering using only in-course edges."""
    prereqs = defaultdict(set)
    for a, b in edges:
        prereqs[b].add(a)
    depth: dict[int, int] = {}

    def resolve(tid: int, seen: frozenset = frozenset()) -> int:
        if tid in depth:
            return depth[tid]
        if tid in seen:
            return 0
        d = 1 + max(
            (resolve(p, seen | {tid}) for p in prereqs[tid] if p in topics), default=-1
        )
        depth[tid] = d
        return d

    for tid in topics:
        resolve(tid)
    return depth


def course_svg(db) -> str:
    """Course-level dependency diagram, layered bottom-up like the MA chart."""
    courses = db.scalars(select(Course).order_by(Course.sequence_order)).all()
    topic_course = {t.id: t.course_id for t in db.scalars(select(Topic))}
    cedges: set[tuple[int, int]] = set()
    for e in db.scalars(select(TopicEdge)):
        ca, cb = topic_course.get(e.prereq_id), topic_course.get(e.topic_id)
        if ca and cb and ca != cb:
            cedges.add((ca, cb))

    ids = {c.id: c for c in courses}
    layer = local_depths({c.id: c for c in courses}, [e for e in cedges])
    by_layer = defaultdict(list)
    for cid in ids:
        by_layer[layer[cid]].append(cid)
    n_layers = max(by_layer) + 1
    width = max(len(v) for v in by_layer.values()) * (NODE_W + GAP_X) + 2 * PAD
    height = n_layers * (NODE_H + 46) + 2 * PAD

    pos = {}
    for lv, members in by_layer.items():
        members.sort(key=lambda cid: ids[cid].sequence_order)
        row_w = len(members) * (NODE_W + GAP_X) - GAP_X
        x0 = (width - row_w) / 2
        y = height - PAD - NODE_H - lv * (NODE_H + 46)
        for i, cid in enumerate(members):
            pos[cid] = (x0 + i * (NODE_W + GAP_X), y)

    paths, nodes = [], []
    for a, b in sorted(cedges):
        xa, ya = pos[a][0] + NODE_W / 2, pos[a][1]
        xb, yb = pos[b][0] + NODE_W / 2, pos[b][1] + NODE_H
        my = (ya + yb) / 2
        paths.append(
            f'<path d="M {xa:.0f} {ya:.0f} C {xa:.0f} {my:.0f}, {xb:.0f} {my:.0f}, '
            f'{xb:.0f} {yb:.0f}" class="cedge"/>'
        )
    for cid, (x, y) in pos.items():
        c = ids[cid]
        words = c.title.split()
        if len(c.title) > 26 and len(words) > 2:
            mid = len(words) // 2
            lines = [" ".join(words[:mid]), " ".join(words[mid:])]
            label = (
                f'<text x="{x + NODE_W/2:.0f}" y="{y + NODE_H/2 - 4:.0f}" class="clabel">{esc(lines[0])}</text>'
                f'<text x="{x + NODE_W/2:.0f}" y="{y + NODE_H/2 + 13:.0f}" class="clabel">{esc(lines[1])}</text>'
            )
        else:
            label = f'<text x="{x + NODE_W/2:.0f}" y="{y + NODE_H/2 + 4:.0f}" class="clabel">{esc(c.title)}</text>'
        nodes.append(
            f'<g><a href="#course-{esc(c.slug)}">'
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{NODE_W}" height="{NODE_H}" rx="6" class="cnode"/>'
            f"{label}</a></g>"
        )
    return (
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" style="max-width:{width:.0f}px">'
        + "".join(paths)
        + "".join(nodes)
        + "</svg>"
    )


def course_section(db, course: Course) -> str:
    topics = {
        t.id: t
        for t in db.scalars(
            select(Topic).where(Topic.course_id == course.id).order_by(Topic.id)
        )
    }
    all_titles = {t.id: (t.title, t.course.title) for t in db.scalars(select(Topic))}
    in_edges, cross = [], defaultdict(list)
    for e in db.scalars(select(TopicEdge).where(TopicEdge.topic_id.in_(topics.keys()))):
        if e.prereq_id in topics:
            in_edges.append((e.prereq_id, e.topic_id))
        else:
            title, ctitle = all_titles.get(e.prereq_id, ("?", "?"))
            cross[e.topic_id].append(f"{ctitle} · {title}")

    depth = local_depths(topics, in_edges)
    by_col = defaultdict(list)
    for tid, d in depth.items():
        by_col[d].append(tid)
    for col in by_col.values():
        col.sort(key=lambda tid: (topics[tid].unit, topics[tid].id))

    n_cols = max(by_col) + 1
    n_rows = max(len(v) for v in by_col.values())
    width = n_cols * (NODE_W + GAP_X) - GAP_X + 2 * PAD
    height = n_rows * (NODE_H + GAP_Y) - GAP_Y + 2 * PAD

    pos = {}
    for d, col in by_col.items():
        for i, tid in enumerate(col):
            pos[tid] = (PAD + d * (NODE_W + GAP_X), PAD + i * (NODE_H + GAP_Y))

    adj_down = defaultdict(list)
    adj_up = defaultdict(list)
    paths = []
    for k, (a, b) in enumerate(in_edges):
        adj_down[a].append(b)
        adj_up[b].append(a)
        xa, ya = pos[a][0] + NODE_W, pos[a][1] + NODE_H / 2
        xb, yb = pos[b][0], pos[b][1] + NODE_H / 2
        mx = (xa + xb) / 2
        paths.append(
            f'<path d="M {xa:.0f} {ya:.0f} C {mx:.0f} {ya:.0f}, {mx:.0f} {yb:.0f}, '
            f'{xb:.0f} {yb:.0f}" class="edge" data-from="{a}" data-to="{b}"/>'
        )

    nodes = []
    for tid, (x, y) in pos.items():
        t = topics[tid]
        tip = t.description or t.title
        if cross[tid]:
            tip += "\nAlso requires: " + "; ".join(cross[tid])
        marker = '<tspan class="crossmark">⇠ </tspan>' if cross[tid] else ""
        nodes.append(
            f'<g class="tnode" data-id="{tid}"><title>{esc(tip)}</title>'
            f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="5"/>'
            f'<text x="{x + 10}" y="{y + 24}" class="ttitle">{marker}{esc(t.title[:30])}'
            f'{"…" if len(t.title) > 30 else ""}</text>'
            f'<text x="{x + 10}" y="{y + 43}" class="tunit">{esc(t.unit[:32])}</text></g>'
        )

    graph_json = json.dumps({"down": adj_down, "up": adj_up})
    unit_names = list(dict.fromkeys(t.unit for t in topics.values()))
    return f"""
<section class="course" id="course-{esc(course.slug)}">
  <h2>{esc(course.title)} <span class="count">{len(topics)} topics · {len(unit_names)} units</span></h2>
  <p class="desc">{esc(course.description.strip())}</p>
  <div class="scroller">
    <svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" data-graph='{esc(graph_json)}'>
      {"".join(paths)}
      {"".join(nodes)}
    </svg>
  </div>
</section>"""


def main() -> None:
    db = build_db()
    courses = db.scalars(select(Course).order_by(Course.sequence_order)).all()
    total = len(db.scalars(select(Topic)).all())
    edges = len(db.scalars(select(TopicEdge)).all())

    sections = "\n".join(course_section(db, c) for c in courses)
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Educator — Curriculum Map</title>
<style>
  :root {{
    --paper:#f7f2e7; --raised:#fdfaf3; --sunken:#efe8d8; --ink:#221d15;
    --soft:#5c5344; --faint:#9c9280; --rule:#d8cfba; --accent:#9c2f22; --blue:#2e5d74;
  }}
  body {{ background:var(--paper); color:var(--ink); font-family: Georgia, 'Times New Roman', serif;
         margin:0; padding:40px 48px 100px; }}
  h1 {{ font-size:34px; margin:0 0 6px; }}
  h2 {{ font-size:22px; margin:48px 0 4px; border-bottom:2px solid var(--ink); padding-bottom:6px; }}
  h2 .count {{ font-family:monospace; font-size:12px; color:var(--faint); font-weight:normal; }}
  .kicker {{ font-family:monospace; font-size:12px; letter-spacing:.16em; text-transform:uppercase;
             color:var(--accent); }}
  .desc {{ color:var(--soft); max-width:72ch; margin:4px 0 14px; }}
  .hint {{ font-family:monospace; font-size:12px; color:var(--faint); margin-bottom:26px; }}
  .overview {{ background:var(--raised); border:1px solid var(--rule); padding:18px;
               box-shadow:4px 4px 0 rgba(34,29,21,.07); overflow-x:auto; }}
  .scroller {{ overflow-x:auto; background:var(--raised); border:1px solid var(--rule);
               box-shadow:4px 4px 0 rgba(34,29,21,.07); }}
  .cnode {{ fill:var(--sunken); stroke:var(--ink); stroke-width:1.4; }}
  g:hover .cnode {{ fill:#e8ddc4; }}
  .clabel {{ font-family:Georgia, serif; font-size:13.5px; text-anchor:middle; fill:var(--ink); }}
  .cedge {{ fill:none; stroke:var(--soft); stroke-width:1.4; opacity:.55; }}
  .edge {{ fill:none; stroke:var(--faint); stroke-width:1.3; opacity:.5; }}
  .tnode rect {{ fill:var(--paper); stroke:var(--rule); stroke-width:1.2; }}
  .tnode:hover rect {{ stroke:var(--ink); }}
  .ttitle {{ font-family:Georgia, serif; font-size:12.5px; fill:var(--ink); }}
  .tunit {{ font-family:monospace; font-size:9.5px; fill:var(--faint); letter-spacing:.04em; }}
  .crossmark {{ fill:var(--blue); }}
  .tnode.hl-self rect {{ fill:#f3ddd7; stroke:var(--accent); stroke-width:1.8; }}
  .tnode.hl-up rect {{ fill:#dbe7ec; stroke:var(--blue); }}
  .tnode.hl-down rect {{ fill:#dde8d4; stroke:#3d6b35; }}
  .edge.hl {{ stroke:var(--accent); opacity:1; stroke-width:2; }}
  a {{ text-decoration:none; }}
  nav {{ font-family:monospace; font-size:12.5px; margin:14px 0 30px; line-height:2; }}
  nav a {{ color:var(--accent); margin-right:14px; }}
</style>
</head>
<body>
<div class="kicker">Educator</div>
<h1>Curriculum Map</h1>
<p class="desc">{len(courses)} courses · {total} topics · {edges} prerequisite edges.
Topics flow left to right: everything a topic needs sits somewhere to its left.</p>
<p class="hint">Hover a topic to highlight what it requires (blue) and what it unlocks (green).
A <span style="color:var(--blue)">⇠</span> marks topics with prerequisites in another course
(hover to see them). Click a course in the overview to jump to it.</p>

<div class="overview">{course_svg(db)}</div>

<nav>{"".join(f'<a href="#course-{esc(c.slug)}">{esc(c.title)}</a>' for c in courses)}</nav>

{sections}

<script>
document.querySelectorAll('.scroller svg').forEach(svg => {{
  const graph = JSON.parse(svg.dataset.graph);
  const nodes = new Map();
  svg.querySelectorAll('.tnode').forEach(n => nodes.set(n.dataset.id, n));
  const walk = (start, dir) => {{
    const out = new Set(); const stack = [...(graph[dir][start] || [])];
    while (stack.length) {{
      const cur = String(stack.pop());
      if (!out.has(cur)) {{ out.add(cur); stack.push(...(graph[dir][cur] || [])); }}
    }}
    return out;
  }};
  svg.querySelectorAll('.tnode').forEach(node => {{
    node.addEventListener('mouseenter', () => {{
      const id = node.dataset.id;
      node.classList.add('hl-self');
      walk(id, 'up').forEach(t => nodes.get(t)?.classList.add('hl-up'));
      walk(id, 'down').forEach(t => nodes.get(t)?.classList.add('hl-down'));
      svg.querySelectorAll('.edge').forEach(e => {{
        if (e.dataset.from === id || e.dataset.to === id) e.classList.add('hl');
      }});
    }});
    node.addEventListener('mouseleave', () => {{
      svg.querySelectorAll('.hl-self,.hl-up,.hl-down').forEach(n =>
        n.classList.remove('hl-self','hl-up','hl-down'));
      svg.querySelectorAll('.edge.hl').forEach(e => e.classList.remove('hl'));
    }});
  }});
}});
</script>
</body>
</html>"""

    out = Path(__file__).resolve().parent.parent.parent / "docs" / "course-map.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(doc)
    print(f"wrote {out} ({len(doc) // 1024} KB): {len(courses)} courses, {total} topics")


if __name__ == "__main__":
    main()
