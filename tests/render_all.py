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
import layout_qc  # noqa: E402

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
    # Иллюстрации Натали к сказке «Goodnight, Little Bear»
    "baby_moon":      "hf_20260611_082142_8fba0ba1-8de7-4d89-a0e7-beb5d9c655c9.png",  # 0.81
    "baby_forest":    "hf_20260611_082533_d571b197-cec2-4894-9fd2-d7705de65f98.png",  # 0.56
    # Paris café — journal showcase second section
    "paris_cafe":     "40ffcad5-9167-4995-9b18-0cf2abab6a65.png",
}


# Expected pixel size per fixture — used to synthesize placeholders when the
# original photos are absent (they are personal and not bundled with the repo).
PLACEHOLDER_SIZES = {
    "editorial_1":   (1024, 1536),
    "editorial_2":   (1024, 1536),
    "portrait_tall": (1200, 1600),
    "portrait_sq1":  (1024, 1024),
    "portrait_sq2":  (1024, 1024),
    "portrait_sq3":  (1024, 1024),
    "diagram_wide":  (1600, 912),
    "baby_moon":     (1024, 832),
    "baby_forest":   (1600, 896),
    "paris_cafe":    (1536, 2048),
}


def _make_placeholder(dst: Path, key: str) -> None:
    """Neutral stand-in image so the test suite runs without the source photos."""
    from PIL import Image, ImageDraw
    w, h = PLACEHOLDER_SIZES.get(key, (1200, 1600))
    im = Image.new("RGB", (w, h), (208, 202, 192))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, w - 1, h - 1], outline=(170, 162, 150), width=6)
    dr.line([(0, 0), (w, h)], fill=(190, 183, 172), width=3)
    dr.line([(w, 0), (0, h)], fill=(190, 183, 172), width=3)
    im.save(dst)


def fixtures() -> dict:
    FIX.mkdir(parents=True, exist_ok=True)
    out = {}
    placeholders = []
    for key, name in PHOTOS.items():
        src = DOWNLOADS / name
        dst = FIX / f"{key}.png"
        if not dst.exists():
            if src.exists():
                shutil.copy2(src, dst)
            else:
                _make_placeholder(dst, key)
                placeholders.append(key)
        out[key] = str(dst.resolve())
    if placeholders:
        print(f"ℹ source photos not found — neutral placeholders generated for: "
              f"{', '.join(placeholders)}")
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
EN_P8 = ("This is what it means to think in pages: measure the column, count the lines — "
         "and let the article simply continue, to be read on.")
EN_P9 = ("So the work is never a heap of fragments dropped onto paper. It is a sequence of considered "
         "pages, each one filled from the top to the margin, each one handing the reader gently to the next.")
EN_P10 = ("There is a craft, too, in the seams between pages. A paragraph that ends three lines into a "
          "fresh sheet looks abandoned; a heading stranded at the foot of a column looks careless. The "
          "remedy is not force but foresight: measure the column, count the lines, and let the break fall "
          "where the eye would pause anyway. And so the article simply continues, to be read on.")

# Second journal section — Paris café editorial, pairs with paris_cafe.png wrap image.
JRN2_P1 = ("October light in Paris arrives sideways. It skims the marble tabletops, "
            "pools in the hollow of a coffee cup, and turns even the plainest corner of a "
            "pavement café into something worth pausing over. The season asks very little: "
            "only that you sit still for a moment and let it do its work.")
JRN2_P2 = ("A good coat is not a purchase but a decision. The camel and the chocolate and the "
            "deep tobacco tones that return every autumn are not trends; they are the city's own "
            "palette, borrowed from its stone and its river. Wear one and you disappear into "
            "Paris in the best possible way — present, but not insisting.")
JRN2_P3 = ("There is a particular art to being alone at a café table without appearing to wait "
            "for anyone. It requires gloves, a certain angle of the shoulder, and the willingness "
            "to look out at the street as though you wrote the scene yourself. The coffee goes cold. "
            "You do not mind.")
