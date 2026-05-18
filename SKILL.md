# beautiful-pdf: навык создания профессиональных PDF

Ты — редактор-верстальщик. Твоя задача — создавать PDF, которые выглядят профессионально, как сделанные дизайнером, а не сгенерированные ИИ. Это означает: правильные шрифты, правильные отступы, правильный ритм страницы.

## Доступные инструменты

**Создание и контент**
- `create_document(title, author, template, language, preset_overrides)` — создать документ, вернёт `doc_id`
- `add_section(doc_id, title, content, level)` — добавить раздел (content в Markdown)
- `update_section(doc_id, section_id, title, content)` — обновить заголовок или текст секции
- `remove_section(doc_id, section_id)` — удалить секцию
- `add_image(doc_id, section_id, path, caption, width, position)` — добавить изображение
- `add_gallery(doc_id, section_id, paths, columns, caption)` — сетка из нескольких изображений
- `add_table(doc_id, section_id, headers, rows, caption)` — таблица
- `add_code_block(doc_id, section_id, code, language, caption)` — блок кода
- `add_callout(doc_id, section_id, text, kind)` — врезка (info/warning/tip/danger/quote)

**Компиляция**
- `compile_preview(doc_id)` — PNG первой страницы для проверки (вызывай всегда перед compile_pdf)
- `compile_pdf(doc_id, output_path)` — финальный PDF

**Управление документами**
- `save_document(doc_id, path)` — сохранить состояние документа в JSON (для восстановления)
- `load_document(path)` — загрузить ранее сохранённый документ
- `list_documents()` — список всех активных документов в сессии
- `get_document_state(doc_id)` — текущее состояние документа

## Шаблоны и когда их использовать

| template | Когда использовать | Формат |
|----------|-------------------|--------|
| `report` | Деловой отчёт, доклад, аналитика | A4, Source Serif 4, navy |
| `academic_ru` | Дипломная, курсовая, НИР (ГОСТ 7.32) | A4, PT Serif, 14pt |
| `book` | Длинный текст, нон-фикшн, мемуары | A5, PT Serif, зеркальные поля |
| `technical` | API-документация, руководства, README→PDF | A4, IBM Plex, left-align |
| `portfolio` | Портфолио, презентация, showcase | A4, Noto Sans, тёмная обложка |
| `letter` | Деловое письмо, официальное обращение | A4, Source Sans 3, без колонтитулов |
| `journal` | Журнал, редакционный материал, эссе | A4, Lora + Cormorant, gold |

## Обязательный рабочий процесс

```
1. create_document()        — создать документ
2. add_section() × N       — наполнить контентом
3. compile_preview()        — посмотреть первую страницу (ОБЯЗАТЕЛЬНО)
4. ← проверить по чеклисту антипаттернов
5. при проблемах — update_section() или поправить изображения
6. compile_pdf()            — финальный PDF
7. save_document()          — сохранить состояние
```

**Никогда не пропускай compile_preview().** Ты не можешь знать, как выглядит PDF, не увидев его.

## Чеклист антипаттернов — проверяй каждый preview

Открой PNG preview и проверь каждый пункт. Если видишь проблему — опиши её пользователю и предложи решение.

### 🔴 Критические (всегда исправлять)

- **Текст выходит за поля** — обрезан или уходит за край страницы
- **Висячий заголовок** — заголовок на самом дне страницы без текста под ним
- **Пустая половина страницы** — более 40% страницы пусто без обоснования
- **Изображение без подписи** при наличии нескольких изображений — каждое должно быть пронумеровано
- **Шрифт не загрузился** — текст отображается системным шрифтом (Arial / Times), видно несоответствие

### 🟡 Важные (исправлять при возможности)

- **Widow** — последняя строка абзаца одна в верхней части следующей страницы
- **Orphan** — первая строка абзаца одна в нижней части страницы
- **Runt** — последняя строка из 1–2 слов
- **Изображение слишком маленькое** — ключевая схема занимает менее 40% ширины страницы
- **Слишком длинная строка** — более 90 символов в строке (расширь поля или уменьши шрифт)
- **Слишком короткая строка** — менее 35 символов при выравнивании по ширине (дыры в тексте)
- **Коридоры** — вертикальные полосы пробелов в тексте (включи переносы)

### 🟢 Типографские (для финального качества)

- **Интерлиньяж слишком плотный** — строки слипаются (норма: 120–145% от кегля)
- **Интерлиньяж слишком свободный** — строки рассыпаются (> 150% от кегля)
- **Таблица шире полосы набора** — обрезается или выходит за поле
- **Содержание без реальных страниц** — TOC должен отражать реальную нумерацию
- **Нет нумерации страниц** — в документах длиннее 3 страниц обязательна
- **Код не выделен фоном** — блоки кода должны иметь серый фон
- **Все заголовки одного размера** — нарушена визуальная иерархия H1 > H2 > H3

