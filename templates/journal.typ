// Journal template — editorial / magazine layout
// Wrap images float to the top of their page (placement: top), alternating side-alignment.
// Explicit position="center" forces a standalone centered float.
#import "helpers.typ": callout-box, render-table, render-code, render-gallery, render-body-with-marks
#import "@preview/wrap-it:0.1.1": wrap-content
#import "@preview/meander:0.4.3"

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
// Page-number placement: "auto" (template default: top-right in the running header),
// "top-left" | "top-center" | "top-right" | "bottom-left" | "bottom-center" |
// "bottom-right" | "none". Settable per document via preset_overrides.
#let pn-pos   = p.at("page_num_position", default: "auto")
// The thin accent rule under the running header — on by default, can be disabled.
#let hdr-rule = p.at("header_rule", default: true)

#let m-left   = eval(p.at("margin_left",   default: "2.8cm"), mode: "code")
#let m-right  = eval(p.at("margin_right",  default: "2.8cm"), mode: "code")
#let m-top    = eval(p.at("margin_top",    default: "2.0cm"), mode: "code")
#let m-bottom = eval(p.at("margin_bottom", default: "2.0cm"), mode: "code")
// A4 width minus margins → the text column. Computed up front so wrap images can
// use ABSOLUTE widths (no layout()/measure that would force sections onto a new page).
#let text-width = 21cm - m-left - m-right
// A4 height minus margins → the usable text height of ONE page. Used to pour exactly
// one page worth of a two-photo spread, then carry the remainder to the next page.
#let page-text-height = 29.7cm - m-top - m-bottom

// ── Page setup ────────────────────────────────────────────────────────────────
#set page(
  paper: "a4",
  margin: (
    left:   m-left,
    right:  m-right,
    top:    m-top,
    bottom: m-bottom,
  ),
  header: context {
    if show-hf and here().page() > 1 [
      #set text(font: heading-font, size: 7.5pt, fill: muted-color)
      #let num = counter(page).display("1")
      #if pn-pos == "top-left" [
        #num #h(1fr) #upper(doc.title)
      ] else if pn-pos == "top-center" [
        #grid(columns: (1fr, auto, 1fr), align(left)[#upper(doc.title)], num, [])
      ] else if pn-pos in ("auto", "top-right") [
        #upper(doc.title) #h(1fr) #num
      ] else [
        #upper(doc.title)
      ]
      #v(-4pt)
      #if hdr-rule { line(length: 100%, stroke: 0.5pt + accent-color.lighten(30%)) }
    ]
  },
  footer: context {
    if show-hf and here().page() > 1 and pn-pos.starts-with("bottom") [
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
  // Cheap hyphenation cost → Typst hyphenates readily instead of stretching word
  // spaces, so justified lines pack tight and never open into rivers, even in the
  // narrow columns beside a wrapped photo.
  costs: (hyphenation: 5%, runt: 100%, widow: 100%, orphan: 100%),
)
// Justified for a clean right edge (magazine standard), but rivers are prevented by
// the aggressive hyphenation above.
#set par(
  justify: true,
  leading: eval(p.at("leading", default: "0.68em"), mode: "code"),
  spacing: 1.0em,
)
#show raw: set text(font: mono-font, size: 0.88em)

// ── Figure captions — tiny tracked Cormorant credit, right-aligned ───────────
// Only shown when agent explicitly provides a caption. Default is no caption.
#show figure.caption: it => [
  #set text(font: heading-font, size: 7pt, fill: muted-color, tracking: 0.06em)
  #set par(justify: false)
  #v(0.1em)
  #align(right)[#upper(it.body)]
]

// ── Heading styles — quiet editorial typography ──────────────────────────────
// No full-width gold bar on every heading (it doubled up with the running-header
// rule and read as two stacked stripes). The title carries itself; a short accent
// stroke under it gives a magazine flourish without the heavy repeating line.
#show heading.where(level: 1): it => [
  #v(1.0em)
  #block[
    #set text(font: heading-font, size: h1-size, weight: "bold", fill: head-color)
    #it.body
  ]
  #v(0.22em)
  #line(length: 1.6cm, stroke: 1.6pt + accent-color)
  #v(0.55em)
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
  #text(font: heading-font, size: 13pt, weight: "bold")[#if doc.language == "en" { [Contents] } else { [Содержание] }]
  #v(0.5em)
  #outline(title: none, indent: 1.2em, depth: 2)
  #pagebreak()
]

