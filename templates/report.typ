// Report template — professional business/academic report
#import "helpers.typ": callout-box, render-table, render-code, render-gallery
#import "@preview/wrap-it:0.1.1": wrap-content

#let doc = json("assets/content.json")
#let p = doc.at("preset", default: (:))

// ── Preset helpers ─────────────────────────────────────────────────────────────
#let body-font    = p.at("body_font",    default: "PT Serif")
#let heading-font = p.at("heading_font", default: "PT Sans")
#let mono-font    = p.at("mono_font",    default: "Source Code Pro")
#let accent-color = rgb(p.at("accent_color",  default: "#1d3557"))
#let head-color   = rgb(p.at("heading_color", default: "#1d3557"))
#let muted-color  = rgb(p.at("muted_color",   default: "#64748b"))
#let body-color   = rgb(p.at("body_color",    default: "#1a1a1a"))
#let text-size    = eval(p.at("text_size", default: "10.5pt"), mode: "code")
#let h1-size      = eval(p.at("h1_size",   default: "16pt"),   mode: "code")
#let h2-size      = eval(p.at("h2_size",   default: "13pt"),   mode: "code")
#let h3-size      = eval(p.at("h3_size",   default: "11pt"),   mode: "code")
#let h1-weight    = p.at("h1_weight", default: "bold")
#let h2-weight    = p.at("h2_weight", default: "semibold")
#let show-hf      = p.at("show_header_footer", default: true)
#let show-toc     = p.at("show_toc", default: true)
#let do-number    = p.at("numbered_headings", default: true)

// ── Page setup ────────────────────────────────────────────────────────────────
#set page(
  paper: p.at("paper", default: "a4"),
  margin: (
    left:   eval(p.at("margin_left",   default: "2.8cm"), mode: "code"),
    right:  eval(p.at("margin_right",  default: "2.2cm"), mode: "code"),
    top:    eval(p.at("margin_top",    default: "2.5cm"), mode: "code"),
    bottom: eval(p.at("margin_bottom", default: "2.5cm"), mode: "code"),
  ),
  header: context {
    if show-hf and here().page() > 1 {
      set text(font: heading-font, size: 8pt, fill: muted-color)
      doc.title
      h(1fr)
      counter(page).display("1")
      linebreak()
      line(length: 100%, stroke: 0.4pt + luma(210))
    }
  },
  footer: context {
    if show-hf and here().page() == 1 {
      set text(font: heading-font, size: 8pt, fill: muted-color)
      h(1fr)
      if doc.author != "" { doc.author }
    }
  },
)

// ── Typography ────────────────────────────────────────────────────────────────
#set text(
  font: body-font,
  size: text-size,
  fill: body-color,
  lang: doc.language,
  hyphenate: p.at("hyphenate", default: true),
)
#set par(
  justify: p.at("justify", default: true),
  leading: eval(p.at("leading", default: "0.65em"), mode: "code"),
  spacing: 1.1em,
)
#show raw: set text(font: mono-font, size: 0.88em)

// ── Heading styles ────────────────────────────────────────────────────────────
#show heading.where(level: 1): it => {
  v(1.5em)
  set text(font: heading-font, size: h1-size, weight: h1-weight, fill: head-color)
  it
  v(0.15em)
  line(length: 100%, stroke: 0.6pt + accent-color.lighten(40%))
  v(0.4em)
}
#show heading.where(level: 2): it => {
  v(1.1em)
  set text(font: heading-font, size: h2-size, weight: h2-weight, fill: head-color)
  it
  v(0.35em)
}
#show heading.where(level: 3): it => {
  v(0.8em)
  set text(font: heading-font, size: h3-size, weight: "semibold", fill: head-color)
  it
  v(0.2em)
}

// ── Title page ────────────────────────────────────────────────────────────────
#align(center + horizon)[
  #v(3cm)
  #rect(fill: accent-color, width: 100%, height: 4pt, radius: 2pt)
  #v(1.2cm)
  #text(font: heading-font, size: 26pt, weight: "bold", fill: accent-color)[#doc.title]
  #v(0.8cm)
  #if doc.author != "" [
    #set text(font: body-font, size: 13pt, fill: muted-color)
    #doc.author
  ]
  #v(3cm)
  #rect(fill: accent-color.lighten(60%), width: 100%, height: 2pt, radius: 1pt)
]
#pagebreak()

// ── Table of contents ─────────────────────────────────────────────────────────
#if show-toc and doc.sections.len() > 2 [
  #set heading(numbering: none)
  #text(font: heading-font, size: 14pt, weight: "bold")[Содержание]
  #v(0.6em)
  #outline(title: none, indent: 1.5em, depth: 2)
  #pagebreak()
]

// ── Body ──────────────────────────────────────────────────────────────────────
#if do-number {
  set heading(numbering: "1.1")
}

#for section in doc.sections {
  let lvl = section.level
  if lvl == 1 { heading(level: 1)[#section.title] }
  else if lvl == 2 { heading(level: 2)[#section.title] }
  else { heading(level: 3)[#section.title] }

  let safe-content = section.content.replace("#", "\\#").replace("\\#link(", "#link(").replace("\\#footnote[", "#footnote[")
  let body = eval(safe-content, mode: "markup")

  // Separate wrap-images from standard ones
  let wrap-imgs = section.images.filter(img =>
    img.at("position", default: "center") in ("left-wrap", "right-wrap")
  )
  let std-imgs = section.images.filter(img =>
    img.at("position", default: "center") not in ("left-wrap", "right-wrap")
  )

  if wrap-imgs.len() > 0 {
    let wi = wrap-imgs.first()
    let w  = wi.at("width", default: "40%")
    let side = if wi.at("position", default: "center") == "left-wrap" { left } else { right }
    let fig = figure(
      image(wi.at("_local", default: wi.path), width: eval(w, mode: "code")),
      caption: if wi.at("caption", default: "") != "" { [#wi.caption] } else { none },
      supplement: none,
    )
    wrap-content(fig, body, align: side + top, column-gutter: 1.5em)
    // Any additional wrap-images are placed inline after
    for wi2 in wrap-imgs.slice(1) {
      let w2   = wi2.at("width", default: "40%")
      let side2 = if wi2.at("position", default: "center") == "left-wrap" { left } else { right }
      v(0.8em)
      align(side2)[
        #figure(
          image(wi2.at("_local", default: wi2.path), width: eval(w2, mode: "code")),
          caption: if wi2.at("caption", default: "") != "" { [#wi2.caption] } else { none },
          supplement: none,
        )
      ]
    }
  } else {
    body
  }

  // Standard (centered / full-width) images
  for img in std-imgs {
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