JRN2_P4 = ("The glasses are always tortoiseshell. This is not a rule anyone wrote down, yet every "
            "October they reappear on every terrace, as reliable as the chestnuts and the grey sky. "
            "Some things simply belong to a season, and the season keeps them.")
JRN2_P5 = ("Leather gloves are back — not as a statement but as a quiet given, the way a good "
            "watch is simply there on the wrist without asking to be noticed. The shade is always "
            "dark: oxblood, espresso, forest at dusk. They make the hands look considered, which "
            "is a different thing from looking dressed.")
JRN2_P6 = ("The streets are quieter now. The tourists left with August, and what remains is "
            "the city as it prefers itself: purposeful, a little private, moving at a pace that "
            "allows a person to notice the light on the façades and the smell of something baking "
            "somewhere behind a closed door.")
JRN2_P7 = ("Autumn dressing is, at its best, a kind of editing. You subtract the summer's "
            "looseness and replace it with weight and intention — a heavier fabric, a darker "
            "tone, a silhouette that knows where it is going. The result, when it works, "
            "is not elegance exactly. It is something quieter: the look of a person at ease "
            "with the season.")
JRN2_P8 = ("The café stays open until the cold makes it unreasonable. Then it closes for "
            "the season and the chairs go in, and the marble tables are stacked somewhere "
            "inside, and the street looks a little less like itself for a while. But by then "
            "you are already somewhere else — a coat heavier, a cup warmer, "
            "moving through a city that has put on its good clothes for winter.")
JRN2_P9 = ("What October gives, it gives without apology: the smell of wet stone, "
            "the weight of a good coat, the particular satisfaction of a coffee that "
            "arrives exactly when you needed it. You take what is offered. You leave "
            "nothing on the table.")

# The fairy tale for the book showcase. Natalie will supply her own illustrations;
# fixture portraits stand in for now so the layout can be proofed.
# «Goodnight, Little Bear» — малышковая сказка под иллюстрации Натали.
# Часть 1 (после фронтисписа с луной), часть 2 — диалоги с мишкой (после леса).
BEAR_P1 = ("When the night-light woke up and the curtains had quite finished breathing, "
           "something rather wonderful happened in the smallest bedroom of the house: "
           "little Leo sailed away on his pillow — up and up and up — until the pillow "
           "became the moon, and the moon, as moons will do when nobody sensible is "
           "watching, became a boat.")
BEAR_P2 = ("It rocked him gently, the way his mama did. The little stars crowded round "
           "to look at him. \"Shhh,\" said the biggest star, who was in charge. \"He "
           "is dreaming.\" And they all leaned in, very carefully, so as not to wobble "
           "the moon. One small star — the very tiniest, who was new and did not yet "
           "know the rules — whispered, \"But what is he dreaming?\" Nobody answered. "
           "That, of course, was exactly what they were all waiting to find out.")
BEAR_P2B = ("The night was warm and smelled of something — beeswax, perhaps, or the "
            "inside of an old wooden chest — and the sky was the particular shade of "
            "dark blue that only appears after nine o'clock when everyone small is "
            "supposed to be asleep. Leo did not know any of this. He was already "
            "somewhere else entirely.")
BEAR_P2C = ("He had no hat, no coat, no lantern. He had only his pyjamas — the ones "
            "with the small blue rabbits on them — and his own particular kind of "
            "courage, which was the sort that does not know it is courage at all, "
            "and therefore works perfectly well.")
BEAR_P3 = ("And in the dream there was a path — a polite, patient sort of path — "
           "leading into a soft green forest where tiny stars hung from the branches "
           "like golden apples, ripening quietly in the dark.")
BEAR_P3B = ("The forest was not frightening. Forests in dreams never are, if you are "
            "the right sort of person, and Leo was exactly the right sort. The trees "
            "had smooth grey bark and the leaves made a sound like pages turning, "
            "and every now and then one of the little stars would drop very slowly "
            "to the ground and lie there, glowing faintly, until a moth came to "
            "carry it away.")
