// Resume template — modern two-column CV that ALWAYS fills its page.
//
// Page-as-canvas: the whole CV is built as a function of a scale factor `s`.
// At render time the template measures itself at several scales and picks the
// LARGEST one that still fits a single A4 sheet — so a shorter CV gets bigger
// type and more air instead of a half-empty page, and a dense CV steps down
// gracefully. (If even scale 1.0 overflows, it simply continues to page 2.)
//
// Conventions (documented in SKILL.md):
//   doc.title  = person's name, doc.author = role/tagline shown under the name
//   level-1 section = rubric (EXPERIENCE, SKILLS, …)
//   level-2 section = an entry inside the last rubric; title parsed as
//                     "Role — Company | dates" (company and dates optional)
//   rubrics matching the sidebar keywords (skills, education, languages,
//   certificates, interests) go to the right sidebar; a rubric named
//   contact(s)/контакты becomes the contact line in the header.
//   First image found in any section → round avatar in the header.
#import "helpers.typ": render-table, render-code, callout-box

#let doc = json("assets/content.json")
#let p = doc.at("preset", default: (:))

// ── Preset helpers ─────────────────────────────────────────────────────────────
#let body-font    = p.at("body_font",    default: "IBM Plex Sans")
#let heading-font = p.at("heading_font", default: "IBM Plex Sans")
#let mono-font    = p.at("mono_font",    default: "IBM Plex Mono")
#let accent-color = rgb(p.at("accent_color",  default: "#0f766e"))
#let head-color   = rgb(p.at("heading_color", default: "#111827"))
#let muted-color  = rgb(p.at("muted_color",   default: "#6b7280"))
#let body-color   = rgb(p.at("body_color",    default: "#1f2937"))
#let text-size    = eval(p.at("text_size", default: "10pt"),   mode: "code")
#let name-size    = eval(p.at("h1_size",   default: "27pt"),   mode: "code")
#let rubric-size  = eval(p.at("h2_size",   default: "9.5pt"),  mode: "code")
#let entry-size   = eval(p.at("h3_size",   default: "11pt"),   mode: "code")

#let m-left   = eval(p.at("margin_left",   default: "1.9cm"), mode: "code")
#let m-right  = eval(p.at("margin_right",  default: "1.9cm"), mode: "code")
#let m-top    = eval(p.at("margin_top",    default: "1.8cm"), mode: "code")
#let m-bottom = eval(p.at("margin_bottom", default: "1.8cm"), mode: "code")
#let avail-w  = 21cm   - m-left - m-right
#let avail-h  = 29.7cm - m-top  - m-bottom

#set page(
  paper: "a4",
  margin: (left: m-left, right: m-right, top: m-top, bottom: m-bottom),
)
#set text(font: body-font, fill: body-color, lang: doc.language)

#let safe(c) = c.replace("#", "\\#").replace("\\#link(", "#link(")

// ── Group flat sections into rubrics with entries ─────────────────────────────
#let groups = {
  let gs = ()
  let cur = none
  for s in doc.sections {
    if s.level == 1 {
      if cur != none { gs.push(cur) }
      cur = (head: s, entries: ())
    } else {
      if cur == none { cur = (head: none, entries: ()) }
      cur.entries.push(s)
    }
  }
  if cur != none { gs.push(cur) }
  gs
}

#let title-of(g)  = if g.head == none { "" } else { lower(g.head.title) }
#let is-contact(g) = ("контакт", "contact").any(k => title-of(g).contains(k))
#let is-side(g) = (
  "навык", "skill", "образован", "education", "язык", "language",
  "сертифик", "certif", "интерес", "interest", "стек", "stack",
).any(k => title-of(g).contains(k))

#let contact-groups = groups.filter(is-contact)
#let side-groups    = groups.filter(g => is-side(g) and not is-contact(g))
#let main-groups    = groups.filter(g => not is-side(g) and not is-contact(g))

// First image anywhere in the document → round header avatar.
#let avatar = {
  let found = none
  for s in doc.sections {
    if found == none and s.images.len() > 0 { found = s.images.first() }
  }
  found
}

