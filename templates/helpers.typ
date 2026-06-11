// Shared helper functions — callout boxes, tables, code blocks

#let callout-colors = (
  info:    (bg: rgb("#e8f4fd"), border: rgb("#2980b9"), icon: "ℹ"),
  warning: (bg: rgb("#fef9e7"), border: rgb("#e67e22"), icon: "⚠"),
  tip:     (bg: rgb("#eafaf1"), border: rgb("#27ae60"), icon: "✓"),
  danger:  (bg: rgb("#fdf2f2"), border: rgb("#c0392b"), icon: "✗"),
  quote:   (bg: rgb("#faf6ef"), border: rgb("#c8b48a"), icon: "❝"),
)

#let callout-box(body, kind) = {
  let colors = callout-colors.at(kind, default: callout-colors.info)
  // Escape bare # (hex colors, anchors) but preserve #link(...) we inserted
  let safe-body = body.replace("#", "\\#").replace("\\#link(", "#link(")
  v(0.6em)
  block(
    width: 100%,
    fill: colors.bg,
    stroke: (left: 3pt + colors.border),
    inset: (left: 11pt, right: 9pt, top: 8pt, bottom: 8pt),
    radius: (right: 3pt),
  )[
    #set text(size: 0.92em)
    #eval(safe-body, mode: "markup")
  ]
  v(0.6em)
}

#let render-table(tbl) = {
  v(0.7em)
  let col-count = tbl.headers.len()
  figure(
    table(
      columns: col-count,
      fill: (_, row) => if row == 0 { luma(225) } else if calc.odd(row) { luma(250) } else { white },
      stroke: 0.5pt + luma(185),
      inset: (x: 8pt, y: 5pt),
      ..tbl.headers.map(h => text(weight: "semibold")[#h]),
      ..tbl.rows.flatten().map(cell => [#cell]),
    ),
    caption: if tbl.caption != "" { tbl.caption } else { none },
    supplement: none,
  )
  v(0.5em)
}

#let render-gallery(gallery) = {
  let cols = int(gallery.at("columns", default: 2))
  let imgs = gallery.images
  let gap = 6pt
  // Row height in pt — all images in a row share this height.
  // Width of each image is proportional to its aspect ratio (w/h = 1/aspect).
  // This produces a justified gallery where every row fills the full text width.
  let row-h = gallery.at("row_height_pt", default: 140)

  v(0.8em)
  block(breakable: false)[
    #for row in imgs.chunks(cols) {
      grid(
        columns: row.map(im => (1.0 / im.at("aspect", default: 0.75)) * 1fr),
        gutter: gap,
        ..row.map(im => {
          let local = im.at("_local", default: im.path)
          image(local, height: (row-h * 1pt), fit: "cover")
        })
      )
      v(gap)
    }
    #if gallery.caption != "" {
      v(0.1em)
      align(center)[
        #set text(size: 0.8em, fill: luma(110), style: "italic")
        #gallery.caption
      ]
    }
  ]
  v(0.8em)
}

#let render-code(cb, mono-font) = {
  v(0.6em)
  block(
    width: 100%,
    fill: luma(246),
    stroke: (left: 3pt + luma(200), rest: 0.5pt + luma(215)),
    radius: 3pt,
    inset: (x: 12pt, y: 10pt),
  )[
    #if cb.caption != "" or cb.language != "" [
      #set text(font: mono-font, size: 7.5pt, fill: luma(100))
      #cb.language#if cb.caption != "" and cb.language != "" [ — ]#cb.caption
      #v(0.4em)
    ]
    #set text(font: mono-font, size: 9pt)
    #raw(cb.code, lang: if cb.language != "" { cb.language } else { none })
  ]
  v(0.5em)
}
