// Portfolio template — visual, image-forward, dark cover, accent bars
#import "helpers.typ": callout-box, render-table, render-code

#let doc = json("assets/content.json")
#let p = doc.at("preset", default: (:))

// ── Preset helpers ─────────────────────────────────────────────────────────────
#let body-font    = p.at("body_font",    default: "Noto Sans")
#let heading-font = p.at("heading_font", default: "Noto Sans")
#let mono-font    = p.at("mono_font",    default: "Noto Sans Mono")
#let accent-color = rgb(p.at("accent_color",  default: "#7c3aed"))
#let cover-color  = rgb(p.at("heading_color", default: "#1a1a2e"))
#let muted-color  = rgb(p.at("muted_color",   default: "#888888"))
#let body-color   = rgb(p.at("body_color",    default: "#1a1a1a"))
#let text-size    = eval(p.at("text_size", default: "11pt"),  mode: "code")
#let h1-size      = eval(p.at("h1_size",   default: "22pt"),  mode: "code")
#let h2-size      = eval(p.at("h2_size",   default: "15pt"),  mode: "code")
#let h3-size      = eval(p.at("h3_size",   default: "12pt"),  mode: "code")
#let show-toc     = p.at("show_toc", default: false)

// ── Page setup ────────────────────────────────────────────────────────────────
#set page(
  paper: "a4",
  margin: (
    left:   eval(p.at("margin_left",   default: "2.5cm"), mode: "code"),
    right:  eval(p.at("margin_right",  default: "2.5cm"), mode: "code"),
    top:    eval(p.at("margin_top",    default: "2.5cm"), mode: "code"),
    bottom: eval(p.at("margin_bottom", default: "2.5cm"), mode: "code"),
  ),
  header: context {
    if here().page() > 1 [
      #set text(font: heading-font, size: 8pt, fill: muted-color)
      #doc.title
      #h(1fr)
      #counter(page).display("1 / 1", both: true)
      #v(-3pt)
      #line(length: 100%, stroke: 0.4pt + accent-color.lighten(50%))
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
#set par(justify: true, leading: 0.62em, spacing: 1.05em)
#show raw: set text(font: mono-font, size: 0.88em)

// ── Heading styles ────────────────────────────────────────────────────────────
#show heading.where(level: 1): it => [
  #v(1.3em)
  #block(
    fill: cover-color,
    width: 100%,
    inset: (x: 12pt, y: 9pt),
    radius: 4pt,
  )[
    #set text(font: heading-font, size: h1-size, weight: "bold", fill: white)
    #it.body
  ]
  #v(0.5em)
]
#show heading.where(level: 2): it => [
  #v(1em)
  #block[
    #set text(font: heading-font, size: h2-size, weight: "bold", fill: accent-color)
    #it
  ]
  #line(length: 3cm, stroke: 2pt + accent-color)
  #v(0.35em)
]
#show heading.where(level: 3): it => [
  #v(0.8em)
  #set text(font: heading-font, size: h3-size, weight: "semibold", fill: cover-color)
  #it
  #v(0.2em)
]

// ── Dark cover ────────────────────────────────────────────────────────────────
#set page(margin: 0pt)
#block(fill: cover-color, width: 100%, height: 100%)[
  #set text(fill: white)
  #pad(left: 3cm, right: 3cm, top: 0pt, bottom: 0pt)[
    #v(1fr)
    #block(
      fill: accent-color,
      width: 5cm,
      height: 4pt,
      radius: 2pt,
    )
    #v(0.8cm)
    #text(font: heading-font, size: 36pt, weight: "bold", tracking: -1pt)[#doc.title]
    #v(0.9cm)
    #if doc.author != "" [
      #set text(font: body-font, size: 14pt, fill: rgb("#a0a8c0"))
      #doc.author
    ]
    #v(1fr)
  ]
]
#pagebreak()
#set page(
  margin: (
    left:   eval(p.at("margin_left",   default: "2.5cm"), mode: "code"),
    right:  eval(p.at("margin_right",  default: "2.5cm"), mode: "code"),
    top:    eval(p.at("margin_top",    default: "2.5cm"), mode: "code"),
    bottom: eval(p.at("margin_bottom", default: "2.5cm"), mode: "code"),
  ),
)

// ── Optional TOC ──────────────────────────────────────────────────────────────
#if show-toc and doc.sections.len() > 2 [
  #text(font: heading-font, size: 14pt, weight: "bold")[Содержание]
  #v(0.5em)
  #outline(title: none, indent: 1.2em, depth: 2)
  #pagebreak()
]

// ── Body ──────────────────────────────────────────────────────────────────────
#set heading(numbering: none)

#for section in doc.sections {
  let lvl = section.level
  if lvl == 1 { heading(level: 1)[#section.title] }
  else if lvl == 2 { heading(level: 2)[#section.title] }
  else { heading(level: 3)[#section.title] }

  eval(section.content.replace("#", "\\#").replace("\\#link(", "#link("), mode: "markup")

  for img in section.images {
    v(0.7em)
    let w = img.at("width", default: "100%")
    align(center)[
      #image(img.at("_local", default: img.path), width: eval(w, mode: "code"))
      #if img.caption != "" [
        #set text(font: body-font, size: 8.5pt, fill: muted-color, style: "italic")
        #v(0.25em)
        #img.caption
      ]
    ]
    v(0.7em)
  }

  for tbl in section.tables { render-table(tbl) }
  for cb in section.code_blocks { render-code(cb, mono-font) }
  for co in section.callouts { callout-box(co.at("text"), co.kind) }
}
