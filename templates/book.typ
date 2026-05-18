// Book template — chapter-based, A5, Van de Graaf margins, long-form reading
#import "helpers.typ": callout-box, render-table, render-code, render-gallery

#let doc = json("assets/content.json")
#let p = doc.at("preset", default: (:))

// ── Preset helpers ─────────────────────────────────────────────────────────────
#let body-font    = p.at("body_font",    default: "PT Serif")
#let heading-font = p.at("heading_font", default: "PT Sans")
#let mono-font    = p.at("mono_font",    default: "PT Mono")
#let accent-color = rgb(p.at("accent_color",  default: "#8b0000"))
#let head-color   = rgb(p.at("heading_color", default: "#1a1a1a"))
#let muted-color  = rgb(p.at("muted_color",   default: "#888888"))
#let body-color   = rgb(p.at("body_color",    default: "#1a1a1a"))
#let text-size    = eval(p.at("text_size", default: "10pt"),  mode: "code")
#let h1-size      = eval(p.at("h1_size",   default: "18pt"),  mode: "code")
#let h2-size      = eval(p.at("h2_size",   default: "13pt"),  mode: "code")
#let h3-size      = eval(p.at("h3_size",   default: "11pt"),  mode: "code")
#let do-number    = p.at("numbered_headings", default: false)
#let show-toc     = p.at("show_toc", default: true)
#let indent-str   = p.at("indent", default: "1.5em")

// ── Page setup (A5, mirrored Van de Graaf margins) ────────────────────────────
// inside (binding): 20mm, top: 25mm, outside: 35mm, bottom: 40mm
#set page(
  paper: "a5",
  margin: (inside: 2.0cm, outside: 3.5cm, top: 2.5cm, bottom: 4.0cm),
  header: context {
    let pg = here().page()
    if pg > 2 [
      #set text(font: heading-font, size: 7.5pt, fill: muted-color)
      #if calc.odd(pg) [
        #h(1fr)
        #doc.title
      ] else [
        #counter(page).display("1")
        #h(1fr)
      ]
      #v(-3pt)
      #line(length: 100%, stroke: 0.4pt + luma(210))
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
// 140% leading (Butterick optimum for book-weight text)
#set par(
  justify: true,
  leading: eval(p.at("leading", default: "0.65em"), mode: "code"),
  spacing: 0em,           // no space between paragraphs — use indent instead
  first-line-indent: eval(indent-str, mode: "code"),
)
#show raw: set text(font: mono-font, size: 0.88em)

// ── Heading styles ────────────────────────────────────────────────────────────
// Chapter heading — centered, decorative rules, page break before
#show heading.where(level: 1): it => [
  #pagebreak(weak: true)
  #v(2.5cm)
  #align(center)[
    #set text(font: heading-font, size: h1-size, weight: "bold", fill: head-color, tracking: -0.5pt)
    #it.body
  ]
  #v(0.3cm)
  #align(center)[
    #line(length: 3cm, stroke: 1pt + accent-color)
  ]
  #v(1cm)
]
#show heading.where(level: 2): it => [
  #v(1.3em)
  #set text(font: heading-font, size: h2-size, weight: "semibold", fill: head-color)
  #it
  #v(0.4em)
]
#show heading.where(level: 3): it => [
  #v(0.9em)
  #set text(font: heading-font, size: h3-size, weight: "semibold", style: "italic", fill: head-color)
  #it
  #v(0.25em)
]

// ── Title page ────────────────────────────────────────────────────────────────
#set page(numbering: none)
#align(center + horizon)[
  #v(1.5cm)
  #line(length: 7cm, stroke: 1pt + luma(170))
  #v(0.9cm)
  #text(font: heading-font, size: 28pt, weight: "bold", tracking: -1pt)[#doc.title]
  #v(0.9cm)
  #line(length: 7cm, stroke: 1pt + luma(170))
  #v(1.8cm)
  #if doc.author != "" [
    #set text(font: body-font, size: 13pt, fill: muted-color, style: "italic")
    #doc.author
  ]
]
#pagebreak()

// ── TOC ───────────────────────────────────────────────────────────────────────
#set page(numbering: "i")
#counter(page).update(1)
#if show-toc and doc.sections.len() > 2 [
  #align(center)[
    #text(font: heading-font, size: 13pt, weight: "bold")[Содержание]
  ]
  #v(0.6em)
  #outline(title: none, indent: 1.5em, depth: 2)
]
#pagebreak()

// ── Body ──────────────────────────────────────────────────────────────────────
#set page(numbering: "1")
#counter(page).update(1)

#if do-number {
  set heading(numbering: "1.1")
}

#for section in doc.sections {
  let lvl = section.level
  if lvl == 1 { heading(level: 1)[#section.title] }
  else if lvl == 2 { heading(level: 2)[#section.title] }
  else { heading(level: 3)[#section.title] }

  eval(section.content.replace("#", "\\#").replace("\\#link(", "#link("), mode: "markup")

  for img in section.images {
    v(0.9em)
    let w = img.at("width", default: "100%")
    figure(
      image(img.at("_local", default: img.path), width: eval(w, mode: "code")),
      caption: if img.caption != "" { [#img.caption] } else { none },
      supplement: none,
    )
    v(0.6em)
  }

  for gal in section.at("galleries", default: ()) { render-gallery(gal) }
  for tbl in section.tables { render-table(tbl) }
  for cb in section.code_blocks { render-code(cb, mono-font) }
  for co in section.callouts { callout-box(co.at("text"), co.kind) }
}
