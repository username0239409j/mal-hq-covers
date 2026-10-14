#!/usr/bin/env python3
"""Build hq_example.css - high-res cover overrides for MAL custom CSS.

Usage:
    python make_hq.py animelist.xml mangalist.xml [-o hq_example.css]
    python make_hq.py --user THEIR_USERNAME [-o hq_example.css]
    python make_hq.py --anime anime.html --manga manga.html [-o hq_example.css]

Takes official MAL exports (from https://myanimelist.net/panel.php?go=export),
reads your username out of them, fetches your PUBLIC lists for cover URLs,
and writes one hq_example.css. Or skip the files: --user fetches both lists
directly (they must be Public). Host it somewhere serving text/css,
then paste this as the FIRST line of the MAL custom CSS box
(Modern list style):

    @import url("HOSTED-URL-GOES-HERE");

Re-run when titles are added. Needs Python 3 only (no other packages).
"""
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
QUOT = "&quot;"


def parse_export(path):
    """(username, entries) from an official MAL XML export."""
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        sys.exit("Cannot parse %s (%s). Use official MAL exports." % (path, e))
    username = ""
    info = root.find("myinfo")
    if info is not None:
        username = (info.findtext("user_name") or "").strip()
    entries = []
    for el in root.findall("anime"):
        entries.append(("anime",
                        (el.findtext("series_animedb_id") or "").strip(),
                        (el.findtext("series_title") or "untitled").strip()))
    for el in root.findall("manga"):
        entries.append(("manga",
                        (el.findtext("manga_mangadb_id") or "").strip(),
                        (el.findtext("manga_title") or "untitled").strip()))
    entries = [(k, i, t) for k, i, t in entries if i]
    if not entries:
        sys.exit("No entries in %s. Wrong file?" % path)
    return username, entries


def fetch_list(user, kind):
    page = "animelist" if kind == "anime" else "mangalist"
    req = urllib.request.Request(
        "https://myanimelist.net/%s/%s" % (page, user), headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        sys.exit("Could not load %s list for '%s' (%s).\n"
                 "Lists must be Public (no login supported)."
                 % (kind, user, e))


def normalize(text):
    return (text.replace("&quoquot;", QUOT)
                .replace("&quotquot;", QUOT)
                .replace("&qquot;", QUOT))


def split_objects(line):
    start = line.find("data-items=")
    if start < 0:
        return []
    i = line.find("[", start)
    if i < 0:
        return []
    objs, depth, obj_start, instr = [], 1, None, False
    n = len(line)
    i += 1
    while i < n:
        if line.startswith(QUOT, i):
            instr = not instr
            i += len(QUOT)
            continue
        if not instr:
            ch = line[i]
            if ch in "{[":
                if ch == "{" and depth == 1:
                    obj_start = i
                depth += 1
            elif ch in "}]":
                depth -= 1
                if ch == "}" and depth == 1 and obj_start is not None:
                    objs.append(line[obj_start:i + 1])
                    obj_start = None
                if depth == 0:
                    break
        i += 1
    return objs


def field(obj, name):
    m = re.search(QUOT + re.escape(name) + QUOT + ":" + QUOT +
                  "((?:(?!" + QUOT + ").)*)" + QUOT, obj)
    if m:
        return m.group(1)
    num_pat = r"(-?[\d.]+|true|false|null)"
    m = re.search(QUOT + re.escape(name) + QUOT + ":" + num_pat, obj)
    return m.group(1) if m else ""


def live_paths(text):
    """(kind, mal_id) -> (image path, title, english title), from a list page."""
    out = {}
    for line in text.splitlines():
        if "data-items=" not in line:
            continue
        for obj in split_objects(line):
            kind = ("anime" if "anime_image_path" in obj
                    else "manga" if "manga_image_path" in obj else "")
            if not kind:
                continue
            mid = field(obj, "anime_id" if kind == "anime" else "manga_id")
            path = field(obj, kind + "_image_path").replace("\\/", "/")
            title = html.unescape(field(obj, kind + "_title")) or "untitled"
            title = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), title)
            eng = html.unescape(field(obj, kind + "_title_eng"))
            eng = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), eng)
            if mid and path:
                out[(kind, mid)] = (path, title, eng)
    return out


def hq_pair(lq_path):
    base = re.sub(r"/r/\d+x\d+(?=/images/)", "", lq_path, count=1)
    base = base.split("?")[0]
    stem = base.rsplit(".", 1)[0]
    return stem + "l.jpg", base


def fragment(lq_path):
    tail = lq_path.split("/images/")[-1].split("?")[0]
    if "." in tail.rsplit("/", 1)[-1]:
        tail = tail.rsplit(".", 1)[0] + "."
    return "/" + tail


