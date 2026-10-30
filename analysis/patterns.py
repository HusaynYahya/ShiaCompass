#!/usr/bin/env python3
"""Shia Compass: find patterns in shared results.

Usage
  python3 analysis/patterns.py results.csv            # a CSV exported from Supabase (Table Editor -> results -> Export -> CSV)
  python3 analysis/patterns.py --demo                 # run on made-up data to see what the report looks like

Writes analysis/report.html (open it in a browser). Needs Python 3 with numpy and pandas:
  pip install numpy pandas

What it does
  1. Scores everyone on every axis (part 1's three spectrums, part 2's nine axes).
  2. Habits and About-you answers: for each answer (for example "Latmiyya in the car"), the average position on
     every axis compared with everyone else, as an effect size (difference in standard deviations).
  3. Links between statements: the strongest correlations between individual statements on *different* axes,
     which are the links the labels don't predict.
  4. Hidden dimensions: a factor analysis (principal components with varimax rotation) over all slider
     statements, showing which statements move together, whatever axis they were written for.
Groups smaller than --min-group (default 30) are never reported, so no small group can be singled out.
"""
import argparse, json, math, os, sys, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)
HERE = os.path.dirname(os.path.abspath(__file__))
Q = json.load(open(os.path.join(HERE, "questions.json"), encoding="utf-8"))
AXES = Q["axes"]


def parse_array(v, n):
    """Postgres array text '{1,2,NULL}' (or a JSON list) -> list of floats/None, or None if missing."""
    if v is None or (isinstance(v, float) and math.isnan(v)) or v == "":
        return None
    if isinstance(v, list):
        items = v
    else:
        s = str(v).strip()
        if s.startswith("["):
            items = json.loads(s)
        else:
            items = [x.strip() for x in s.strip("{}").split(",")] if s.strip("{}") else []
    out = [None if (x is None or str(x).upper() == "NULL" or str(x) == "") else float(x) for x in items]
    return out if len(out) == n else None


def pad(a, n):
    """Rows saved under an earlier version of part 2 (42, 61 or 62 answers): pad them with blanks."""
    return a + [None] * (n - len(a)) if a else None


def load(path):
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "about": parse_array(r.get("about"), len(Q["about"])),
            "p1": parse_array(r.get("answers"), len(Q["part1"])) or next((pad(x, len(Q["part1"])) for x in (parse_array(r.get("answers"), n) for n in (50, 48, 36)) if x), None),
            "p2": parse_array(r.get("answers2"), len(Q["part2"])) or next((pad(x, len(Q["part2"])) for x in (parse_array(r.get("answers2"), n) for n in (71, 70, 69, 68, 65, 64, 63, 62, 61, 42)) if x), None),
        })
    return rows


