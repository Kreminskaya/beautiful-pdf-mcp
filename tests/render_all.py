"""Full visual test harness.

Builds a realistic multi-page document for every template (rich text,
captioned images in wrap + center positions, tables, code, callouts) and
renders EVERY page to PNG under tests/output/<template>/.

Run:  python tests/render_all.py            # all templates
      python tests/render_all.py journal    # one template

Reads curated photos from ~/Downloads into tests/output/_fixtures/ (gitignored),
so reruns are stable. Imports the real preset loader + markdown converter from
src/server.py, so what renders here is exactly what the MCP server produces.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from server import _load_preset, _md_to_typst  # noqa: E402

TEMPLATES = ROOT / "templates"
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "tests" / "output"
FIX = OUT / "_fixtures"
DOWNLOADS = Path.home() / "Downloads"

# Curated source photos: editorial portraits + a wide diagram.
PHOTOS = {
    "editorial_1":    "4680850d-6820-4c4f-bca6-6c61f0854b9c.png",  # shearling, highlands (tall)
    "editorial_2":    "ea5e33ed-6aa6-46f7-abe7-36c74062b8ae.png",  # grey jersey, studio (tall)
    "portrait_tall":  "hf_20260601_123843_d6bb3eba-c862-4e3b-ade3-e3868607dfda.png",  # blazer, 1.33
    "portrait_sq1":   "sofia.png",
    "portrait_sq2":   "maya.png",
    "portrait_sq3":   "james.png",
    "diagram_wide":   "hf_20260608_165253_f416ef8a-f8dd-4977-a82c-16eb3637ca4f.png",  # 0.57
}


def fixtures() -> dict:
    FIX.mkdir(parents=True, exist_ok=True)
    out = {}
    for key, name in PHOTOS.items():
        src = DOWNLOADS / name
        dst = FIX / f"{key}.png"
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
        out[key] = str(dst.resolve())
    # Locally drawn fixtures (not photos) live directly in FIX.
    pendulum = FIX / "pendulum_scheme.png"
    if pendulum.exists():
        out["pendulum"] = str(pendulum.resolve())
    return out


# ── Reusable Russian copy (long enough to flow across pages) ────────────────────
LEAD = (
    "Хороший макет начинается с тишины. Когда страница дышит, читатель не замечает "
    "вёрстки — он просто читает. Именно к этому мы стремимся: чтобы текст, "
    "изображения и пустое пространство сложились в спокойный ритм, в котором ничто "
    "не спорит за внимание."
)
PARA = (
    "Типографика — это не украшение, а инженерия внимания. Каждый отступ, каждая "
    "величина интерлиньяжа и каждая ширина полосы набора влияют на то, насколько "
    "легко глаз скользит по строкам. Слишком плотный текст утомляет, слишком "
    "разрежённый — рассыпается на отдельные слова. Баланс рождается из чисел, "
    "проверенных веками: пропорции Ван де Граафа, рекомендации Брингхёрста, "
    "требования ГОСТ. Мы берём эти ориентиры и доводим их до автоматизма."
)
PARA2 = (
    "Изображение в тексте — отдельная история. Оно должно быть достаточно крупным, "
    "чтобы его детали читались, и достаточно скромным, чтобы не разрывать поток. "
    "Подпись под снимком — это не дубликат основного текста, а его тихий "
    "комментарий: другим кеглем, другим начертанием, иным голосом. В журнальной "
    "вёрстке снимок часто обтекается текстом, и тогда особенно важно выдержать "
    "воздух между колонкой и краем фотографии."
)
PARA3 = (
    "Финальная проверка всегда визуальная. Никакие правила не заменят взгляда на "
    "готовую полосу: нет ли висячих строк, не сирота ли первая строка абзаца внизу "
    "страницы, не упёрся ли заголовок в самый низ. Поэтому каждый макет проходит "
    "через превью — страницу за страницей, пока вёрстка не станет невидимой."
)


def doc_base(template, title, author="Наталия Креминская"):
    preset = _load_preset(template)
    return {
        "doc_id": "t", "title": title, "author": author,
        "template": template, "language": "ru", "preset": preset,
        "sections": [],
    }


def sec(title, content, level=1, numbered=True, **kw):
    s = {
        "id": title[:6], "title": title, "content": _md_to_typst(content),
        "level": level, "numbered": numbered,
        "images": [], "galleries": [], "tables": [], "code_blocks": [], "callouts": [],
    }
    s.update(kw)
    return s


def _aspect(path):
    """height / width, mirroring server.py so the template sees real proportions."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            return round(h / w, 3)
    except Exception:
        return 1.3


