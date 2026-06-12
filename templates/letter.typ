// Business letter template — DIN 5008 / GOST style, clean, no TOC.
//
// Page-as-canvas, letter edition: the letter is built as a function of a scale
// factor and gently sized UP (at most ~15%) when the text is short, so a
// three-paragraph letter doesn't strand in the top third of an empty sheet.
// Business correspondence must stay sober, so the scale range is narrow —
// unlike the resume template, which may scale up to 1.3.
#import "helpers.typ": callout-box, render-table, render-code, render-gallery, render-body-with-marks
#import "@preview/wrap-it:0.1.1": wrap-content

#let doc = json("assets/content.json")
#let p = doc.at("preset", default: (:))

// ── Preset helpers ─────────────────────────────────────────────────────────────
#let body-font    = p.at("body_font",    default: "Source Sans 3")
#let heading-font = p.at("heading_font", default: "Source Sans 3")
#let mono-font    = p.at("mono_font",    default: "Source Code Pro")
#let accent-color = rgb(p.at("accent_color",  default: "#1d3557"))
#let head-color   = rgb(p.at("heading_color", default: "#1a1a1a"))
#let muted-color  = rgb(p.at("muted_color",   default: "#555555"))
#let body-color   = rgb(p.at("body_color",    default: "#1a1a1a"))
#let text-size    = eval(p.at("text_size", default: "11pt"),  mode: "code")
#let h1-size      = eval(p.at("h1_size",   default: "13pt"),  mode: "code")
#let h2-size      = eval(p.at("h2_size",   default: "12pt"),  mode: "code")

#let m-left   = eval(p.at("margin_left",   default: "2.5cm"), mode: "code")
#let m-right  = eval(p.at("margin_right",  default: "2.0cm"), mode: "code")
#let m-top    = eval(p.at("margin_top",    default: "2.0cm"), mode: "code")
#let m-bottom = eval(p.at("margin_bottom", default: "2.0cm"), mode: "code")
#let avail-w  = 21cm   - m-left - m-right
#let avail-h  = 29.7cm - m-top  - m-bottom

// ── Page setup (DIN 5008: 25/20/20/20 mm) ────────────────────────────────────
#set page(
  paper: "a4",
  margin: (left: m-left, right: m-right, top: m-top, bottom: m-bottom),
  // No header/footer for letters
)

// ── The whole letter as a function of scale `s` ───────────────────────────────
#let letter(s) = {
  set text(
    font: body-font,
    size: text-size * s,
    fill: body-color,
    lang: doc.language,
    hyphenate: false,
  )
  set par(
    justify: false,
    leading: eval(p.at("leading", default: "0.65em"), mode: "code"),
    spacing: 0.85em,
  )
  show raw: set text(font: mono-font, size: 0.88em)
  show figure.caption: it => [
    #set text(size: 0.78em, style: "italic", fill: muted-color)
    #set par(justify: false)
    #align(center)[#it.body]
  ]
  show heading.where(level: 1): it => {
    v(1.2em)
    set text(font: heading-font, size: h1-size * s, weight: "bold", fill: head-color)
    it
    v(0.3em)
  }
  show heading.where(level: 2): it => {
    v(0.8em)
    set text(font: heading-font, size: h2-size * s, weight: "semibold", fill: head-color)
    it
    v(0.2em)
  }
  show heading.where(level: 3): it => {
    v(0.6em)
    set text(font: heading-font, size: text-size * s, weight: "semibold", fill: muted-color)
    it
    v(0.15em)
  }
  set heading(numbering: none)

  // Letter header — sender info at top (DIN 5008 Form A)
  if doc.author != "" {
    text(font: heading-font, size: 11pt * s, weight: "semibold")[#doc.author]
    linebreak()
  }
  v(1.5cm)

  // Letter subject / title
  text(font: heading-font, size: 14pt * s, weight: "bold", fill: accent-color)[#doc.title]
  v(0.2em)
  line(length: 100%, stroke: 0.5pt + accent-color.lighten(40%))
  v(0.8cm)

  // Body — sections render as letter paragraphs
  for (si, section) in doc.sections.enumerate() {
    let lvl = section.level
    if lvl == 1 {
      heading(level: 1)[#section.title]
      // метка начала секции для постраничного QC (docs/SPEC_PAGE_FILL.md)
      context [#metadata(here().position()) <bp-sec>]
    }
    else if lvl == 2 { heading(level: 2)[#section.title] }
    else { heading(level: 3)[#section.title] }

    let safe-content = section.content.replace("#", "\\#").replace("\\#link(", "#link(").replace("\\#footnote[", "#footnote[")

    let wrap-imgs = section.images.filter(img =>
      img.at("position", default: "center") in ("left-wrap", "right-wrap")
    )
    let flow-imgs = section.images.filter(img =>
      img.at("position", default: "center") not in ("left-wrap", "right-wrap")
    )

    if wrap-imgs.len() > 0 {
      let body = eval(safe-content, mode: "markup")
      let wi = wrap-imgs.first()
      let w  = wi.at("width", default: "40%")
      let side = if wi.at("position", default: "center") == "left-wrap" { left } else { right }
      let fig = figure(
        image(wi.at("_local", default: wi.path), width: eval(w, mode: "code")),
        caption: if wi.at("caption", default: "") != "" { [#wi.caption] } else { none },
        supplement: none,
      )
      wrap-content(fig, body, align: side + top, column-gutter: 0.8em)
      for img in flow-imgs {
        v(0.8em)
        let w = img.at("width", default: "100%")
        figure(
          image(img.at("_local", default: img.path), width: eval(w, mode: "code")),
          caption: if img.caption != "" { [#img.caption] } else { none },
          supplement: none,
        )
        v(0.5em)
      }
    } else {
      let ltr-fig = im => {
        v(0.8em)
        let w = im.at("width", default: "100%")
        figure(
          image(im.at("_local", default: im.path), width: eval(w, mode: "code")),
          caption: if im.caption != "" { [#im.caption] } else { none },
          supplement: none,
        )
        v(0.5em)
      }
      render-body-with-marks(safe-content, flow-imgs, si, ltr-fig)
    }

    for gal in section.at("galleries", default: ()) { render-gallery(gal) }
    for tbl in section.tables { render-table(tbl) }
    for cb in section.code_blocks { render-code(cb, mono-font) }
    for co in section.callouts { callout-box(co.at("text"), co.kind) }
  }
}

// ── Pick the largest (sober) scale that still fits one page ──────────────────
#context {
  let candidates = (1.15, 1.1, 1.05, 1.0)
  let pick = 1.0
  for s in candidates {
    if measure(box(width: avail-w, letter(s))).height <= avail-h {
      pick = s
      break
    }
  }
  letter(pick)
}