def demo(n=600, seed=7):
    """Made-up respondents with a few planted links, so the report has something to find."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        trad = rng.normal()          # a hidden 'traditional' trait that drives several axes
        devo = rng.normal()          # a hidden 'devotional' trait
        lat = {"m": trad, "i": .6 * devo + .3 * trad, "e": .4 * trad, "c": .8 * trad, "w": rng.normal(), "pl": .5 * trad,
               "u": .5 * devo, "r": .8 * devo, "s": .5 * trad + .3 * rng.normal(), "g": .4 * trad, "p": -.3 * devo, "a": .5 * trad}

        def slider(axis, key):
            x = key * lat[axis] + rng.normal(scale=.9)
            return float(np.clip(round(50 + 22 * x), 0, 100))
        p1 = [slider(q["axis"], q["key"]) for q in Q["part1"]]
        lat.update({"f": rng.normal(), "kb": .5 * lat["w"] + rng.normal(scale=.5), "mh": .4 * lat["w"], "io": .5 * trad,
                    "rl": .6 * trad, "mj": .5 * trad, "rb": .4 * trad, "id": rng.normal(), "sc": .3 * devo})
        p2 = []
        for q in Q["part2"]:
            if q["type"] == "slider" and q["axis"]:
                p2.append(slider(q["axis"], q["key"]))
            elif q["type"] == "slider":                       # unscored slider (mut'ah)
                p2.append(float(np.clip(round(50 - 15 * trad + rng.normal(scale=20)), 0, 100)))
            else:
                k = len(q["options"])
                if q["id"] == "car":                          # planted: devotional people pick latmiyya
                    w = np.array([1.0, 1 + 2.5 * max(devo, 0), 1.0, 1 + 2 * max(-trad, 0), .6])
                    p2.append(float(rng.choice(k, p=w / w.sum())))
                else:
                    p2.append(float(rng.integers(k)) if rng.random() > .1 else None)
        about = [float(rng.integers(len(q["options"]))) if rng.random() > .15 else None for q in Q["about"]]
        rows.append({"about": about, "p1": p1 if rng.random() > .2 else None, "p2": p2 if rng.random() > .1 else None})
    return rows


def axis_scores(rows):
    recs = []
    for r in rows:
        s = {}
        for part, key in (("part1", "p1"), ("part2", "p2")):
            ans = r[key]
            if ans is None:
                continue
            tot, cnt = {}, {}
            for q, v in zip(Q[part], ans):
                if not q["axis"] or q["type"] != "slider" or v is None:
                    continue
                tot[q["axis"]] = tot.get(q["axis"], 0) + q["key"] * (v - 50) / 50
                cnt[q["axis"]] = cnt.get(q["axis"], 0) + 1
            s.update({a: tot[a] / cnt[a] for a in tot})
        recs.append(s)
    return pd.DataFrame(recs, columns=list(AXES))


def opt(q, arr, j):
    if not arr or arr[j] is None:
        return None
    k = int(arr[j])
    return q["options"][k] if 0 <= k < len(q["options"]) else None


def categorical(rows):
    """One column per multiple-choice question (About you + unscored habits), holding the option label."""
    cols = {}
    for j, q in enumerate(Q["about"]):
        cols["about:" + q["id"]] = [opt(q, r["about"], j) for r in rows]
    for j, q in enumerate(Q["part2"]):
        if q["type"] == "choice":
            cols[q["id"]] = [opt(q, r["p2"], j) for r in rows]
    return pd.DataFrame(cols)


def sliders(rows):
    """One column per slider statement, 0..100, oriented as written (not reversed)."""
    cols = {}
    for part, key in (("part1", "p1"), ("part2", "p2")):
        for j, q in enumerate(Q[part]):
            if q["type"] == "slider":
                cols[(part, j)] = [r[key][j] if r[key] and r[key][j] is not None else np.nan for r in rows]
    return pd.DataFrame(cols)


def label(part, j):
    q = Q[part][j]
    ax = AXES[q["axis"]]["name"] if q["axis"] else "unscored"
    return f"{'P1' if part == 'part1' else 'P2'}-{j + 1:02d} [{ax}] {q['text']}"


def varimax(L, iters=100, tol=1e-6):
    p, k = L.shape
    R = np.eye(k)
    d = 0
    for _ in range(iters):
        Lr = L @ R
        u, s, vt = np.linalg.svd(L.T @ (Lr ** 3 - Lr @ np.diag(np.sum(Lr ** 2, axis=0)) / p))
        R = u @ vt
        d_new = np.sum(s)
        if d_new < d * (1 + tol):
            break
        d = d_new
    return L @ R


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="CSV export of the results table")
    ap.add_argument("--demo", action="store_true", help="use made-up data")
    ap.add_argument("--min-group", type=int, default=30, help="smallest group size to report (default 30)")
    ap.add_argument("--factors", type=int, default=6, help="number of hidden dimensions to extract (default 6)")
    ap.add_argument("--out", default=os.path.join(HERE, "report.html"))
    a = ap.parse_args()
    if not a.csv and not a.demo:
        ap.error("give a CSV file, or --demo")
    rows = demo() if a.demo else load(a.csv)
    # Retired questions keep their slot in the stored arrays but are no longer asked or scored.
    for r in rows:
        for part, key in (("part1", "p1"), ("part2", "p2")):
            if r.get(key):
                r[key] = [None if q.get("retired") else v for q, v in zip(Q[part], r[key])]
    n = len(rows)
    scores, cats, sl = axis_scores(rows), categorical(rows), sliders(rows)
    html = [f"<h1>Shia Compass · patterns</h1><p>{n} shared results{' (made-up demo data)' if a.demo else ''}. "
            f"Part 1 answered by {sum(r['p1'] is not None for r in rows)}, part 2 by {sum(r['p2'] is not None for r in rows)}. "
            f"Groups under {a.min_group} people are not shown.</p>"]

    # 1. axis overview
    html.append("<h2>1. Where people sit</h2><table><tr><th>Axis</th><th>People</th><th>Average</th><th>Spread (SD)</th><th>Leaning</th></tr>")
    for k, v in AXES.items():
        col = scores[k].dropna()
        if len(col) < a.min_group:
            continue
        m = col.mean()
        html.append(f"<tr><td>{esc(v['name'])}</td><td>{len(col)}</td><td>{m:+.2f}</td><td>{col.std():.2f}</td>"
                    f"<td>{round((m + 1) * 50)}% {esc(v['pos'])} / {100 - round((m + 1) * 50)}% {esc(v['neg'])}</td></tr>")
    html.append("</table>")

    # 2. habits / about-you vs axes
    html.append("<h2>2. What goes with what: answers to the multiple-choice questions</h2>"
                "<p>For each answer, how its group differs from everyone else on each axis, in standard deviations "
                "(0.2 small, 0.5 medium, 0.8 large). Only differences of at least 0.3 are listed.</p>")
    sd = scores.std()
    for col in cats.columns:
        found = []
        for opt, idx in cats.groupby(col).groups.items():
            if len(idx) < a.min_group:
                continue
            rest = scores.drop(index=idx)
            for k in AXES:
                g, o = scores.loc[idx, k].dropna(), rest[k].dropna()
                if len(g) < a.min_group or len(o) < a.min_group or not sd[k]:
                    continue
                d = (g.mean() - o.mean()) / sd[k]
                if abs(d) >= .3:
                    pole = AXES[k]["pos"] if d > 0 else AXES[k]["neg"]
                    found.append((abs(d), f"<tr><td>{esc(opt)}</td><td>{len(g)}</td><td>more <b>{esc(pole)}</b> on {esc(AXES[k]['name'].lower())}</td><td>{d:+.2f}</td></tr>"))
        title = col.replace("about:", "About you: ")
        qtext = next((q["text"] for q in Q["about"] + Q["part2"] if q["id"] == col.replace("about:", "")), col)
        html.append(f"<h3>{esc(title)}</h3><p class='q'>{esc(qtext)}</p>")
        if found:
            html.append("<table><tr><th>Answer</th><th>People</th><th>Tend to be</th><th>Effect</th></tr>" + "".join(r for _, r in sorted(found, reverse=True)) + "</table>")
        else:
            html.append("<p class='muted'>Nothing notable yet.</p>")

    # unscored slider items (e.g. mut'ah) vs axes
    unsc = [c for c in sl.columns if not Q[c[0]][c[1]]["axis"]]
    if unsc:
        html.append("<h3>Unscored statements</h3><table><tr><th>Statement</th><th>Strongest links with axes (correlation)</th></tr>")
        for c in unsc:
            r = scores.apply(lambda s: s.corr(sl[c]) if s.notna().sum() >= a.min_group else np.nan).dropna()
            r = r.reindex(r.abs().sort_values(ascending=False).index)[:3]
            html.append(f"<tr><td>{esc(Q[c[0]][c[1]]['text'])}</td><td>" + "; ".join(
                f"{esc(AXES[k]['pos'] if v > 0 else AXES[k]['neg'])} on {esc(AXES[k]['name'].lower())} ({v:+.2f})" for k, v in r.items()) + "</td></tr>")
        html.append("</table>")

    # 3. statement-to-statement links across different axes
    html.append("<h2>3. Links the labels don't predict</h2><p>The strongest correlations between statements written for <em>different</em> axes "
                "(Spearman, statements as worded: a negative value means agreeing with one goes with disagreeing with the other).</p>")
    keep = [c for c in sl.columns if sl[c].notna().sum() >= a.min_group]
    C = sl[keep].corr(method="spearman", min_periods=a.min_group)
    pairs = []
    for x in range(len(keep)):
        for y in range(x + 1, len(keep)):
            qa, qb = Q[keep[x][0]][keep[x][1]], Q[keep[y][0]][keep[y][1]]
            if qa["axis"] == qb["axis"]:
                continue
            v = C.iat[x, y]
            if not np.isnan(v):
                pairs.append((abs(v), v, keep[x], keep[y]))
    pairs.sort(reverse=True)
    html.append("<table><tr><th>r</th><th>Statement</th><th>Statement</th></tr>")
    for _, v, ca, cb in pairs[:25]:
        html.append(f"<tr><td>{v:+.2f}</td><td>{esc(label(*ca))}</td><td>{esc(label(*cb))}</td></tr>")
    html.append("</table>")

    # 4. hidden dimensions
    X = sl[keep]
    complete = X.dropna()
    if len(complete) >= max(a.min_group, 3 * a.factors):
        Z = (complete - complete.mean()) / complete.std(ddof=0).replace(0, 1)
        corr = np.corrcoef(Z.values, rowvar=False)
        w, V = np.linalg.eigh(corr)
        order = np.argsort(w)[::-1]
        w, V = w[order], V[:, order]
        k = a.factors
        L = varimax(V[:, :k] * np.sqrt(w[:k]))
        explained = w[:k] / w.sum()
        html.append(f"<h2>4. Hidden dimensions</h2><p>{k} dimensions extracted from {len(keep)} statements and {len(complete)} people who answered all of them "
                    f"({explained.sum():.0%} of the variation). Each lists the statements that move together most strongly. "
                    "If a dimension mixes statements from several axes, people are answering along a line the labels don't name.</p>")
        for f in range(k):
            load_ = L[:, f]
            top = np.argsort(-np.abs(load_))[:8]
            ax_mix = pd.Series([Q[keep[t][0]][keep[t][1]]["axis"] for t in top]).value_counts()
            mix = ", ".join(f"{AXES[x]['name'] if x else 'unscored'} ×{c}" for x, c in ax_mix.items())
            html.append(f"<h3>Dimension {f + 1} · {explained[f]:.0%} · {esc(mix)}</h3><table><tr><th>Loading</th><th>Statement</th></tr>" +
                        "".join(f"<tr><td>{load_[t]:+.2f}</td><td>{esc(label(*keep[t]))}</td></tr>" for t in top) + "</table>")
    else:
        html.append("<h2>4. Hidden dimensions</h2><p class='muted'>Not enough people have answered every statement yet.</p>")

    css = ("body{font-family:system-ui,sans-serif;max-width:1000px;margin:24px auto;padding:0 16px;color:#0B2233;line-height:1.45}"
           "table{border-collapse:collapse;width:100%;margin:8px 0 18px;font-size:14px}td,th{border-bottom:1px solid #DCE4EA;padding:6px 8px;text-align:left;vertical-align:top}"
           "th{background:#F6F9FA}h2{margin-top:36px;color:#0E6E72}h3{margin:22px 0 2px}.q{margin:0 0 6px;color:#3D5566}.muted{color:#3D5566}")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><meta charset='utf-8'><title>Shia Compass patterns</title><style>{css}</style>" + "\n".join(html))
    print(f"Wrote {a.out} ({n} results)")


if __name__ == "__main__":
    main()