_WIDTHS = {"full": "100%", "half": "50%", "third": "33%", "quarter": "25%", "large": "80%"}


def img(path, caption="", width="full", position="auto"):
    return {"path": path, "_local": path, "caption": caption,
            "width": _WIDTHS.get(width, width), "position": position, "aspect": _aspect(path)}


def build(template, F):
    """Return a content dict tailored to exercise each template's features."""
    if template == "journal":
        d = doc_base("journal", "Между скалой и небом")
        # Длинная статья с НЕСКОЛЬКИМИ фото — единый поток: оба снимка обтекаются
        # текстом, чередуются по сторонам, страница заполняется до низа.
        s1 = sec("О сдержанности", "\n\n".join([LEAD, PARA, PARA2, PARA3, PARA]), level=1)
        # По умолчанию в журнале подписей под фото НЕТ — передаём фото без caption.
        s1["images"] = [img(F["editorial_1"]), img(F["editorial_2"])]
        s2 = sec("Линия и тишина", "\n\n".join([PARA, PARA3, PARA2]), level=1)
        s2["images"] = [img(F["portrait_tall"])]
        s3 = sec("Полный разворот", "\n\n".join([LEAD, PARA3]), level=1)
        s3["images"] = [img(F["diagram_wide"], "", "100%", "center")]
        d["sections"] = [s1, s2, s3]
        return d

    if template == "report":
        d = doc_base("report", "Квартальный отчёт", "Аналитический отдел")
        s1 = sec("Резюме", "\n\n".join([LEAD, PARA]), level=1)
        s1["images"] = [img(F["diagram_wide"], "Архитектура продукта.", "80%", "center")]
        s1["callouts"] = [{"id": "c", "text": _md_to_typst("**Ключевой вывод:** выручка выросла на 18% к прошлому кварталу."), "kind": "tip"}]
        s2 = sec("Показатели", "\n\n".join([PARA, PARA2]), level=1)
        s2["images"] = [img(F["portrait_sq2"], "Руководитель направления.", "38%", "right-wrap")]
        s2["tables"] = [{"id": "t", "headers": ["Регион", "Выручка", "Рост"],
                          "rows": [["EMEA", "$4.2M", "+18%"], ["APAC", "$3.1M", "+31%"], ["США", "$5.8M", "+12%"]],
                          "caption": "Выручка по регионам"}]
        s3 = sec("Выводы", "\n\n".join([PARA3, PARA]), level=1)
        d["sections"] = [s1, s2, s3]
        return d

    if template == "academic_ru":
        d = doc_base("academic_ru", "Влияние типографики на восприятие текста")
        s1 = sec("Введение", "\n\n".join([PARA, PARA2]), level=1)
        s1["images"] = [img(F["diagram_wide"], "Схема исследования", "85%", "center")]
        s2 = sec("Методология", "\n\n".join([PARA2, PARA3]) + " Подробнее см.#footnote[Подробное описание методики приведено в приложении А.]", level=1)
        s2["tables"] = [{"id": "t", "headers": ["Параметр", "Значение"],
                          "rows": [["Кегль", "14 pt"], ["Интерлиньяж", "1,5"], ["Поле слева", "30 мм"]],
                          "caption": "Параметры вёрстки"}]
        s3 = sec("Результаты", "\n\n".join([PARA, PARA3]), level=1)
        d["sections"] = [s1, s2, s3]
        return d

    if template == "book":
        d = doc_base("book", "Тихая вёрстка", "")
        s1 = sec("Глава первая. Воздух", "\n\n".join([LEAD, PARA, PARA2, PARA3]), level=1)
        s2 = sec("Глава вторая. Ритм", "\n\n".join([PARA, PARA2, PARA3, PARA]), level=1)
        s2["images"] = [img(F["portrait_sq3"], "Портрет наборщика.", "55%", "center")]
        d["sections"] = [s1, s2]
        return d

    if template == "technical":
        d = doc_base("technical", "API: руководство разработчика", "Платформенная команда")
        s1 = sec("Обзор", "\n\n".join([LEAD, PARA]), level=1)
        s1["images"] = [img(F["diagram_wide"], "Конвейер обработки запросов.", "90%", "center")]
        s2 = sec("Быстрый старт", PARA2, level=1)
        s2["code_blocks"] = [{"id": "cb", "language": "python",
                               "code": "from client import API\n\napi = API(token=\"...\")\nresult = api.search(query=\"typography\", limit=10)\nfor item in result:\n    print(item.title, item.score)",
                               "caption": "Пример запроса"}]
        s2["callouts"] = [{"id": "c", "text": _md_to_typst("**Внимание:** токен хранится только в переменных окружения."), "kind": "warning"}]
        s3 = sec("Параметры", PARA3, level=1)
        s3["tables"] = [{"id": "t", "headers": ["Параметр", "Тип", "Описание"],
                          "rows": [["query", "str", "Поисковый запрос"], ["limit", "int", "Число результатов"]],
                          "caption": "Параметры метода search"}]
        d["sections"] = [s1, s2, s3]
        return d

    if template == "portfolio":
        d = doc_base("portfolio", "Портфолио", "Наталия Креминская")
        s1 = sec("О себе", "\n\n".join([LEAD, PARA]), level=1)
        s1["images"] = [img(F["portrait_sq1"], "", "40%", "right-wrap")]
        s2 = sec("Работы", PARA2, level=1)
        s2["galleries"] = [{"id": "g", "columns": 2,
                             "images": [img(F["portrait_sq2"]), img(F["portrait_sq3"]),
                                        img(F["portrait_tall"]), img(F["diagram_wide"])],
                             "caption": "Избранные проекты"}]
        d["sections"] = [s1, s2]
        return d

    if template == "letter":
        d = doc_base("letter", "Деловое письмо", "Наталия Креминская")
        s1 = sec("Уважаемый коллега,", "\n\n".join([LEAD, PARA, PARA3]), level=1, numbered=False)
        d["sections"] = [s1]
        return d

    raise ValueError(template)


