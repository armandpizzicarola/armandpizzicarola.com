# armandpizzicarola.com

Static personal site. Armand writes privately in Notion; this repo holds the
published copy as markdown and the plain HTML built from it. GitHub Pages
serves the `docs/` folder as-is.

## Layout

- `content/posts/YYYY-MM-DD-slug.md` — Ramblings (essays and reading notes)
- `content/pages/*.md` — About, Reading
- `assets/` — images, referenced in markdown as `/assets/<file>`
- `site.json` — name, homepage bio, links, structured-data fields
- `style.css` — the whole design (inlined into every page)
- `build.py` — builds everything into `docs/` (needs `pip install markdown`)
- `docs/` — generated output. Never edit by hand; always commit it after a build.

## Publishing a post from Notion

When asked to "publish <title> from Notion":

1. Find the page in the Notion "Ramblings" database (under Site / Armand Pizzicarola)
   and fetch it with the Notion connector.
2. Create `content/posts/<Date property>-<slug>.md` with front matter:
   `title`, `date` (the Notion Date property), `notion_id` (32-char page id, no dashes).
   Quote the title if it contains a colon or starts with `[`.
3. Convert the body to plain markdown. Keep Armand's wording exactly, typos included;
   do not edit, tidy or summarize his prose.
   - Links to other Notion pages become `[text](notion:<32-char id>)`; the build
     resolves them to local pages, or to plain text if that page is not migrated.
   - Download images into `assets/` (Notion file links expire) and reference them
     as `![alt](/assets/<file>)`.
   - Embedded tweets: link to the tweet URL.
4. If the book is new, add it to `content/pages/reading.md` under the right year.
5. Run `python3 build.py`, check the new page in `docs/`, then commit and push.

To update an existing post, find it by `notion_id`, re-fetch, and overwrite the body.

## Rules

- Only publish pages Armand names. Drafts stay in Notion.
- Post URLs are `/ramblings/<slug>/`. Do not rename a published file; that changes its URL.
- `custom_domain` in `site.json` is empty while testing on github.io. Set it to
  `www.armandpizzicarola.com` only when the domain is being switched over.