// ── The whole CV as a function of scale `s` ───────────────────────────────────
// Font sizes are multiplied by s; every vertical distance is in em, so air
// grows in proportion automatically. s = 1.0 is the dense baseline.
#let cv(s) = {
  set text(font: body-font, size: text-size * s, fill: body-color, lang: doc.language)
  set par(justify: false, leading: 0.62em, spacing: 0.75em)
  show raw: set text(font: mono-font, size: 0.9em)
  set list(
    marker: box(baseline: -0.28em, circle(radius: 1.7pt * s, fill: accent-color)),
    indent: 1pt, body-indent: 0.65em, spacing: 0.7em,
  )

  let rubric(title) = {
    v(1.7em, weak: true)
    block(sticky: true)[
      #text(font: heading-font, size: rubric-size * s, weight: "bold",
            fill: accent-color, tracking: 0.13em)[#upper(title)]
      #v(-0.45em)
      #line(length: 100%, stroke: 0.6pt + accent-color.lighten(55%))
    ]
    v(0.8em, weak: true)
  }

  // "Role — Company | dates" → bold role, accent company, right-aligned dates.
  let entry(sct) = {
    let parts = sct.title.split("|").map(x => x.trim())
    let head  = parts.at(0)
    let dates = if parts.len() > 1 { parts.at(1) } else { "" }
    let hp    = head.split("—").map(x => x.trim())
    let role  = hp.at(0)
    let comp  = if hp.len() > 1 { hp.at(1) } else { "" }
    v(1.25em, weak: true)
    block(sticky: true)[
      #grid(columns: (1fr, auto), column-gutter: 0.8em,
        [
          #text(font: heading-font, size: entry-size * s, weight: "semibold", fill: head-color)[#role]
          #if comp != "" [ #text(fill: accent-color, weight: "medium")[· #comp] ]
        ],
        align(right + horizon)[#text(size: 0.85em, fill: muted-color)[#dates]],
      )
    ]
    v(0.75em, weak: true)
    eval(safe(sct.content), mode: "markup")
  }

  // Sidebar skills as pill chips when content is a single comma-separated line.
  let chips(content-str) = {
    set par(leading: 0.95em)
    let items = content-str.split(",").map(x => x.trim()).filter(x => x != "")
    for it in items {
      box(
        fill: accent-color.lighten(88%),
        radius: 3pt,
        inset: (x: 6pt * s, y: 3.5pt * s),
        text(size: 8.5pt * s, fill: accent-color.darken(15%), weight: "medium")[#it],
      )
      h(4pt)
    }
  }

  let side-block(g) = {
    rubric(g.head.title)
    let body = g.head.content.trim()
    if body != "" {
      if not body.contains("\n") and body.contains(",") and not body.contains("-") {
        chips(body)
      } else {
        eval(safe(body), mode: "markup")
      }
    }
    for e in g.entries {
      v(0.65em, weak: true)
      text(weight: "semibold", size: 0.95em, fill: head-color)[#e.title]
      v(0.3em, weak: true)
      text(size: 0.9em, fill: muted-color)[#eval(safe(e.content), mode: "markup")]
    }
  }

  // Header
  grid(
    columns: if avatar != none { (1fr, auto) } else { (1fr,) },
    column-gutter: 1.2em,
    [
      #text(font: heading-font, size: name-size * s, weight: "bold",
            fill: head-color, tracking: -0.01em)[#doc.title]
      #v(0.15em)
      #if doc.author != "" [
        #text(size: 12pt * s, fill: accent-color, weight: "medium")[#doc.author]
        #v(0.1em)
      ]
      #for g in contact-groups [
        #if g.head.content.trim() != "" [
          #text(size: 9pt * s, fill: muted-color)[
            #g.head.content.split("\n").map(x => x.trim()).filter(x => x != "").join([ #text(fill: accent-color)[·] ])
          ]
        ]
      ]
    ],
    ..if avatar != none {
      (box(clip: true, radius: 50%, width: 2.7cm * s, height: 2.7cm * s,
        image(avatar.at("_local", default: avatar.path), width: 2.7cm * s, height: 2.7cm * s, fit: "cover")),)
    } else { () },
  )
  v(0.8em)
  line(length: 100%, stroke: 1.4pt + accent-color)
  v(1.2em)

  // Two-column body (sidebar widens with the scale too)
  grid(
    columns: (1fr, 5.2cm * s),
    column-gutter: 1.1cm,
    [
      #for g in main-groups {
        if g.head != none { rubric(g.head.title) }
        if g.head != none and g.head.content.trim() != "" {
          eval(safe(g.head.content), mode: "markup")
        }
        for e in g.entries { entry(e) }
        for tbl in if g.head != none { g.head.tables } else { () } { render-table(tbl) }
        for cb in if g.head != none { g.head.code_blocks } else { () } { render-code(cb, mono-font) }
        for co in if g.head != none { g.head.callouts } else { () } { callout-box(co.at("text"), co.kind) }
      }
    ],
    [
      #for g in side-groups { side-block(g) }
    ],
  )
}

// ── Pick the largest scale that still fits ONE page ──────────────────────────
// Page-as-canvas in both directions: sparse content scales UP to fill the
// sheet, dense content stays at 1.0 (and overflows to page 2 if it must).
#context {
  let candidates = (1.3, 1.24, 1.18, 1.12, 1.06, 1.0)
  let pick = 1.0
  for s in candidates {
    if measure(box(width: avail-w, cv(s))).height <= avail-h {
      pick = s
      break
    }
  }
  cv(pick)
}