# ── Showcase documents — polished English/GOST content for GitHub screenshots ──
EN_LEAD = ("Good layout begins in silence. When a page breathes, the reader forgets the "
           "typesetting and simply reads. That is the whole ambition: to let text, image and "
           "empty space settle into a calm rhythm in which nothing competes for attention.")
EN_P2 = ("Typography is not decoration but the engineering of attention. Every indent, every "
         "measure of leading, every column width decides how easily the eye travels along a line. "
         "Type set too tightly exhausts the reader; set too loosely it scatters into separate words. "
         "Balance is born from numbers proven over centuries: the proportions of Van de Graaf, the "
         "counsel of Bringhurst, the discipline of a well-made grid.")
EN_P3 = ("An image inside running text is a story of its own. It must be large enough for its "
         "detail to read, and modest enough not to tear the flow apart. The caption beneath a "
         "photograph is not a copy of the body text but its quiet aside, set in another size and "
         "another voice.")
EN_P4 = ("In the highlands the light arrives late and leaves early. Between the grey of the rock "
         "and the pale of the sky there is a narrow band of colour, and the whole north seems to hold "
         "its breath. A photograph made there carries that stillness, and the page that frames it must "
         "keep the same air between the column and the edge of the image.")
EN_P5 = ("Restraint is not poverty. A spare page is a deliberate one: the designer has chosen what "
         "to leave out so that what remains can be heard. White space is not waste; it is the rest "
         "between notes, the pause that lets a sentence land.")
EN_P6 = ("The final check is always visual. No rule replaces a long look at the finished spread, "
         "whether a single line hangs alone, whether the first line of a paragraph is orphaned at the "
         "foot of a page, whether a heading is pressed against the very bottom. Each layout passes "
         "through preview, page after page, until the typesetting becomes invisible.")
