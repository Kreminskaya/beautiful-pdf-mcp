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
// Running header & page numbers, user-controllable via preset_overrides:
//   show_header_footer: false → no running header at all
//   header_rule: false        → keep the header text but drop the thin line
//   page_num_position: "auto" (book default: mirrored — number on the outer edge),
//     "top-left"|"top-center"|"top-right"|"bottom-left"|"bottom-center"|
//     "bottom-right"|"none"
#let show-hf  = p.at("show_header_footer", default: true)
#let hdr-rule = p.at("header_rule", default: true)
#let pn-pos   = p.at("page_num_position", default: "auto")

// ── Page setup (A5, mirrored Van de Graaf margins) ────────────────────────────
// inside (binding): 20mm, top: 25mm, outside: 35mm, bottom: 40mm
#set page(
  paper: "a5",
  margin: (inside: 2.0cm, outside: 3.5cm, top: 2.5cm, bottom: 4.0cm),
  header: context {
    let pg = here().page()
    if show-hf and pg > 2 [
      #set text(font: heading-font, size: 7.5pt, fill: muted-color)
      #let num = counter(page).display("1")
      #if pn-pos == "auto" [
        // Classic mirrored book furniture: number rides the OUTER edge.
        #if calc.odd(pg) [#doc.title #h(1fr) #num] else [#num #h(1fr) #doc.title]
      ] else if pn-pos == "top-left" [
        #num #h(1fr) #doc.title
      ] else if pn-pos == "top-center" [
        #grid(columns: (1fr, auto, 1fr), align(left)[#doc.title], num, [])
      ] else if pn-pos == "top-right" [
        #doc.title #h(1fr) #num
      ] else [
        // bottom-* or none: header keeps only the title
        #doc.title #h(1fr)
      ]
      #v(-3pt)
      #if hdr-rule { line(length: 100%, stroke: 0.4pt + luma(210)) }
    ]
  },
  footer: context {
    let pg = here().page()
    if show-hf and pg > 2 and pn-pos.starts-with("bottom") [
      #set text(font: heading-font, size: 7.5pt, fill: muted-color)
      #align(
        if pn-pos == "bottom-left" { left }
        else if pn-pos == "bottom-center" { center }
        else { right }
      )[#counter(page).display("1")]
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
  // Cheap hyphenation cost → justified lines pack tight instead of opening into
  // rivers (large gaps between words on sparse lines).
  costs: (hyphenation: 5%, runt: 100%, widow: 100%, orphan: 100%),
)
// 140% leading (Butterick optimum for book-weight text)
#set par(
  justify: true,
  leading: eval(p.at("leading", default: "0.65em"), mode: "code"),
  spacing: 0.75em,
  first-line-indent: eval(indent-str, mode: "code"),
)
#show raw: set text(font: mono-font, size: 0.88em)
#show figure.caption: it => [
  #set text(font: heading-font, size: 0.8em, style: "italic", fill: muted-color)
  #set par(justify: false)
  #align(center)[#it.body]
]

// ── Heading styles ────────────────────────────────────────────────────────────
// Chapter heading — centered, decorative rules, page break before
#show heading.where(level: 1): it => [
  #pagebreak(weak: true)
  #v(1.2cm)
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
#if show-toc and doc.sections.len() > 2 [
  #set page(numbering: "i")
  #counter(page).update(1)
  #align(center)[
    #text(font: heading-font, size: 13pt, weight: "bold")[Содержание]
  ]
  #v(0.6em)
  #outline(title: none, indent: 1.5em, depth: 2)
  #pagebreak()
]

// ── Body ──────────────────────────────────────────────────────────────────────
#set page(numbering: "1")
#counter(page).update(1)

#if do-number {
  set heading(numbering: "1.1")
}

#for (si, section) in doc.sections.enumerate() {
  let lvl = section.level
  if lvl == 1 {
    heading(level: 1)[#section.title]
    // метка начала главы для постраничного QC (docs/SPEC_PAGE_FILL.md)
    context [#metadata(here().position()) <bp-sec>]
  }
  else if lvl == 2 { heading(level: 2)[#section.title] }
  else { heading(level: 3)[#section.title] }

  let safe-content = section.content.replace("#", "\\#").replace("\\#link(", "#link(").replace("\\#footnote[", "#footnote[")

  // Books never wrap text around side floats — illustrations sit CENTERED in the
  // column (optionally captioned), and the text simply resumes underneath, the
  // way a printed book is set. Each illustration is interleaved INTO the chapter
  // (not appended after it): if it doesn't fit on the current page it moves to
  // the top of the next one and the remaining prose follows right below it, so a
  // picture is never stranded alone on a near-empty sheet.
  let book-fig(img) = {
    let w = img.at("width", default: "85%")
    if w == "full" { w = "100%" }
    v(0.9em, weak: true)
    figure(
      image(img.at("_local", default: img.path), width: eval(w, mode: "code")),
      caption: if img.at("caption", default: "") != "" { [#img.caption] } else { none },
      supplement: none,
    )
    v(0.9em, weak: true)
  }

  // position "top" → the illustration opens the chapter, BEFORE any text
  // (frontispiece, the way picture books start). The rest interleave evenly.
  let top-imgs  = section.images.filter(im => im.at("position", default: "auto") == "top")
  let flow-imgs = section.images.filter(im => im.at("position", default: "auto") != "top")

  for im in top-imgs { book-fig(im) }

  // Split by paragraph for Stage-3 <bp-para> marks and after:N interleaving.
  // Inline mark appended to each para; chunk is eval'd as ONE string via join("\n\n")
  // to preserve the original paragraph spacing (same as eval'ing the whole block).
  let paras  = safe-content.split("\n\n").map(s => s.trim()).filter(s => s != "")
  let total  = paras.len()
  let with-mark(pi) = (
    paras.at(pi)
    + "#box(context[#metadata((sec: " + str(si)
    + ", para: " + str(pi)
    + ", pos: here().position())) <bp-para>])"
  )
  let render-chunk(from, to) = {
    if from < to {
      eval(range(from, to).map(with-mark).join("\n\n"), mode: "markup")
    }
  }
  let n      = flow-imgs.len()
  let cursor = 0
  for (k, im) in flow-imgs.enumerate() {
    let pos = im.at("position", default: "auto")
    let cut = if pos.starts-with("after:") {
      calc.min(total, calc.max(0, int(pos.slice(6))))
    } else {
      calc.min(total, calc.ceil(total * (k + 1) / (n + 1)))
    }
    render-chunk(cursor, cut)
    cursor = cut
    book-fig(im)
  }
  render-chunk(cursor, total)

  for gal in section.at("galleries", default: ()) { render-gallery(gal) }
  for tbl in section.tables { render-table(tbl) }
  for cb in section.code_blocks { render-code(cb, mono-font) }
  for co in section.callouts { callout-box(co.at("text"), co.kind) }
}
