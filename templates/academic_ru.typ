// Academic RU template — ГОСТ 7.32, 14pt, 1.5x leading, 30/15/20/20 margins
// ГОСТ 7.32: все иллюстрации — по центру, подпись под рисунком. Обтекание текстом не применяется.
#import "helpers.typ": render-table, render-code, render-gallery

// ГОСТ: callout-боксы без цвета — серая левая черта, обычный текст
#let callout-box(body, kind) = {
  let safe-body = body.replace("#", "\\#").replace("\\#link(", "#link(").replace("\\#footnote[", "#footnote[")
  v(0.5em)
  block(
    width: 100%,
    stroke: (left: 2pt + luma(160)),
    inset: (left: 12pt, right: 8pt, top: 6pt, bottom: 6pt),
  )[
    #set text(size: 0.9em, fill: luma(30))
    #eval(safe-body, mode: "markup")
  ]
  v(0.5em)
}

#let doc = json("assets/content.json")
#let p = doc.at("preset", default: (:))

// ── Preset helpers ─────────────────────────────────────────────────────────────
#let body-font    = p.at("body_font",    default: "PT Serif")
#let heading-font = p.at("heading_font", default: "PT Sans")
#let mono-font    = p.at("mono_font",    default: "PT Mono")
#let head-color   = rgb(p.at("heading_color", default: "#1a1a1a"))
#let body-color   = rgb(p.at("body_color",    default: "#000000"))
#let muted-color  = rgb(p.at("muted_color",   default: "#555555"))
#let text-size    = eval(p.at("text_size", default: "14pt"),  mode: "code")
#let h1-size      = eval(p.at("h1_size",   default: "16pt"),  mode: "code")
#let h2-size      = eval(p.at("h2_size",   default: "14pt"),  mode: "code")
#let h3-size      = eval(p.at("h3_size",   default: "14pt"),  mode: "code")
#let indent-str   = p.at("indent", default: "1.25cm")
#let show-toc     = p.at("show_toc", default: true)

// ── Page setup (GOST 7.32) ────────────────────────────────────────────────────
// left 30mm, right 15mm, top 20mm, bottom 20mm
#set page(
  paper: "a4",
  margin: (
    left:   eval(p.at("margin_left",   default: "3.0cm"), mode: "code"),
    right:  eval(p.at("margin_right",  default: "1.5cm"), mode: "code"),
    top:    eval(p.at("margin_top",    default: "2.0cm"), mode: "code"),
    bottom: eval(p.at("margin_bottom", default: "2.0cm"), mode: "code"),
  ),
  // GOST: page number centered at bottom
  footer: context {
    if here().page() > 1 {
      align(center)[
        #set text(font: body-font, size: 12pt)
        #counter(page).display("1")
      ]
    }
  },
)

// ── Typography (GOST: 14pt, 1.5x line spacing = 0.75em leading in Typst) ─────
// Typst leading = space between baselines minus font size.
// 14pt × 1.5 = 21pt total line height → leading = 21pt − 14pt = 7pt ≈ 0.5em
// But styles.json preset already encodes the correct value:
#set text(
  font: body-font,
  size: text-size,
  fill: body-color,
  lang: doc.language,
  hyphenate: false,   // GOST does not require hyphenation
)
#set par(
  justify: true,
  leading: eval(p.at("leading", default: "0.75em"), mode: "code"),
  spacing: 0em,
  first-line-indent: eval(indent-str, mode: "code"),
)
#show raw: set text(font: mono-font, size: 0.82em)

// ── Heading styles (GOST: bold, centered for H1, left for H2/H3) ─────────────
#show heading.where(level: 1): it => {
  v(1.8em)
  align(center)[
    #set text(font: heading-font, size: h1-size, weight: "bold", fill: head-color)
    #upper(it.body)
  ]
  v(0.8em)
}
#show heading.where(level: 2): it => {
  v(1.4em)
  set text(font: heading-font, size: h2-size, weight: "bold", fill: head-color)
  it
  v(0.5em)
}
#show heading.where(level: 3): it => {
  v(1.0em)
  set text(font: heading-font, size: h3-size, weight: "bold", fill: head-color)
  it
  v(0.4em)
}

// ── Title page ────────────────────────────────────────────────────────────────
#set page(numbering: none)
#v(3cm)
#align(center)[
  #text(font: heading-font, size: 15pt, weight: "bold")[
    #upper(doc.title)
  ]
  #v(1.5cm)
  #if doc.author != "" [
    #set text(font: body-font, size: 14pt)
    #doc.author
  ]
]
#pagebreak()

// ── Table of contents (ГОСТ: "СОДЕРЖАНИЕ") ───────────────────────────────────
#set page(numbering: "1")
#counter(page).update(2)   // title page is page 1 but unnumbered
#if show-toc and doc.sections.len() > 2 [
  #set heading(numbering: none)
  #align(center)[
    #text(font: heading-font, size: 14pt, weight: "bold")[СОДЕРЖАНИЕ]
  ]
  #v(0.8em)
  #outline(title: none, indent: 1.5em, depth: 2)
  #pagebreak()
]

// ── Body ──────────────────────────────────────────────────────────────────────
#set heading(numbering: "1.1")

#for section in doc.sections {
  let lvl = section.level
  if lvl == 1 { heading(level: 1)[#section.title] }
  else if lvl == 2 { heading(level: 2)[#section.title] }
  else { heading(level: 3)[#section.title] }

  let safe-content = section.content.replace("#", "\\#").replace("\\#link(", "#link(").replace("\\#footnote[", "#footnote[")
  eval(safe-content, mode: "markup")

  // ГОСТ 7.32: все изображения по центру, подпись под рисунком. Обтекание не применяется.
  for img in section.images {
    v(1.0em)
    let w = img.at("width", default: "80%")
    figure(
      image(img.at("_local", default: img.path), width: eval(w, mode: "code")),
      caption: if img.at("caption", default: "") != "" { [#img.caption] } else { none },
      supplement: [Рисунок],
    )
    v(0.8em)
  }

  for gal in section.at("galleries", default: ()) { render-gallery(gal) }
  for tbl in section.tables { render-table(tbl) }
  for cb in section.code_blocks { render-code(cb, mono-font) }
  for co in section.callouts { callout-box(co.at("text"), co.kind) }
}