EN_P7 = ("Consider the long article. It does not live on a single sheet; it moves through several, "
         "and the reader should never feel the seams. A sentence may break across a page, even break at "
         "a hyphen, and continue overleaf without ceremony: no fresh heading, no fuss, simply the next "
         "line where the last one ended.")
EN_P8 = ("This is what it means to think in pages. The sheet of A4 is the unit of design, a canvas "
         "with fixed edges. Whatever falls onto it, text or photographs or a table, must be placed well "
         "within that frame, and whatever does not fit is carried cleanly to the page that follows.")
EN_P9 = ("So the work is never a heap of fragments dropped onto paper. It is a sequence of considered "
         "pages, each one filled from the top to the margin, each one handing the reader gently to the next.")
EN_P10 = ("There is a craft, too, in the seams between pages. A paragraph that ends three lines into a "
          "fresh sheet looks abandoned; a heading stranded at the foot of a column looks careless. The "
          "remedy is not force but foresight: measure the column, count the lines, and let the break fall "
          "where the eye would pause anyway. And so the article simply continues, to be read on.")

# The fairy tale for the book showcase. Natalie will supply her own illustrations;
# fixture portraits stand in for now so the layout can be proofed.
TALE_1 = ("Far beyond the last bus stop, where the road gives up and becomes a path, there "
          "lived a small fox who carried a lantern. Nobody had given it to her; she had found "
          "it one autumn evening, glowing softly under a rowan tree, and the lantern had "
          "simply decided to stay. From that night on, the forest was never quite dark.\n\n"
          "The fox did not think of herself as brave. She was afraid of thunder, of deep "
          "water, and of the long whistle of trains she had never seen. But every evening, "
          "when the shadows grew taller than the pines, she lifted her lantern and walked "
          "the crooked path from the bramble gate to the sleeping pond, so that anyone "
          "lost between the trees could find their way by her little light.\n\n"
          "Mice followed the glow to their burrows. Moths circled it politely, as if "
          "saying good evening. Even the old owl, who pretended to need nobody, secretly "
          "checked from his oak that the small light was on its way.")
TALE_2 = ("One night the wind came down from the hills with rain on its shoulders, and the "
          "lantern went out. The dark rushed in so fast that the fox forgot how her own "
          "paws looked. She sat very still in the middle of the path, hugging the cold "
          "glass, and for the first time the forest heard her cry.\n\n"
          "Then something strange happened. A glow-worm lit up by her left paw. Another "
          "answered by her right. The moths arrived, dusted with pale shimmer, and the "
          "owl glided down with two moonlit feathers. Light by tiny light, the forest "
          "gathered around the fox until the path shone brighter than it ever had under "
          "the lantern alone.\n\n"
          "The fox looked at them all and understood something that warm rooms never "
          "teach: she had never been the only light in the forest. She had only been "
          "the first one.")
TALE_3 = ("The lantern was mended by morning, the wick dried and trimmed by careful mouse "
          "paws. But after that night the fox carried it a little differently, the way "
          "you carry a song everyone around you knows the words to.\n\n"
          "And if you are ever lost between the trees after the last bus has gone, look "
          "for a small light swinging low above the path. Walk towards it without fear. "
          "It has been waiting for you all along.")

GOST_INTRO = ("Ускорение свободного падения входит в число фундаментальных физических "
              "величин: его значение определяет вес тел, параметры движения снарядов и "
              "спутников, показания гравиметров при разведке полезных ископаемых. Несмотря "
              "на кажущееся постоянство, величина g зависит от географической широты, высоты "
              "над уровнем моря и локальных неоднородностей земной коры, поэтому задача её "
              "точного измерения сохраняет практическое значение и сегодня.\n\n"
              "Целью настоящей работы является экспериментальное определение ускорения "
              "свободного падения при помощи математического маятника. Для достижения цели "
              "решались следующие задачи: сборка экспериментальной установки; измерение "
              "периода малых колебаний для пяти значений длины подвеса; вычисление величины "
              "g по результатам измерений; оценка случайной и приборной погрешностей; "
              "сравнение полученного значения со справочным для широты Санкт-Петербурга.\n\n"
              "Маятниковый метод выбран не случайно. Исторически именно маятник был первым "
              "точным инструментом гравиметрии: ещё Х. Гюйгенс в XVII веке связал период "
              "колебаний с длиной подвеса и ускорением свободного падения, а маятниковые "
              "приборы оставались основным средством измерения g вплоть до середины XX века. "
              "Метод нагляден, не требует сложного оборудования и при аккуратной постановке "
              "опыта даёт погрешность менее одного процента, что делает его классической "
              "учебной работой физического практикума.\n\n"
              "Математическим маятником называют идеализированную систему — материальную "
              "точку, подвешенную на невесомой нерастяжимой нити. Реальный маятник может "
              "считаться математическим, если размеры груза малы по сравнению с длиной "
              "подвеса, а масса нити пренебрежимо мала по сравнению с массой груза. Для "
              "малых углов отклонения (до 5°) период колебаний не зависит от амплитуды — "
              "это свойство изохронности и используется в настоящей работе.")
