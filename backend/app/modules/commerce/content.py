"""Seed catalogue: products and plans.

STATUS: DRAFT. Every price, plan, inclusion and title below is a PLACEHOLDER
written by the development team so purchase flows can be built and tested.
Row 61 (subscription structure) and row 62 (monetisation boundaries) are open
client decisions. The client sets real values in the admin (rows 55, 57).
Seeded once; never overwritten by a re-seed.
"""


def L(en: str, ar: str) -> dict:
    return {"en": en, "ar": ar}


SEASONS = {
    "spring": L("Spring", "الربيع"),
    "summer": L("Summer", "الصيف"),
    "autumn": L("Autumn", "الخريف"),
    "winter": L("Winter", "الشتاء"),
}
BODY_SHAPES = {
    "hourglass": L("Hourglass", "الساعة الرملية"),
    "pear": L("Pear", "الكمّثرى"),
    "inverted_triangle": L("Inverted triangle", "المثلّث المقلوب"),
    "rectangle": L("Rectangle", "المستطيل"),
    "apple": L("Apple", "التفّاحة"),
}

# Premium membership unlocks every guide and the full report.
PREMIUM = "premium"

PRODUCTS = []
for season, name in SEASONS.items():
    PRODUCTS.append({
        "key": f"guide.palette.{season}",
        "kind": "guide",
        "feature_key": "phase1.free_resources",
        "title": L(f"{name['en']} colour palette", f"لوحة ألوان {name['ar']}"),
        "description": L("Your season's colours to take shopping.", "ألوان موسمك لترافقك عند التسوّق."),
        "is_free": True,
        "price_minor": 0,
        "payload": {"document": "seasonal_palette", "season": season},
    })
    PRODUCTS.append({
        "key": f"guide.lip_blush.{season}",
        "kind": "guide",
        "feature_key": "phase1.digital_guides",
        "title": L(f"{name['en']} lipstick and blush palette", f"لوحة أحمر الشفاه والخدود لموسم {name['ar']}"),
        "description": L("Lip and blush shades for your season.", "درجات أحمر الشفاه والخدود المناسبة لموسمك."),
        "price_minor": 1900,
        "payload": {"document": "lip_blush_palette", "season": season},
    })
for shape, name in BODY_SHAPES.items():
    PRODUCTS.append({
        "key": f"guide.body.{shape}",
        "kind": "guide",
        "feature_key": "phase1.digital_guides",
        "title": L(f"{name['en']} body-shape guide", f"دليل شكل الجسم: {name['ar']}"),
        "description": L("What to wear to balance and flatter your shape.", "ما ترتدينه لإبراز تناسق قوامك."),
        "price_minor": 2900,
        "payload": {"document": "body_shape_guide", "shape": shape},
    })
PRODUCTS += [
    {
        "key": "guide.personal_style",
        "kind": "guide",
        "feature_key": "phase1.digital_guides",
        "title": L("Your personalised style guide", "دليل أسلوبك الشخصي"),
        "description": L("All your results and advice in one guide.", "جميع نتائجك ونصائحك في دليل واحد."),
        "price_minor": 4900,
        "payload": {"document": "personal_style_guide"},
    },
    {
        "key": "report.full_assessment",
        "kind": "report",
        "feature_key": "phase1.paid_reports",
        "title": L("Detailed assessment report", "تقرير التقييم المفصّل"),
        "description": L("Every result with measurements, scores and advice, as a PDF.", "جميع النتائج مع القياسات والدرجات والنصائح بصيغة PDF."),
        "price_minor": 9900,
        "payload": {"document": "full_assessment_report"},
    },
    {
        "key": "credits.workspace.10",
        "kind": "workspace_credits",
        "feature_key": "phase2.metered_tool_access",
        "title": L("Colour workspace: 10 clients", "مساحة تحليل الألوان: ١٠ عميلات"),
        "description": L("Use the colour-analysis workspace for 10 clients.", "استخدام مساحة تحليل الألوان لعشر عميلات."),
        "price_minor": 25000,
        "grants": [],
        "payload": {"credits": 10},
    },
    {
        "key": "physical.colour_keychain",
        "kind": "physical",
        "feature_key": "phase3.physical_products",
        "title": L("Colour swatch keychain", "ميدالية عيّنات الألوان"),
        "description": L("Your season's colours on a keychain.", "ألوان موسمك على ميدالية مفاتيح."),
        "price_minor": 7500,
        "requires_shipping": True,
        "payload": {"personalised": "seasonal_color"},
    },
    {
        "key": "physical.fabric_palette",
        "kind": "physical",
        "feature_key": "phase3.physical_products",
        "title": L("Fabric swatch palette", "لوحة عيّنات الأقمشة"),
        "description": L("Real fabric swatches in your colours.", "عيّنات أقمشة حقيقية بألوانك."),
        "price_minor": 15000,
        "requires_shipping": True,
        "payload": {"personalised": "seasonal_color"},
    },
    {
        "key": "physical.pocket_guide",
        "kind": "physical",
        "feature_key": "phase3.physical_products",
        "title": L("Pocket style guide", "دليل الأسلوب للجيب"),
        "description": L("A printed pocket guide.", "دليل مطبوع بحجم الجيب."),
        "price_minor": 6000,
        "requires_shipping": True,
        "payload": {},
    },
    {
        "key": "physical.printed_book",
        "kind": "physical",
        "feature_key": "phase3.physical_products",
        "title": L("Your printed style book", "كتاب أسلوبك المطبوع"),
        "description": L("Your personalised style guide, printed and bound.", "دليل أسلوبك الشخصي مطبوعاً ومجلّداً."),
        "price_minor": 29900,
        "requires_shipping": True,
        "payload": {"personalised": "all_results"},
    },
]
for product in PRODUCTS:
    if product["kind"] in ("guide", "report"):
        product.setdefault("grants", [product["key"]])

PLANS = [
    {
        "key": "customer.premium.monthly",
        "audience": "customer",
        "title": L("Premium, monthly", "العضوية المميّزة، شهرياً"),
        "description": L("Every guide and the detailed report.", "جميع الأدلّة والتقرير المفصّل."),
        "price_minor": 4900,
        "interval": "month",
        "grants": [PREMIUM],
    },
    {
        "key": "customer.premium.annual",
        "audience": "customer",
        "title": L("Premium, annual", "العضوية المميّزة، سنوياً"),
        "description": L("Every guide and the detailed report, for a year.", "جميع الأدلّة والتقرير المفصّل لمدة سنة."),
        "price_minor": 39900,
        "interval": "year",
        "grants": [PREMIUM],
    },
    {
        "key": "consultant.annual",
        "audience": "consultant",
        "title": L("Consultant membership, annual", "عضوية المستشارة، سنوياً"),
        "description": L("Offer services on the platform for a year.", "تقديم خدماتك عبر المنصّة لمدة سنة."),
        "price_minor": 150000,
        "interval": "year",
        "grants": ["consultant.membership"],
    },
]
