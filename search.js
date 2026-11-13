// Site search: a ⌘K palette over a prebuilt index (search.json). No dependencies.
(function () {
  "use strict";
  var root = (document.querySelector("script[data-root]") || {}).dataset.root || "";
  var ICON = {
    page: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>',
    post: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>'
  };
  var svg = function (k) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + ICON[k] + "</svg>"; };
  var esc = function (s) { return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ");
  var nice = function (iso) { var d = iso.split("-"); return MONTHS[+d[1] - 1] + " " + (+d[2]) + ", " + d[0]; };

  // ---- markup -------------------------------------------------------------
  var nav = document.querySelector("header nav");
  var trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "search-trigger";
  trigger.innerHTML = svg("search") + "Search<kbd>⌘K</kbd>";
  if (nav) { nav.appendChild(document.createTextNode(" · ")); nav.appendChild(trigger); }

  var dlg = document.createElement("dialog");
  dlg.className = "search";
  dlg.innerHTML =
    '<div class="search-box">' + svg("search") +
    '<input type="search" placeholder="Search…" autocomplete="off" spellcheck="false" aria-label="Search">' +
    '<button type="button" class="search-close" aria-label="Close"><kbd>esc</kbd></button></div>' +
    '<ol class="search-results"></ol>' +
    '<div class="search-foot"><span><kbd>↑</kbd><kbd>↓</kbd> navigate</span><span><kbd>↵</kbd> open</span></div>';
  document.body.appendChild(dlg);
  var input = dlg.querySelector("input"), list = dlg.querySelector("ol");

  // ---- index --------------------------------------------------------------
  var items = null, loading = null;
  function load() {
    if (items || loading) return loading;
    loading = fetch(root + "search.json").then(function (r) { return r.json(); }).then(function (data) {
      items = data.map(function (it) { it.lt = it.t.toLowerCase(); it.lx = it.x.toLowerCase(); return it; });
      render();
    });
    return loading;
  }

  // ---- search -------------------------------------------------------------
  function search(q) {
    var terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) {
      return items.filter(function (it) { return it.k === "post"; }).slice(0, 8)
        .map(function (it) { return { it: it, snip: "" }; });
    }
    var out = [];
    items.forEach(function (it) {
      var score = 0, first = -1;
      for (var i = 0; i < terms.length; i++) {
        var t = terms[i], inTitle = it.lt.indexOf(t), inText = it.lx.indexOf(t);
        if (inTitle < 0 && inText < 0) return;
        if (inTitle >= 0) score += 10;
        if (inText >= 0) { score += 1; if (first < 0 || inText < first) first = inText; }
      }
      out.push({ it: it, score: score, snip: first >= 0 ? snippet(it.x, first, terms) : "" });
    });
    out.sort(function (a, b) { return b.score - a.score || (b.it.d || "").localeCompare(a.it.d || ""); });
    return out.slice(0, 12);
  }

  function snippet(text, at, terms) {
    var start = Math.max(0, at - 50), end = Math.min(text.length, at + 110);
    if (start > 0) start = text.lastIndexOf(" ", start) + 1;
    var s = (start > 0 ? "…" : "") + text.slice(start, end) + (end < text.length ? "…" : "");
    return mark(s, terms);
  }

  function mark(text, terms) {
    if (!terms.length) return esc(text);
    var re = new RegExp("(" + terms.map(function (t) { return t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }).join("|") + ")", "ig");
    return text.split(re).map(function (part, i) { return i % 2 ? "<mark>" + esc(part) + "</mark>" : esc(part); }).join("");
  }

  // ---- render -------------------------------------------------------------
  var sel = 0, results = [];
  function render() {
    if (!items) return;
    var q = input.value.trim(), terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    results = search(q);
    sel = 0;
    if (!results.length) {
      list.innerHTML = '<li class="search-empty">No results for “' + esc(q) + "”</li>";
      return;
    }
    list.innerHTML = (q ? "" : '<li class="search-label">Recent</li>') + results.map(function (r, i) {
      var it = r.it;
      return '<li' + (i === sel ? ' class="sel"' : "") + '><a href="' + root + it.u + '">' + svg(it.k) +
        '<span class="search-title">' + mark(it.t, terms) + "</span>" +
        (it.d ? '<span class="search-date">' + nice(it.d) + "</span>" : "<span></span>") +
        (r.snip ? '<span class="search-snip">' + r.snip + "</span>" : "") + "</a></li>";
    }).join("");
  }

  function move(delta) {
    var rows = list.querySelectorAll("li:not(.search-label):not(.search-empty)");
    if (!rows.length) return;
    rows[sel].classList.remove("sel");
    sel = (sel + delta + rows.length) % rows.length;
    rows[sel].classList.add("sel");
    rows[sel].scrollIntoView({ block: "nearest" });
  }

  // ---- open / close -------------------------------------------------------
  function open() {
    if (dlg.open) return;
    dlg.showModal();
    input.value = "";
    input.focus();
    load();
    render();
  }
  function close() { if (dlg.open) dlg.close(); }

  trigger.addEventListener("click", open);
  dlg.querySelector(".search-close").addEventListener("click", close);
  dlg.addEventListener("click", function (e) { if (e.target === dlg) close(); });
  input.addEventListener("input", render);
  input.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter") {
      var a = list.querySelector("li.sel a");
      if (a) { e.preventDefault(); location.href = a.href; }
    }
  });
  document.addEventListener("keydown", function (e) {
    var typing = /^(input|textarea|select)$/i.test((e.target.tagName || "")) || e.target.isContentEditable;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); dlg.open ? close() : open(); }
    else if (e.key === "/" && !typing && !dlg.open) { e.preventDefault(); open(); }
  });
  if (!/Mac|iPhone|iPad/.test(navigator.platform)) trigger.querySelector("kbd").textContent = "Ctrl K";
})();