GOST_METHOD = ("Экспериментальная установка состоит из массивного штатива с консолью, нити "
               "длиной от 0,5 до 1,2 м и стального шарика диаметром 25 мм. Схема установки "
               "приведена на рисунке 1. Длина подвеса измерялась стальной линейкой с ценой "
               "деления 1 мм от точки крепления нити до центра шарика; радиус шарика "
               "определялся штангенциркулем как половина диаметра. Время измерялось "
               "электронным секундомером с ценой деления 0,01 с.\n\n"
               "Порядок выполнения опыта был следующим. Нить закреплялась в зажиме консоли, "
               "после чего измерялась длина подвеса. Шарик отклонялся от положения "
               "равновесия на угол не более 5° и отпускался без начальной скорости. После "
               "двух-трёх свободных колебаний, когда движение устанавливалось, включался "
               "секундомер и отсчитывалось время t тридцати полных колебаний. Период "
               "вычислялся как T = t/30: измерение большого числа колебаний уменьшает "
               "относительный вклад погрешности реакции экспериментатора.\n\n"
               "Для каждой из пяти длин подвеса измерение времени повторялось трижды, и в "
               "обработку принималось среднее значение. Случайная погрешность оценивалась "
               "по разбросу повторных измерений с использованием коэффициентов Стьюдента "
               "при доверительной вероятности 0,95; приборная погрешность принималась "
               "равной половине цены деления каждого прибора; суммарная погрешность "
               "вычислялась квадратичным сложением обеих составляющих.")
GOST_RESULTS = ("Период малых колебаний математического маятника связан с длиной подвеса "
                "соотношением T = 2π·√(L/g), откуда ускорение свободного падения выражается "
                "как g = 4π²L/T². Результаты измерений и вычислений для пяти значений длины "
                "подвеса приведены в таблице 1.\n\n"
                "Как видно из таблицы, вычисленные значения g группируются в узком интервале "
                "от 9,77 до 9,82 м/с², систематического дрейфа с ростом длины подвеса не "
                "наблюдается. Это подтверждает применимость модели математического маятника "
                "во всём исследованном диапазоне длин: поправка на конечный радиус шарика "
                "(отношение r/L не превышает 0,025) лежит за пределами достигнутой точности.\n\n"
                "Среднее значение составило g = 9,79 м/с². Случайная погрешность среднего "
                "при доверительной вероятности 0,95 равна ±0,04 м/с²; с учётом приборной "
                "составляющей суммарная погрешность оценивается в ±0,06 м/с². Таким образом, "
                "итоговый результат записывается в виде g = (9,79 ± 0,06) м/с².\n\n"
                "Полученное значение согласуется со справочным для широты Санкт-Петербурга "
                "g = 9,819 м/с²: расхождение составляет 0,3 % и не выходит за пределы "
                "доверительного интервала. Основной вклад в погрешность вносит измерение "
                "длины подвеса — положение центра шарика определяется на глаз, что даёт "
                "неопределённость порядка двух-трёх миллиметров.")