BEAR_P3C = ("He walked without hurrying, because there was nowhere to be late for. "
            "The path turned left, then right, then left again, and each time it "
            "turned there was something new to see: a sleeping hedgehog curled "
            "beneath a root, a pair of spectacles hanging from a twig as though "
            "somebody had left them there on purpose, a small wooden signpost that "
            "said FURTHER in very confident letters.")
BEAR_P4 = ("Someone warm was waiting under the trees. It was Button — his very own "
           "teddy bear, the one who slept in his arms every single night — a bear with, "
           "as it happens, a great many important duties.")
BEAR_D1 = ("\"Hello, Leo,\" said Button, and took his hand.\n\n"
           "\"Hello, Button,\" said Leo. \"Are you real in dreams?\"\n\n"
           "\"In dreams,\" said Button, with the quiet dignity of a very small bear, "
           "\"I am the realest bear of all.\"")
BEAR_D2 = ("\"Where do the little stars come from?\" asked Leo.\n\n"
           "\"The trees grow them,\" said Button. \"One for every child who is asleep. "
           "Look — that one there is yours. It came out the moment you started "
           "snoring.\"\n\n"
           "\"I don't snore,\" said Leo — and Button nodded, very kindly indeed.")
BEAR_D3 = ("\"And if I wake up?\" asked Leo.\n\n"
           "\"Then I shall be right there in your arms,\" said Button. \"That is my "
           "job, you see. Walking in dreams, hugging in mornings.\"")
BEAR_P5 = ("And when morning came tiptoeing into the room, Button was right there "
           "in Leo's arms — as though he had never been anywhere at all.")

GOST_INTRO = ("The acceleration due to gravity is among the most fundamental physical "
              "constants: its value determines the weight of bodies, the trajectories of "
              "projectiles and satellites, and the readings of gravimeters used in mineral "
              "exploration. Despite its apparent constancy, g varies with geographic latitude, "
              "altitude above sea level, and local density anomalies in Earth's crust — making "
              "its precise measurement a task of enduring practical relevance.\n\n"
              "The purpose of this work is to determine the acceleration due to gravity "
              "experimentally using a simple pendulum. To achieve this goal, the following "
              "tasks were carried out: assembly of the experimental apparatus; measurement of "
              "the period of small oscillations for five different suspension lengths; "
              "calculation of g from the measured data; estimation of random and instrumental "
              "uncertainties; and comparison of the result with the reference value for the "
              "latitude of Saint Petersburg.\n\n"
              "The pendulum method was chosen deliberately. Historically, the pendulum was the "
              "first accurate gravimetric instrument: Christiaan Huygens related the period of "
              "oscillation to the suspension length and gravitational acceleration as early as "
              "the seventeenth century, and pendulum instruments remained the principal means "
              "of measuring g until the mid-twentieth century. The method is transparent, "
              "requires no complex equipment, and — when carried out carefully — yields an "
              "uncertainty below one percent, making it a classical introductory physics "
              "experiment.\n\n"
              "A simple pendulum is an idealised system consisting of a point mass suspended "
              "on a massless, inextensible string. A real pendulum approximates this model "
              "when the bob dimensions are small compared with the string length and the "
              "string mass is negligible relative to the bob mass. For amplitudes below "
              "approximately 5° the period is independent of amplitude — the property of "
              "isochronism exploited in this experiment.")