// ── Body — editorial layout with side-wrapped images ─────────────────────────
// Layout is chosen from the photo's own proportions (aspect = height/width):
//   • wide landscape (aspect < 0.85) → full-width centered band
//   • portrait / square             → floats to the side, text wraps around it
// Sides auto-alternate per section. position="center"/"left-wrap"/"right-wrap"
// override the automatic choice when the agent sets it explicitly.
#set heading(numbering: none)

// Magazine default is NO caption; shown only when the agent supplies one, and
// then centered under the photo across its full width.
#let caption-credit(cap) = [
  #v(0.35em)
  #set text(font: heading-font, size: 7.5pt, fill: muted-color, tracking: 0.08em)
  #set par(justify: false, leading: 0.4em)
  #align(center)[#upper(cap)]
]

// Resolve an image to "center" | "left-wrap" | "right-wrap" from its position +
// proportions. Wide photos read better full-width than squeezed into a column.
#let resolve-pos(img, auto-side) = {
  let pos = img.at("position", default: "auto")
  if pos == "center" or pos == "left-wrap" or pos == "right-wrap" { pos }
  else if img.at("aspect", default: 1.3) < 0.85 { "center" }
  else { auto-side }
}

#let flip-side(s) = if s == "left-wrap" { "right-wrap" } else { "left-wrap" }

// Build a pixel-accurate, absolutely-sized figure box for a wrap image. Absolute
// dims are required because wrap-it's internal measure() collapses relative
// widths (a 40% image would render tiny). iw = column × pct, ih = iw × real aspect.
// One image at an absolute pixel width. `force-w` overrides the per-shape default
// so several stacked photos share one tidy column edge.
#let make-wrap-fig(wi, caption-fn, force-w: none) = {
  let aspect = wi.at("aspect", default: 1.3)
  // Default column share by shape: portraits a touch narrower than squares.
  let default-w = if aspect > 1.15 { "40%" } else { "46%" }
  let wstr = if force-w != none { force-w } else { wi.at("width", default: default-w) }
  if wstr == "full" or wstr == "100%" { wstr = default-w }
  let pct = eval(wstr, mode: "code")
  let iw  = text-width * pct
  let ih  = iw * aspect
  let cap = wi.at("caption", default: "")
  box(width: iw)[
    #image(wi.at("_local", default: wi.path), width: iw, height: ih)
    #if cap != "" { caption-fn(cap) }
  ]
}

// Wrap one continuous body around a prebuilt fixed brick (figure).
// `context` (not layout()) gives wrap-it its measurement context while keeping the
// result a normal, breakable part of the flow — the page fills, then breaks mid-line.
#let wrap-fixed(fixed, body, side) = context wrap-content(
  fixed,
  body,
  align: (if side == "left-wrap" { left } else { right }) + top,
  column-gutter: 0.9em,
  size: (width: text-width, height: 0pt),
)

#let wrap-one(wi, seg, side) = wrap-fixed(make-wrap-fig(wi, caption-credit), seg, side)

// A diagonal magazine spread, powered by the meander page-layout engine.
// Photo A floats near the TOP of one side, photo B sits at the BOTTOM of the
// opposite side, and ONE continuous body threads around both — meander segments
// the page into zones and pours the text through them, filling the page to the
// bottom. Whatever doesn't fit is captured by the overflow handler and continues
// as plain prose right after — no new heading, no repeated photos, like a book.
// (Replaces the manual measure-and-split loop: meander thinks in pages natively,
// which is exactly the page-as-canvas principle of this project.)
#let two-photo-spread(body, a, b, side-a, side-b) = meander.reflow({
  import meander: *
  placed(
    top + (if side-a == "left-wrap" { left } else { right }),
    boundary: contour.margin(x: 10pt, bottom: 9pt),
    make-wrap-fig(a, caption-credit),
  )
  placed(
    bottom + (if side-b == "left-wrap" { left } else { right }),
    boundary: contour.margin(x: 10pt, top: 9pt),
    make-wrap-fig(b, caption-credit),
  )
  container()
  content(body)
  opt.overflow.custom(o => o.styled)
})