GOST_CONCL = ("В работе экспериментально определено ускорение свободного падения методом "
              "математического маятника. По результатам пяти серий измерений получено "
              "значение g = (9,79 ± 0,06) м/с², согласующееся со справочным значением для "
              "широты Санкт-Петербурга в пределах погрешности эксперимента; расхождение "
              "не превышает 0,4 %.\n\n"
              "Анализ источников погрешности показал, что определяющим является измерение "
              "длины подвеса, тогда как вклад погрешности времени при отсчёте тридцати "
              "колебаний пренебрежимо мал. Точность метода может быть повышена применением "
              "катетометра для измерения длины, увеличением числа одновременно отсчитываемых "
              "колебаний и автоматической регистрацией периода фотодатчиком.\n\n"
              "Результаты работы подтверждают, что даже простейшая маятниковая установка "
              "при корректной методике измерений и обработке данных позволяет определить "
              "фундаментальную физическую константу с точностью лучше половины процента.")


def build_showcase(template, F):
    """Hand-finished documents for GitHub screenshots (and as end-to-end tests)."""
    if template == "journal":
        d = doc_base("journal", "Between Rock and Sky", "Natalia Kreminskaya")
        d["language"] = "en"
        s1 = sec("On Restraint",
                 "\n\n".join([EN_LEAD, EN_P2, EN_P3, EN_P4, EN_P5, EN_P6, EN_P7, EN_P8, EN_P9, EN_P10]),
                 level=1)
        s1["images"] = [img(F["editorial_1"]), img(F["editorial_2"])]
        d["sections"] = [s1]
        return d

    if template == "book":
        d = doc_base("book", "The Lantern Fox", "")
        d["language"] = "en"
        s1 = sec("Chapter One. The Little Light", TALE_1, level=1)
        s1["images"] = [img(F["portrait_sq3"], "", "62%", "center")]
        s2 = sec("Chapter Two. The Night the Wind Came", TALE_2, level=1)
        s2["images"] = [img(F["portrait_sq2"], "", "62%", "center")]
        s3 = sec("Chapter Three. The First One", TALE_3, level=1)
        d["sections"] = [s1, s2, s3]
        return d

    if template == "academic_ru":
        d = doc_base("academic_ru",
                     "Определение ускорения свободного падения при помощи математического маятника")
        s1 = sec("Введение", GOST_INTRO, level=1)
        s2 = sec("Методика измерений", GOST_METHOD, level=1)
        s2["images"] = [img(F.get("pendulum", F["diagram_wide"]),
                            "Схема экспериментальной установки", "68%", "center")]
        s3 = sec("Результаты измерений", GOST_RESULTS, level=1)
        s3["tables"] = [{"id": "t", "headers": ["L, м", "t, с", "T, с", "g, м/с²"],
                          "rows": [["0,50", "42,57", "1,419", "9,81"],
                                   ["0,70", "50,33", "1,678", "9,82"],
                                   ["0,90", "57,12", "1,904", "9,80"],
                                   ["1,10", "63,21", "2,107", "9,78"],
                                   ["1,20", "66,05", "2,202", "9,77"]],
                          "caption": "Результаты измерений и вычислений"}]
        s4 = sec("Заключение", GOST_CONCL, level=1)
        d["sections"] = [s1, s2, s3, s4]
        return d

    if template == "resume":
        d = doc_base("resume", "Natalie Kreminskaya", "Multi-Agent Engineer")
        d["language"] = "en"
        contact = sec("Contact",
                      "Saint Petersburg\ngithub.com/Kreminskaya\nkreminskaya@proton.me", level=1)
        summary = sec("Profile",
                      "I design multi-agent systems that ship: orchestrated LLM pipelines, "
                      "MCP servers and document-generation tools used in production daily. "
                      "I care about the last visual millimetre — software should be useful "
                      "*and* beautiful.", level=1)
        exp = sec("Experience", "", level=1)
        e1 = sec("MCP Engineer — Independent | 2025 — now",
                 "- Built **beautiful-pdf-mcp** — an MCP server that turns LLM output into "
                 "print-ready PDF via Typst: 8 templates, GOST 7.32 support, page-as-canvas layout engine\n"
                 "- Designed **pinterest-vision-mcp** — visual intelligence pipeline for image agents\n"
                 "- Authored agent skills and slash-command toolchains adopted by daily workflows",
                 level=2)
        e2 = sec("AI Creator — Freelance | 2023 — 2025",
                 "- Telegram channel automation: news digests, image generation, post pipelines\n"
                 "- Voice & TTS experiments: Georgian-language tutor stack (XTTS v2, CosyVoice 3)\n"
                 "- Prompt systems and content workflows for small businesses",
                 level=2)
        proj = sec("Selected Projects", "", level=1)
        p1 = sec("beautiful-pdf-mcp | Typst · MCP",
                 "Document engine that thinks in pages: each A4 sheet is composed as a "
                 "complete canvas, with overflow carried cleanly to the next page. Eight "
                 "templates from GOST lab reports to magazine spreads.", level=2)
        p2 = sec("pinterest-vision-mcp | Vision · Pipelines",
                 "Visual-intelligence pipeline that lets image agents search, classify and "
                 "curate boards autonomously.", level=2)
        p3 = sec("Georgian TTS tutor | Speech · ML",
                 "Language-tutor voice stack built on XTTS v2 and CosyVoice 3, trained on "
                 "open CC0 Georgian speech datasets.", level=2)
        skills = sec("Skills",
                     "Python, TypeScript, MCP, Typst, FastAPI, Docker, LLM Orchestration, "
                     "RAG, Telegram Bots, Git", level=1)
        edu = sec("Education", "", level=1)
        edu1 = sec("Self-directed engineering track",
                   "Systems design, agent architectures, typography", level=2)
        langs = sec("Languages", "", level=1)
        l1 = sec("Russian", "native", level=2)
        l2 = sec("English", "professional", level=2)
        l3 = sec("Georgian", "learning", level=2)
        intr = sec("Interests",
                   "Typography, Photography, Tea, Sci-Fi", level=1)
        d["sections"] = [contact, summary, exp, e1, e2, proj, p1, p2, p3,
                         skills, edu, edu1, langs, l1, l2, l3, intr]
        return d

    raise ValueError(f"no showcase for {template}")


