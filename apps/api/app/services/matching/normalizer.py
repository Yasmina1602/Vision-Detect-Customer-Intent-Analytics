"""Atributlarni normalizatsiya qilish (uz/ru/en sinonimlar → yagona kalit).

"sariq xudi", "sariq kapyushonli kofta", "yellow hoodie" → demand_key "kiyim|sariq|xudi".
"""
import re

COLORS: dict[str, list[str]] = {
    "qora": ["qora", "black", "черный", "чёрный", "qoracha"],
    "oq": ["oq", "white", "белый", "oppoq"],
    "kulrang": ["kulrang", "grey", "gray", "серый", "kul rang", "kumush", "silver", "серебристый"],
    "qizil": ["qizil", "red", "красный", "bordo", "burgundy", "бордовый"],
    "pushti": ["pushti", "pink", "розовый"],
    "to'q sariq": ["to'q sariq", "orange", "оранжевый", "apelsin rang"],
    "sariq": ["sariq", "yellow", "желтый", "жёлтый", "oltin", "gold", "золотой"],
    "yashil": ["yashil", "green", "зеленый", "зелёный", "xaki", "khaki", "хаки"],
    "ko'k": ["ko'k", "blue", "синий", "moviy"],
    "to'q ko'k": ["to'q ko'k", "navy", "тёмно-синий", "темно-синий"],
    "havorang": ["havorang", "light blue", "голубой", "zangori"],
    "binafsha": ["binafsha", "purple", "violet", "фиолетовый", "siyohrang"],
    "jigarrang": ["jigarrang", "brown", "коричневый", "qo'ng'ir"],
    "bej": ["bej", "beige", "бежевый", "krem", "cream"],
    "rangli": ["rangli", "multicolor", "разноцветный"],
}

# tur → (kategoriya, sinonimlar)
TYPES: dict[str, tuple[str, list[str]]] = {
    "krossovka": ("poyabzal", ["krossovka", "krossovkalar", "sneaker", "sneakers", "кроссовки", "кроссовка", "kedy", "kedi", "кеды"]),
    "tufli": ("poyabzal", ["tufli", "shoes", "туфли", "loafer", "лоферы"]),
    "etik": ("poyabzal", ["etik", "boots", "ботинки", "сапоги", "botinka"]),
    "shippak": ("poyabzal", ["shippak", "tapochka", "sandal", "sandals", "сандалии", "тапочки", "шлепанцы", "slippers"]),
    "xudi": ("kiyim", ["xudi", "hudi", "hoodie", "худи", "kapyushon", "kapyushonli", "kapyushonli kofta", "толстовка"]),
    "sviter": ("kiyim", ["sviter", "sweater", "свитер", "jumper", "kofta", "кофта", "svitshot", "sweatshirt", "свитшот"]),
    "futbolka": ("kiyim", ["futbolka", "t-shirt", "tshirt", "футболка", "mayka", "майка"]),
    "ko'ylak": ("kiyim", ["ko'ylak", "shirt", "рубашка", "dress", "платье", "koylak"]),
    "shim": ("kiyim", ["shim", "jinsi", "jeans", "джинсы", "pants", "trousers", "брюки", "штаны"]),
    "kurtka": ("kiyim", ["kurtka", "jacket", "куртка", "palto", "coat", "пальто", "pidjak", "пиджак", "blazer"]),
    "yubka": ("kiyim", ["yubka", "skirt", "юбка"]),
    "kostyum": ("kiyim", ["kostyum", "suit", "костюм"]),
    "sumka": ("sumka", ["sumka", "bag", "сумка", "handbag", "klatch", "clutch"]),
    "ryukzak": ("sumka", ["ryukzak", "backpack", "рюкзак", "portfel"]),
    "hamyon": ("aksessuar", ["hamyon", "wallet", "кошелек", "кошелёк"]),
    "soat": ("aksessuar", ["soat", "watch", "часы", "smart soat", "smartwatch"]),
    "ko'zoynak": ("aksessuar", ["ko'zoynak", "glasses", "sunglasses", "очки", "kozoynak"]),
    "kepka": ("aksessuar", ["kepka", "cap", "кепка", "shapka", "hat", "шапка", "бейсболка"]),
    "kamar": ("aksessuar", ["kamar", "belt", "ремень"]),
    "telefon": ("elektronika", ["telefon", "smartfon", "phone", "smartphone", "телефон", "смартфон"]),
    "naushnik": ("elektronika", ["naushnik", "quloqchin", "headphones", "earbuds", "наушники"]),
    "noutbuk": ("elektronika", ["noutbuk", "laptop", "notebook", "ноутбук"]),
    "chashka": ("uy-rozgor", ["chashka", "piyola", "cup", "mug", "кружка", "чашка"]),
    "lampa": ("uy-rozgor", ["lampa", "chiroq", "lamp", "лампа", "светильник"]),
    "atir": ("gozallik", ["atir", "parfyum", "perfume", "духи", "парфюм"]),
    "to'p": ("sport", ["to'p", "ball", "мяч", "top"]),
    "o'yinchoq": ("bolalar", ["o'yinchoq", "toy", "игрушка", "oyinchoq"]),
}

