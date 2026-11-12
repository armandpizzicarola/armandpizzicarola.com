#!/usr/bin/env python3
"""Build the site: content/*.md -> docs/*.html (plain, server-readable HTML).

Usage:  python3 build.py
Needs:  pip install markdown
"""
import datetime, html, json, pathlib, re, shutil
import markdown

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "docs"
SITE = json.loads((ROOT / "site.json").read_text())
CSS = (ROOT / "style.css").read_text()


def parse(path):
    """Split a markdown file into (front-matter dict, body)."""
    text = path.read_text()
    meta = {}
    if text.startswith("---\n"):
        head, text = text[4:].split("\n---\n", 1)
        for line in head.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
    return meta, text.strip() + "\n"


def slug_of(path):
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)


def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}, {d.year}"


# ---- load content -----------------------------------------------------------
posts = []
for p in sorted((ROOT / "content/posts").glob("*.md")):
    meta, body = parse(p)
    posts.append({**meta, "body": body, "slug": slug_of(p), "path": f"ramblings/{slug_of(p)}/"})
posts.sort(key=lambda x: x["date"], reverse=True)

pages = []
for p in sorted((ROOT / "content/pages").glob("*.md")):
    meta, body = parse(p)
    pages.append({**meta, "body": body, "slug": p.stem, "path": f"{p.stem}/"})

# Links written as notion:<page id> resolve to the local page if it has been
# migrated, and fall back to plain text if it has not.
by_notion = {x["notion_id"]: x["path"] for x in posts + pages if x.get("notion_id")}
by_notion.update(SITE.get("notion_aliases", {}))


def render(body, prefix):
    def link(m):
        target = by_notion.get(m.group(2))
        return f"[{m.group(1)}]({prefix}{target})" if target is not None else m.group(1)

    body = re.sub(r"\[([^\]]+)\]\(notion:([0-9a-f]{32})\)", link, body)
    body = body.replace("](/assets/", f"]({prefix}assets/")
    return markdown.markdown(body, extensions=["extra", "sane_lists"])


def page(path, title, content, description, extra_head=""):
    depth = path.count("/")
    prefix = "../" * depth
    full_title = SITE["name"] if not title else f"{title} | {SITE['name']}"
    url = SITE["url"].rstrip("/") + "/" + path
    nav = " · ".join(
        f'<a href="{prefix}{href}">{label}</a>'
        for label, href in [("About", "about/"), ("Ramblings", "ramblings/"), ("Reading", "reading/")]
    )
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(full_title)}</title>
<meta name="description" content="{html.escape(description, quote=True)}">
<meta name="author" content="{html.escape(SITE['name'])}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{html.escape(full_title, quote=True)}">
<meta property="og:description" content="{html.escape(description, quote=True)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
{extra_head}<style>
{CSS}</style>
</head>
<body>
<header><a class="home" href="{prefix or './'}">{html.escape(SITE['name'])}</a><nav>{nav}</nav></header>
<main>
{content}
</main>
<footer>{SITE['footer']}</footer>
</body>
</html>
"""
    dest = OUT / path / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(doc)


def first_words(body, n=28):
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", body)
    text = re.sub(r"[#*_>`]|<[^>]+>", "", text)
    words = text.split()
    return " ".join(words[:n]) + ("…" if len(words) > n else "")


def post_list(items, prefix):
    rows = "\n".join(
        f'<li><time datetime="{p["date"]}">{nice_date(p["date"])}</time>'
        f'<a href="{prefix}{p["path"]}">{html.escape(p["title"])}</a></li>'
        for p in items
    )
    return f'<ul class="posts">\n{rows}\n</ul>'


# ---- write site -------------------------------------------------------------
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
(OUT / ".nojekyll").write_text("")
if (ROOT / "assets").exists():
    shutil.copytree(ROOT / "assets", OUT / "assets")
if SITE.get("custom_domain"):
    (OUT / "CNAME").write_text(SITE["custom_domain"] + "\n")

person = {
    "@context": "https://schema.org",
    "@type": "Person",
    "name": SITE["name"],
    "url": SITE["url"],
    "jobTitle": SITE["job_title"],
    "worksFor": {"@type": "Organization", "name": SITE["works_for"]},
    "sameAs": SITE["same_as"],
}
person_ld = f'<script type="application/ld+json">{json.dumps(person)}</script>\n'

# Home
home = f"""<h1>{html.escape(SITE['name'])}</h1>
<p class="lede">{SITE['bio_html']}</p>
<h2>Recent ramblings</h2>
{post_list(posts[:8], "")}
<p><a href="ramblings/">All ramblings →</a></p>"""
page("", "", home, SITE["description"], person_ld)

# Pages (About, Reading, ...)
for p in pages:
    body = f"<h1>{html.escape(p['title'])}</h1>\n" + render(p["body"], "../")
    page(p["path"], p["title"], body, p.get("description") or first_words(p["body"]))

# Ramblings index
idx = f"<h1>Ramblings</h1>\n<p class=\"lede\">{html.escape(SITE['ramblings_note'])}</p>\n" + post_list(posts, "../")
page("ramblings/", "Ramblings", idx, "Essays and reading notes by " + SITE["name"] + ".")

# Posts (HTML plus a raw markdown copy for agents)
for p in posts:
    article_ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": p["title"],
        "datePublished": p["date"],
        "author": {"@type": "Person", "name": SITE["name"], "url": SITE["url"]},
    }
    head = f'<script type="application/ld+json">{json.dumps(article_ld)}</script>\n'
    body = (
        f"<article>\n<h1>{html.escape(p['title'])}</h1>\n"
        f'<p class="meta">{html.escape(SITE["name"])} · <time datetime="{p["date"]}">{nice_date(p["date"])}</time></p>\n'
        + render(p["body"], "../../")
        + "\n</article>"
    )
    page(p["path"], p["title"], body, p.get("description") or first_words(p["body"]), head)
    (OUT / "ramblings" / f"{p['slug']}.md").write_text(
        f"# {p['title']}\n\nBy {SITE['name']} · {p['date']}\n\n"
        + re.sub(
            r"\[([^\]]+)\]\(notion:([0-9a-f]{32})\)",
            lambda m: f"[{m.group(1)}]({SITE['url']}{by_notion[m.group(2)]})" if m.group(2) in by_notion else m.group(1),
            p["body"],
        ).replace("](/assets/", f"]({SITE['url']}assets/")
    )

# llms.txt, sitemap.xml, robots.txt
base = SITE["url"].rstrip("/")
llms = [f"# {SITE['name']}", "", f"> {SITE['description']}", "", "## Pages", ""]
llms += [f"- [{p['title']}]({base}/{p['path']})" for p in pages]
llms += ["", "## Ramblings (essays and reading notes, newest first)", ""]
llms += [f"- [{p['title']}]({base}/ramblings/{p['slug']}.md) ({p['date']})" for p in posts]
(OUT / "llms.txt").write_text("\n".join(llms) + "\n")

urls = [""] + [p["path"] for p in pages] + ["ramblings/"] + [p["path"] for p in posts]
(OUT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{base}/{u}</loc></url>\n" for u in urls)
    + "</urlset>\n"
)
(OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n")

print(f"Built {len(posts)} posts and {len(pages)} pages into {OUT}")
