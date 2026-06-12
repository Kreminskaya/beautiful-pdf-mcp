// Academic RU template — ГОСТ 7.32, 14pt, 1.5x leading, 30/15/20/20 margins
// ГОСТ 7.32: все иллюстрации — по центру, подпись под рисунком. Обтекание текстом не применяется.
#import "helpers.typ": render-code, render-gallery

// ГОСТ: callout-боксы без цвета — серая левая черта, обычный текст
#let callout-box(body, kind) = {
  let safe-body = body.replace("#", "\\#").replace("\\#link(", "#link(").replace("\\#footnote[", "#footnote[")
  v(1.2em)
  block(
    width: 100%,
    stroke: (left: 2pt + luma(160)),
    inset: (left: 12pt, right: 8pt, top: 8pt, bottom: 8pt),
    above: 0pt,
    below: 0pt,
  )[
    #set text(size: 0.9em, fill: luma(30))
    #set par(first-line-indent: 0pt, spacing: 0.5em)
    #eval(safe-body, mode: "markup")
  ]
  v(1.2em)
}

// ГОСТ 7.32: table — simple borders, no fill. Caption above via figure rule.
// The table spans the full text measure (1fr columns) so it reads as a solid
// block of the page, with generous air before and after — not a cramped strip
// glued to the paragraph above it.
#let render-table-gost(tbl, lang: "ru") = {
  v(1.4em, weak: true)
  let col-count = tbl.headers.len()
  figure(
    table(
      columns: (1fr,) * col-count,
      stroke: 0.5pt + luma(80),
      inset: (x: 8pt, y: 7pt),
      align: center + horizon,
      ..tbl.headers.map(h => text(weight: "semibold")[#h]),
      ..tbl.rows.flatten().map(cell => [#cell]),
    ),
    caption: if tbl.caption != "" { [ — #tbl.caption] } else { [] },
    supplement: if lang == "en" { [Table] } else { [Таблица] },
    gap: 0.65em,
  )
  v(1.4em, weak: true)
}

#let doc = json("assets/content.json")
#let p = doc.at("preset", default: (:))

// ── Preset helpers ─────────────────────────────────────────────────────────────
#let body-font    = p.at("body_font",    default: "Times New Roman")
#let heading-font = p.at("heading_font", default: "Times New Roman")
#let mono-font    = p.at("mono_font",    default: "Courier New")
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
  spacing: 0.4em,
  first-line-indent: eval(indent-str, mode: "code"),
)
#show raw: set text(font: mono-font, size: 0.82em)
// ГОСТ: table captions go ABOVE the table
#show figure.where(kind: table): set figure.caption(position: top)
// ГОСТ: captions — regular, near-black. Images: centered; tables: left-aligned.
// position==top means it's a table caption (set above); bottom means image.
#show figure.caption: it => [
  #set text(font: body-font, size: 12pt, fill: body-color)
  #set par(first-line-indent: 0pt, justify: false)
  #let label = [#it.supplement~#context it.counter.display(it.numbering)#it.body]
  #if it.position == top [#label] else [#align(center)[#label]]
]

// ── Heading styles (GOST: bold, centered for H1, left for H2/H3) ─────────────
// block(sticky: true) keeps every heading glued to the text that follows it, so
// a heading can never be stranded alone at the bottom of a page.
// ГОСТ 7.32 п. 6.2.2: каждый раздел основной части начинается с нового листа.
#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  block(sticky: true)[
    #v(1.8em)
    #align(center)[
      #set text(font: heading-font, size: h1-size, weight: "bold", fill: head-color)
      #upper(it.body)
    ]
    #v(0.8em)
  ]
}
#show heading.where(level: 2): it => block(sticky: true)[
  #v(1.4em)
  #set text(font: heading-font, size: h2-size, weight: "bold", fill: head-color)
  #it
  #v(0.5em)
]
#show heading.where(level: 3): it => block(sticky: true)[
  #v(1.0em)
  #set text(font: heading-font, size: h3-size, weight: "bold", fill: head-color)
  #it
  #v(0.4em)
]

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
    #text(font: heading-font, size: 14pt, weight: "bold")[
      #if doc.language == "en" [CONTENTS] else [СОДЕРЖАНИЕ]
    ]
  ]
  #v(0.8em)
  #outline(title: none, indent: 1.5em, depth: 2)
  #pagebreak()
]

// ── Body ──────────────────────────────────────────────────────────────────────
#set heading(numbering: "1.1")

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

  // ГОСТ 7.32: все изображения по центру, подпись под рисунком. Обтекание не
  // применяется. Рисунок вставляется ВНУТРЬ раздела — после абзаца с первым
  // упоминанием (а не после всего текста), и текст продолжается под ним.
  // Поддерживает "after:N" (серверная расстановка, этап 3 SPEC_PAGE_FILL.md).
  // caption: [] → "Рисунок N"; [ — text] → "Рисунок N — text"
  let gost-fig(img) = {
    v(1.0em, weak: true)
    let w = img.at("width", default: "80%")
    let cap = img.at("caption", default: "")
    figure(
      image(img.at("_local", default: img.path), width: eval(w, mode: "code")),
      caption: if cap != "" { [ — #cap] } else { [] },
      supplement: if doc.language == "en" { [Figure] } else { [Рисунок] },
    )
    v(1.0em, weak: true)
  }

  // Делим по абзацам — нужно для меток <bp-para> и after:N.
  // Inline mark вшивается в конец абзаца; чанк eval'ится через join("\n\n") —
  // сохраняется оригинальный spacing (не меняет вёрстку).
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
  let imgs   = section.images
  let n      = imgs.len()
  let cursor = 0
  for (k, im) in imgs.enumerate() {
    let pos-str = im.at("position", default: "auto")
    let cut = if pos-str.starts-with("after:") {
      calc.min(total, calc.max(0, int(pos-str.slice(6))))
    } else {
      calc.max(1, calc.min(total, calc.ceil(total * (k + 1) / (n + 1))))
    }
    render-chunk(cursor, cut)
    cursor = cut
    gost-fig(im)
  }
  render-chunk(cursor, total)

  for gal in section.at("galleries", default: ()) { render-gallery(gal) }
  for tbl in section.tables { render-table-gost(tbl, lang: doc.language) }
  for cb in section.code_blocks { render-code(cb, mono-font) }
  for co in section.callouts { callout-box(co.at("text"), co.kind) }
}