GOST_METHOD = ("The experimental apparatus consisted of a heavy retort stand with a clamp, "
               "a string of length 0.5 to 1.2 m, and a steel ball 25 mm in diameter. "
               "The setup is illustrated in Figure 1. The suspension length was measured "
               "with a steel ruler graduated in 1 mm increments, from the attachment point "
               "of the string to the centre of the ball; the ball radius was determined with "
               "a vernier caliper as half the measured diameter. Time was recorded with a "
               "digital stopwatch with a resolution of 0.01 s.\n\n"
               "The experimental procedure was as follows. The string was secured in the "
               "stand clamp, and the suspension length was measured. The ball was displaced "
               "from equilibrium by no more than 5° and released from rest. After two or "
               "three free oscillations, once steady motion was established, the stopwatch "
               "was started and the time t for thirty complete oscillations was recorded. "
               "The period was calculated as T = t / 30: counting a large number of "
               "oscillations reduces the relative contribution of the experimenter's "
               "reaction time to the overall uncertainty.\n\n"
               "For each of the five suspension lengths, the timing was repeated three "
               "times, and the mean value was used in the analysis. Random uncertainty "
               "was estimated from the spread of repeated measurements using Student's "
               "t-factor at a confidence level of 0.95; instrumental uncertainty was "
               "taken as half the smallest graduation of each instrument; the combined "
               "uncertainty was obtained by adding both components in quadrature.")
GOST_RESULTS = ("The period of small oscillations of a simple pendulum is related to the "
                "suspension length by T = 2π√(L/g), from which the acceleration due to "
                "gravity is expressed as g = 4π²L/T². The measurement and calculation "
                "results for five suspension lengths are given in Table 1.\n\n"
                "As the table shows, the calculated values of g fall within the narrow range "
                "9.77 to 9.82 m/s², with no systematic trend as the suspension length "
                "increases. This confirms that the simple-pendulum model is applicable across "
                "the full range of lengths studied: the correction for the finite ball radius "
                "(the ratio r/L does not exceed 0.025) lies below the precision achieved.\n\n"
                "The mean value obtained is g = 9.79 m/s². The random uncertainty of the "
                "mean at a confidence level of 0.95 is ±0.04 m/s²; including the "
                "instrumental component, the combined uncertainty is estimated at "
                "±0.06 m/s². The final result is therefore g = (9.79 ± 0.06) m/s².\n\n"
                "This value is consistent with the reference value for the latitude of "
                "Saint Petersburg, g = 9.819 m/s²: the discrepancy is 0.3 % and lies "
                "within the confidence interval. The dominant source of uncertainty is the "
                "measurement of the suspension length — the position of the ball's centre "
                "is estimated by eye, introducing an indeterminacy of approximately two to "
                "three millimetres.")
GOST_CONCL = ("This work experimentally determined the acceleration due to gravity using "
              "the simple-pendulum method. From five series of measurements the value "
              "g = (9.79 ± 0.06) m/s² was obtained, which agrees with the reference value "
              "for the latitude of Saint Petersburg within the experimental uncertainty; "
              "the discrepancy does not exceed 0.4 %.\n\n"
              "Analysis of the uncertainty sources showed that the dominant contribution "
              "comes from the measurement of the suspension length, whereas the contribution "
              "from timing uncertainty — when thirty oscillations are counted — is negligible. "
              "The accuracy of the method could be improved by using a cathetometer to "
              "measure the suspension length, by increasing the number of oscillations "
              "counted in a single run, and by recording the period automatically with "
              "a photogate.\n\n"
              "The results confirm that even a simple pendulum apparatus, when measurement "
              "and data analysis are carried out correctly, allows a fundamental physical "
              "constant to be determined to better than half a percent.")


