// Journal template — editorial / magazine layout
// Images auto-wrap by default (alternating left/right per section).
// Explicit position="center" forces a standalone centered figure.
#import "helpers.typ": callout-box, render-table, render-code, render-gallery
#import "@preview/wrap-it:0.1.1": wrap-content

#let doc = json("assets/content.json")
#let p = doc.at("preset", default: (:))

// ── Preset helpers ─────────────────────────────────────────────────────────────
#let body-font    = p.at("body_font",    default: "Lora")
#let heading-font = p.at("heading_font", default: "Cormorant")
#let mono-font    = p.at("mono_font",    default: "Source Code Pro")
#let accent-color = rgb(p.at("accent_color",  default: "#c4a35a"))
#let head-color   = rgb(p.at("heading_color", default: "#1e1a14"))
#let muted-color  = rgb(p.at("muted_color",   default: "#a89878"))
#let body-color   = rgb(p.at("body_color",    default: "#1e1a14"))
#let text-size    = eval(p.at("text_size", default: "11pt"),  mode: "code")
#let h1-size      = eval(p.at("h1_size",   default: "20pt"),  mode: "code")
#let h2-size      = eval(p.at("h2_size",   default: "14pt"),  mode: "code")
#let h3-size      = eval(p.at("h3_size",   default: "11.5pt"), mode: "code")
#let show-hf      = p.at("show_header_footer", default: true)
#let show-toc     = p.at("show_toc", default: false)

// ── Page setup ────────────────────────────────────────────────────────────────
#set page(
  paper: "a4",
  margin: (
    left:   eval(p.at("margin_left",   default: "2.8cm"), mode: "code"),
    right:  eval(p.at("margin_right",  default: "2.8cm"), mode: "code"),
    top:    eval(p.at("margin_top",    default: "2.5cm"), mode: "code"),
    bottom: eval(p.at("margin_bottom", default: "2.5cm"), mode: "code"),
  ),
  header: context {
    if show-hf and here().page() > 1 [
      #set text(font: heading-font, size: 7.5pt, fill: muted-color)
      #upper(doc.title)
      #h(1fr)
      #counter(page).display("1")
      #v(-4pt)
      #line(length: 100%, stroke: 0.5pt + accent-color.lighten(30%))
    ]
  },
)

// ── Typography ────────────────────────────────────────────────────────────────
#set text(
  font: body-font,
  size: text-size,
  fill: body-color,
  lang: doc.language,
  hyphenate: true,
)
#set par(
  justify: true,
  leading: eval(p.at("leading", default: "0.68em"), mode: "code"),
  spacing: 1.0em,
)
#show raw: set text(font: mono-font, size: 0.88em)

// ── Heading styles — editorial bars ──────────────────────────────────────────
#show heading.where(level: 1): it => [
  #v(2em)
  #line(length: 100%, stroke: 2pt + accent-color)
  #v(0.5em)
  #block[
    #set text(font: heading-font, size: h1-size, weight: "bold", fill: head-color)
    #it.body
  ]
  #v(0.5em)
]
#show heading.where(level: 2): it => [
  #v(1.3em)
  // Warm beige filled section-header bar — stays in the sand/beige palette
  #block(
    fill: rgb("#faf6ef"),
    width: 100%,
    inset: (left: 10pt, right: 8pt, top: 6pt, bottom: 6pt),
    radius: 2pt,
  )[
    #set text(font: heading-font, size: h2-size, weight: "semibold", fill: head-color)
    #it.body
  ]
  #v(0.4em)
]
#show heading.where(level: 3): it => [
  #v(0.9em)
  #stack(dir: ltr, spacing: 8pt,
    rect(fill: accent-color.lighten(20%), width: 3pt, height: 1.1em, radius: 1pt),
    block[
      #set text(font: heading-font, size: h3-size, weight: "semibold",
                fill: muted-color, tracking: 0.5pt)
      #upper(it.body)
    ]
  )
  #v(0.2em)
]

// ── Cover ─────────────────────────────────────────────────────────────────────
#v(4cm)
#line(length: 100%, stroke: 2pt + accent-color)
#v(0.6cm)
#text(font: heading-font, size: 32pt, weight: "bold", fill: head-color)[#doc.title]
#v(0.5cm)
#line(length: 3.5cm, stroke: 0.8pt + muted-color)
#v(0.4cm)
#if doc.author != "" [
  #set text(font: body-font, size: 12pt, fill: muted-color, style: "italic")
  #doc.author
]
#pagebreak()

// ── Optional TOC ──────────────────────────────────────────────────────────────
#if show-toc and doc.sections.len() > 2 [
  #set heading(numbering: none)
  #text(font: heading-font, size: 13pt, weight: "bold")[Contents]
  #v(0.5em)
  #outline(title: none, indent: 1.2em, depth: 2)
  #pagebreak()
]

// ── Body — images auto-wrap, alternating sides ────────────────────────────────
#set heading(numbering: none)

#for (si, section) in doc.sections.enumerate() {
  let lvl = section.level
  if lvl == 1 { heading(level: 1)[#section.title] }
  else if lvl == 2 { heading(level: 2)[#section.title] }
  else { heading(level: 3)[#section.title] }

  let safe-content = section.content.replace("#", "\\#").replace("\\#link(", "#link(").replace("\\#footnote[", "#footnote[")
  let body = eval(safe-content, mode: "markup")

  // Auto-alternate side: even sections → right, odd → left
  let auto-side = if calc.even(si) { "right-wrap" } else { "left-wrap" }

  // Separate wrap vs explicit-center images
  let wrap-imgs = section.images.filter(img =>
    img.at("position", default: auto-side) != "center"
  )
  let center-imgs = section.images.filter(img =>
    img.at("position", default: auto-side) == "center"
  )

  if wrap-imgs.len() > 0 {
    let wi = wrap-imgs.first()
    let pos = wi.at("position", default: auto-side)
    let side = if pos == "left-wrap" { left } else { right }
    let w = wi.at("width", default: "38%")
    let cap = wi.at("caption", default: "")
    let fig = figure(
      image(wi.at("_local", default: wi.path), width: eval(w, mode: "code")),
      caption: if cap != "" { [#cap] } else { none },
      supplement: none,
    )
    wrap-content(fig, body, align: side + top, column-gutter: 1.4em)
  } else {
    body
  }

  // Remaining wrap images (2nd, 3rd...)
  if wrap-imgs.len() > 1 {
    for wi in wrap-imgs.slice(1) {
      v(0.6em)
      let w = wi.at("width", default: "38%")
      let cap = wi.at("caption", default: "")
      let pos = wi.at("position", default: auto-side)
      let side = if pos == "left-wrap" { left } else { right }
      align(side)[
        #figure(
          image(wi.at("_local", default: wi.path), width: eval(w, mode: "code")),
          caption: if cap != "" { [#cap] } else { none },
          supplement: none,
        )
      ]
    }
  }

  // Explicit center images
  for img in center-imgs {
    v(0.9em)
    let w = img.at("width", default: "100%")
    figure(
      image(img.at("_local", default: img.path), width: eval(w, mode: "code")),
      caption: if img.at("caption", default: "") != "" { [#img.caption] } else { none },
      supplement: none,
    )
    v(0.6em)
  }

  for gal in section.at("galleries", default: ()) { render-gallery(gal) }
  for tbl in section.tables { render-table(tbl) }
  for cb in section.code_blocks { render-code(cb, mono-font) }
  for co in section.callouts { callout-box(co.at("text"), co.kind) }
}