def render(template, F, builder=None, out_name=None):
    doc = (builder or build)(template, F)
    work = Path(tempfile.mkdtemp(prefix=f"bpdf_{template}_"))
    assets = work / "assets"
    assets.mkdir()

    # Copy referenced images into assets and rewrite _local to a relative path
    # (Typst resolves leading "/" against the project root, not the FS root).
    def localize(im):
        src = Path(im["path"])
        if src.exists() and not (assets / src.name).exists():
            shutil.copy2(src, assets / src.name)
        im["_local"] = f"assets/{src.name}"
    for s in doc["sections"]:
        for im in s.get("images", []):
            localize(im)
        for g in s.get("galleries", []):
            for im in g.get("images", []):
                localize(im)

    (assets / "content.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    for f in TEMPLATES.glob("*.typ"):
        shutil.copy2(f, work / f.name)

    name = out_name or template
    dest_dir = OUT / name
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True)

    out_tmpl = work / "p_{0p}.png"
    cmd = ["typst", "compile", "--font-path", str(FONTS),
           "--format", "png", "--pages", "1-", "--ppi", "120",
           str(work / f"{template}.typ"), str(out_tmpl)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(work))
    if r.returncode != 0:
        print(f"  ❌ {name}:\n{r.stderr}")
        return False
    pages = sorted(work.glob("p_*.png"))
    for p in pages:
        shutil.copy2(p, dest_dir / p.name)
    warn = "  ⚠ warnings" if r.stderr.strip() else ""
    print(f"  ✓ {name}: {len(pages)} page(s) → tests/output/{name}/{warn}")
    return True


SHOWCASE = ["journal", "book", "academic_ru", "resume"]


def main():
    F = fixtures()
    missing = [k for k, v in F.items() if not Path(v).exists()]
    if missing:
        print(f"⚠ missing fixtures: {missing}")
    args = sys.argv[1:]
    if args and args[0] == "showcase":
        targets = args[1:] or SHOWCASE
        print(f"Rendering showcase: {', '.join(targets)}")
        for t in targets:
            render(t, F, builder=build_showcase, out_name=f"showcase_{t}")
    else:
        targets = args or ["report", "academic_ru", "book", "technical", "portfolio", "letter", "journal"]
        print(f"Rendering: {', '.join(targets)}")
        for t in targets:
            render(t, F)
    print(f"\nDone. Open tests/output/<template>/p_01.png …")


if __name__ == "__main__":
    main()