def rule(title, frag, hi, lo, eng=""):
    safe = re.sub(r"[^\x00-\x7F]+", "", str(title)).strip() or "untitled"
    eng_safe = re.sub(r"[^\x00-\x7F]+", "", str(eng or "")).strip()
    if eng_safe and eng_safe.lower() != safe.lower():
        safe += " / " + eng_safe
    return (
        "/* HQ cover: " + safe + " */\n"
        ".list-table .data.image:has(img[src*=\"" + frag + "\"]) "
        ".link{background-image:url(\"" + hi + "\"), url(\"" + lo + "\") "
        "!important;background-size:cover !important;"
        "background-position:center center !important;"
        "background-repeat:no-repeat !important;}\n"
        ".list-table .data.image:has(img[src*=\"" + frag + "\"]) "
        "img{opacity:0 !important;}\n"
    )


def load_page(path):
    """Page source text from a raw save or a view-source wrapper save."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    if "line-content" in raw and "html-attribute-value" in raw:
        cells = re.findall(r'<td class="line-content">(.*?)</td>', raw, re.S)
        lines = []
        for c in cells:
            c = re.sub(r"<br\s*/?>", "", c)
            c = re.sub(r"<[^>]+>", "", c)
            lines.append(c)
        return html.unescape("\n".join(lines))
    return raw


def main(argv):
    files, out, user, pages = [], "hq_example.css", "", {}
    it = iter(argv)
    for a in it:
        if a in ("-o", "--output"):
            out = next(it)
        elif a == "--user":
            user = next(it)
        elif a in ("--anime", "--manga"):
            pages[a[2:]] = next(it)
        elif a.startswith("-"):
            sys.exit("usage: make_hq.py animelist.xml mangalist.xml [-o hq_example.css]\n"
                     "   or: make_hq.py --user USERNAME [-o hq_example.css]\n"
                     "   or: make_hq.py --anime A.html --manga M.html [-o hq_example.css]")
        else:
            files.append(a)
    entries, paths = [], {}
    if user:
        for kind in ("anime", "manga"):
            for (k, mid), (path, title, eng) in live_paths(
                    normalize(fetch_list(user, kind))).items():
                entries.append((k, mid, title, eng))
                paths[(k, mid)] = (path, eng)
    elif pages:
        for kind in ("anime", "manga"):
            if kind in pages:
                for (k, mid), (path, title, eng) in live_paths(
                        normalize(load_page(pages[kind]))).items():
                    entries.append((k, mid, title, eng))
                    paths[(k, mid)] = (path, eng)
        if not entries:
            sys.exit("No entries found in those pages. Wrong files?")
    else:
        if not files:
            sys.exit("usage: make_hq.py animelist.xml mangalist.xml [-o hq_example.css]\n"
                     "   or: make_hq.py --user USERNAME [-o hq_example.css]\n"
                     "   or: make_hq.py --anime A.html --manga M.html [-o hq_example.css]")
        username = ""
        for p in files:
            u, es = parse_export(p)
            username = username or u
            entries.extend(es)
        if not username:
            sys.exit("No username in the exports. Re-export from MAL and retry.")
        kinds = set(k for k, _, _ in entries)
        for kind in ("anime", "manga"):
            if kind in kinds:
                for (k, mid), (path, _t, eng) in live_paths(
                        normalize(fetch_list(username, kind))).items():
                    paths[(k, mid)] = (path, eng)
    rules, seen, missing = [], set(), []
    for entry in entries:
        kind, mid, title = entry[0], entry[1], entry[2]
        eng = entry[3] if len(entry) > 3 else ""
        got = paths.get((kind, mid))
        if not got:
            missing.append("%s %s" % (kind, title))
            continue
        path, live_eng = got
        hi, lo = hq_pair(path)
        frag = fragment(path)
        if frag in seen:
            continue
        seen.add(frag)
        rules.append((frag, rule(title, frag, hi, lo, live_eng or eng)))
    rules = [text for _, text in sorted(rules)]
    head = ("/* HQ covers - auto-included via @import.\n"
            "   Regenerated when titles are added. */\n")
    with open(out, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(rules))
    print("Wrote %s: %d HQ cover rules." % (out, len(rules)))
    if missing:
        print("No live cover found for %d entries (left on thumbnails):"
              % len(missing))
        for m in missing[:10]:
            print("  -", m)
    print("")
    print("HOST IT (pick one):")
    print("  1. GitHub: new PUBLIC repo, push %s, use" % out)
    print("     https://cdn.jsdelivr.net/gh/USER/REPO@main/%s" % out)
    print("     (replace USER/REPO; purge cache after updates:")
    print("      https://purge.jsdelivr.net/gh/USER/REPO@main/%s)" % out)
    print("  2. Cloudflare R2 / Netlify Drop / Vercel: upload the file,")
    print("     use the URL they give you (must serve as text/css).")
    print("Then paste this as the FIRST line of the MAL custom CSS box:")
    print('  @import url("HOSTED-URL-GOES-HERE");')


if __name__ == "__main__":
    main(sys.argv[1:])