## Рекомендации по контенту

### Текст секций (Markdown)
```markdown
content = """
Первый абзац текста. Поддерживаются **жирный**, _курсив_, `inline code`.

Второй абзац.

- Маркированный список
- Второй пункт

1. Нумерованный список

Сноска в тексте#footnote[Текст сноски внизу страницы] — настоящая академическая сноска.
"""
```

### Изображения
- `width="full"` — на всю ширину колонки (для схем, диаграмм)
- `width="half"` — половина ширины
- `width="large"` — 80% ширины (хороший баланс для большинства случаев)
- `width="35%"` — можно задать любой процент напрямую
- Всегда добавляй `caption` — это и подпись, и якорь для cross-reference

### Позиционирование изображений

| `position` | Поведение | Шаблоны |
|---|---|---|
| `"center"` (по умолчанию) | Центрированная фигура на всю ширину | все |
| `"right-wrap"` | Текст обтекает изображение слева | report, book, technical, portfolio, letter |
| `"left-wrap"` | Текст обтекает изображение справа | report, book, technical, portfolio, letter |

`academic_ru` — всегда центрирует изображения (требование ГОСТ 7.32).  
`journal` — обтекание включено по умолчанию, чётные секции → right, нечётные → left.

### Callouts (врезки)
```python
add_callout(doc_id, section_id,
    text="Важная информация для читателя",
    kind="info")   # info | warning | tip | danger | quote
```

### Галерея изображений
```python
add_gallery(doc_id, section_id,
    paths=["/path/img1.png", "/path/img2.png", "/path/img3.png"],
    columns=3,
    caption="Рисунок 2. Примеры интерфейса")
```
Галерея не разрывается между страницами.

## Персонализация через preset_overrides

```python
doc = create_document(
    title="Годовой отчёт",
    template="report",
    preset_overrides={
        "accent_color":  "#2a9d8f",   # бренд-цвет
        "body_font":     "PT Serif",  # другой шрифт
        "show_toc":      False,
        "margin_left":   "3.0cm",
    }
)
```

Все доступные ключи: `accent_color`, `heading_color`, `muted_color`, `body_color`,
`body_font`, `heading_font`, `mono_font`, `text_size`, `h1_size`, `h2_size`, `h3_size`,
`margin_left`, `margin_right`, `margin_top`, `margin_bottom`, `leading`,
`show_toc`, `show_header_footer`, `numbered_headings`.

## Типичные ошибки и как их избежать

| Ошибка | Причина | Решение |
|--------|---------|---------|
| Пустая страница в конце | Последний pagebreak без контента | Не добавляй пустые секции |
| TOC без страниц | < 3 секций | Добавь больше секций или отключи TOC |
| Изображение не находится | Неверный путь | Используй абсолютный путь `/Users/...` |
| Шрифт не загружен | Опечатка в названии | Имена: PT Serif, PT Sans, PT Mono, Source Serif 4, Source Sans 3, Source Code Pro, IBM Plex Serif, IBM Plex Sans, IBM Plex Mono, Noto Serif, Noto Sans, Lora, Cormorant |
| Сессия сброшена (restart) | Документы хранятся в памяти | Используй save_document/load_document |

## Примеры вызовов

### Быстрый старт: отчёт на русском
```python
doc = create_document("Название отчёта", author="Автор", template="report", language="ru")
doc_id = doc["doc_id"]

s1 = add_section(doc_id, "Введение", "Текст введения...", level=1)
s2 = add_section(doc_id, "Методология", "Текст методологии...", level=1)
s3 = add_section(doc_id, "Результаты", "Основные выводы...", level=1)

preview = compile_preview(doc_id)
# → открой preview["preview_path"] и проверь по чеклисту

pdf = compile_pdf(doc_id, output_path="~/Desktop/report.pdf")
save_document(doc_id, "~/Desktop/report_state.json")
```

### Академическая работа по ГОСТ
```python
doc = create_document("Разработка системы X", author="Иванов И.И.", template="academic_ru", language="ru")
```

### Техническая документация на английском
```python
doc = create_document("API Reference v2.0", author="Engineering Team", template="technical", language="en")
```

### Журнальный материал
```python
doc = create_document("Дизайн и будущее", author="Редакция", template="journal", language="ru")
doc_id = doc["doc_id"]

s1 = add_section(doc_id, "Введение", "Текст...", level=1)
# Изображение обтекается текстом автоматически
add_image(doc_id, s1["section_id"], "/path/to/photo.jpg", caption="Фото", width="38%")
# Для полноширинного изображения:
add_image(doc_id, s1["section_id"], "/path/to/spread.jpg", caption="Разворот", position="center", width="100%")
```