CATEGORIES: dict[str, list[str]] = {
    "kiyim": ["kiyim", "clothes", "clothing", "apparel", "одежда", "kiyim-kechak"],
    "poyabzal": ["poyabzal", "shoes", "footwear", "обувь", "oyoq kiyim"],
    "sumka": ["sumka", "bags", "сумки"],
    "aksessuar": ["aksessuar", "accessories", "аксессуары"],
    "elektronika": ["elektronika", "electronics", "электроника", "gadjet"],
    "uy-rozgor": ["uy-rozgor", "uy-ro'zg'or", "home", "дом", "uy uchun", "household"],
    "gozallik": ["gozallik", "go'zallik", "beauty", "красота", "kosmetika"],
    "sport": ["sport", "спорт", "sports"],
    "bolalar": ["bolalar", "kids", "детские", "дети", "children"],
    "boshqa": ["boshqa", "other", "другое"],
}


def clean(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[ʻʼ’‘`´]", "'", text)
    text = re.sub(r"[^\w\s'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _build_index(groups: dict[str, list[str]]) -> list[tuple[str, str]]:
    pairs = [(clean(s), key) for key, syns in groups.items() for s in [key, *syns]]
    return sorted(pairs, key=lambda p: -len(p[0]))  # uzun ibora birinchi ("to'q ko'k" > "ko'k")


_COLOR_IDX = _build_index(COLORS)
_TYPE_IDX = _build_index({k: v[1] for k, v in TYPES.items()})
_CAT_IDX = _build_index(CATEGORIES)


def _find(text: str, index: list[tuple[str, str]]) -> str | None:
    padded = f" {clean(text)} "
    for phrase, key in index:
        if f" {phrase} " in padded:
            return key
    # qo'shimchalar uchun (krossovkalar, ko'ylagi): prefiks moslik, kamida 4 harf
    for word in padded.split():
        for phrase, key in index:
            if " " not in phrase and len(phrase) >= 4 and word.startswith(phrase):
                return key
    return None


def normalize_color(text: str) -> str | None:
    return _find(text, _COLOR_IDX) or (clean(text)[:30] or None)


def normalize_type(text: str) -> str | None:
    return _find(text, _TYPE_IDX) or (clean(text)[:40] or None)


def normalize_category(text: str) -> str:
    return _find(text, _CAT_IDX) or "boshqa"


def category_for_type(type_key: str | None) -> str | None:
    if type_key and type_key in TYPES:
        return TYPES[type_key][0]
    return None


def extract_attributes(text: str) -> dict[str, str]:
    """Erkin matndan (mahsulot nomi, fayl nomi, izoh) atributlarni ajratadi."""
    out: dict[str, str] = {}
    if not text:
        return out
    if c := _find(text, _COLOR_IDX):
        out["color"] = c
    if t := _find(text, _TYPE_IDX):
        out["type"] = t
        out["category"] = TYPES[t][0]
    elif cat := _find(text, _CAT_IDX):
        out["category"] = cat
    return out


def make_demand_key(category: str | None, color: str | None, type_: str | None) -> str:
    return "|".join([category or "boshqa", color or "-", type_ or "-"])[:191]


def canonical_tokens(text: str) -> list[str]:
    """Sinonimlarni kanonik ko'rinishga keltirilgan tokenlar ro'yxati (embedding uchun)."""
    text = clean(text)
    tokens: list[str] = []
    for idx, prefix in ((_COLOR_IDX, "c:"), (_TYPE_IDX, "t:"), (_CAT_IDX, "k:")):
        padded = f" {text} "
        for phrase, key in idx:
            if " " in phrase and f" {phrase} " in padded:
                tokens.append(prefix + key)
                padded = padded.replace(f" {phrase} ", " ")
        text = padded.strip()
    for word in text.split():
        key = None
        for idx, prefix in ((_COLOR_IDX, "c:"), (_TYPE_IDX, "t:"), (_CAT_IDX, "k:")):
            for phrase, k in idx:
                if word == phrase or (len(phrase) >= 4 and " " not in phrase and word.startswith(phrase)):
                    key = prefix + k
                    break
            if key:
                break
        tokens.append(key or word)
    return tokens