#for (si, section) in doc.sections.enumerate() {
  let lvl = section.level
  if lvl == 1 {
    heading(level: 1)[#section.title]
    // метка начала секции для постраничного QC (docs/SPEC_PAGE_FILL.md)
    context [#metadata(here().position()) <bp-sec>]
  }
  else if lvl == 2 { heading(level: 2)[#section.title] }
  else { heading(level: 3)[#section.title] }

  let safe-content = section.content.replace("#", "\\#").replace("\\#link(", "#link(").replace("\\#footnote[", "#footnote[")

  // Auto-alternate side: even sections → right, odd → left
  let auto-side = if calc.even(si) { "right-wrap" } else { "left-wrap" }

  let wrap-imgs   = section.images.filter(img => resolve-pos(img, auto-side) != "center")
  let center-imgs = section.images.filter(img => resolve-pos(img, auto-side) == "center")

  if wrap-imgs.len() == 0 {
    // No wrap images: paragraph-by-paragraph with <bp-para> marks and after:N
    // interleaving for any centered/full-width images (Stage-3 pipeline).
    let jrn-fig = im => {
      let w   = im.at("width", default: "100%")
      let cap = im.at("caption", default: "")
      v(0.7em)
      align(center)[
        #image(im.at("_local", default: im.path), width: eval(w, mode: "code"))
        #if cap != "" [
          #v(0.25em)
          #set text(font: heading-font, size: 7pt, fill: muted-color, tracking: 0.06em)
          #set par(justify: false)
          #upper(cap)
        ]
      ]
      v(0.7em)
    }
    render-body-with-marks(safe-content, center-imgs, si, jrn-fig)
  } else if wrap-imgs.len() == 1 {
    // Single photo: wrap the whole article body around it.
    let wi   = wrap-imgs.first()
    let side = resolve-pos(wi, auto-side)
    wrap-one(wi, eval(safe-content, mode: "markup"), side)
  } else {
    // TWO (or more) photos in ONE story → diagonal spread (meander): first photo
    // near the top on one side, second photo at the bottom of the OPPOSITE side,
    // one continuous body threading around both; overflow continues as plain prose.
    let a = wrap-imgs.at(0)
    let b = wrap-imgs.at(1)
    let side-a = resolve-pos(a, auto-side)
    let side-b = resolve-pos(b, flip-side(auto-side))
    two-photo-spread(eval(safe-content, mode: "markup"), a, b, side-a, side-b)
    // A third+ photo (rare in one story) flows full-width centered afterwards.
    for extra in wrap-imgs.slice(2) {
      v(0.7em)
      align(center)[#make-wrap-fig(extra, caption-credit, force-w: "70%")]
      v(0.7em)
    }
  }

  // center-imgs in the wrap case: render after the wrap block.
  // In the no-wrap case they are already interleaved by render-body-with-marks above.
  if wrap-imgs.len() > 0 {
    for img in center-imgs {
      let w   = img.at("width", default: "100%")
      let cap = img.at("caption", default: "")
      v(0.7em)
      align(center)[
        #image(img.at("_local", default: img.path), width: eval(w, mode: "code"))
        #if cap != "" [
          #v(0.25em)
          #set text(font: heading-font, size: 7pt, fill: muted-color, tracking: 0.06em)
          #set par(justify: false)
          #upper(cap)
        ]
      ]
      v(0.7em)
    }
  }

  for gal in section.at("galleries", default: ()) { render-gallery(gal) }
  for tbl in section.tables { render-table(tbl) }
  for cb in section.code_blocks { render-code(cb, mono-font) }
  for co in section.callouts { callout-box(co.at("text"), co.kind) }
}