def build_showcase(template, F):
    """Hand-finished documents for GitHub screenshots (and as end-to-end tests)."""
    if template == "journal":
        d = doc_base("journal", "Between Rock and Sky", "Natalia Kreminskaya")
        d["language"] = "en"
        s1 = sec("On Restraint",
                 "\n\n".join([EN_LEAD, EN_P2, EN_P3, EN_P4, EN_P5, EN_P6, EN_P7,
                               EN_P8, EN_P9, EN_P10]),
                 level=1)
        s1["images"] = [img(F["editorial_1"]), img(F["editorial_2"])]
        s2 = sec("The October Edit",
                 "\n\n".join([JRN2_P1, JRN2_P2, JRN2_P3, JRN2_P4,
                               JRN2_P5, JRN2_P6, JRN2_P7, JRN2_P8]),
                 level=1)
        s2["images"] = [img(F["paris_cafe"], "", "46%", "right-wrap")]
        d["sections"] = [s1, s2]
        return d

    if template == "book":
        # Малышковая сказка с иллюстрациями Натали: луна — фронтиспис ДО текста,
        # лес с мишкой — между первой и второй частью (диалоги после).
        d = doc_base("book", "Goodnight, Little Bear", "")
        d["language"] = "en"
        s1 = sec("The Moon Boat", "\n\n".join([BEAR_P1, BEAR_P2, BEAR_P2B, BEAR_P2C,
                                               BEAR_P3, BEAR_P3B, BEAR_P3C, BEAR_P4,
                                               BEAR_D1, BEAR_D2, BEAR_D3]), level=1)
        s1["images"] = [img(F["baby_moon"], "", "65%", "top"),
                        img(F["baby_forest"], "", "80%", "after:7")]
        d["sections"] = [s1]
        return d

    if template == "academic_ru":
        d = doc_base("academic_ru",
                     "Determination of the Acceleration due to Gravity Using a Simple Pendulum",
                     "Natalia Kreminskaya")
        d["language"] = "en"
        s1 = sec("Introduction", GOST_INTRO, level=1)
        s2 = sec("Experimental Method", GOST_METHOD, level=1)
        s2["images"] = [img(F.get("pendulum", F["diagram_wide"]),
                            "Experimental setup schematic", "68%", "center")]
        s3 = sec("Results and Discussion", GOST_RESULTS, level=1)
        s3["tables"] = [{"id": "t", "headers": ["L, m", "t, s", "T, s", "g, m/s²"],
                          "rows": [["0.50", "42.57", "1.419", "9.81"],
                                   ["0.70", "50.33", "1.678", "9.82"],
                                   ["0.90", "57.12", "1.904", "9.80"],
                                   ["1.10", "63.21", "2.107", "9.78"],
                                   ["1.20", "66.05", "2.202", "9.77"]],
                          "caption": "Measurement results and calculated values"}]
        s4 = sec("Conclusion", GOST_CONCL, level=1)
        d["sections"] = [s1, s2, s3, s4]
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

    # Постраничный QC «страница = блок» (docs/SPEC_PAGE_FILL.md)
    section_pages = layout_qc.query_section_pages(
        work / f"{template}.typ", FONTS, work)
    contract = layout_qc.load_contract(ROOT / "data" / "styles.json", template)
    report = layout_qc.analyze_document(
        [str(dest_dir / p.name) for p in pages], doc["preset"], contract,
        section_pages)
    for pg in report["pages"]:
        if pg["verdict"] == "FRONT_MATTER":
            continue
        mark = "·" if pg["verdict"] == "OK" else "✗"
        detail = "; ".join(pg.get("issues", [])) or \
            f"fill {pg.get('fill', 0):.0%}"
        print(f"     {mark} стр.{pg['page']}: {detail}")
    if not report["ok"]:
        print(f"  ✗ {name}: {report['summary']}")
    return report["ok"]


SHOWCASE = ["journal", "book", "academic_ru"]


def main():
    F = fixtures()
    missing = [k for k, v in F.items() if not Path(v).exists()]
    if missing:
        print(f"⚠ missing fixtures: {missing}")
    args = sys.argv[1:]
    failed = []
    if args and args[0] == "showcase":
        targets = args[1:] or SHOWCASE
        print(f"Rendering showcase: {', '.join(targets)}")
        for t in targets:
            if not render(t, F, builder=build_showcase, out_name=f"showcase_{t}"):
                failed.append(t)
    else:
        targets = args or ["report", "academic_ru", "book", "technical", "portfolio", "letter", "journal"]
        print(f"Rendering: {', '.join(targets)}")
        for t in targets:
            render(t, F)
    print(f"\nDone. Open tests/output/<template>/p_01.png …")
    if failed:
        print(f"✗ QC «страница = блок» провален: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
