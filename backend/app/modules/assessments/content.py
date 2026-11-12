"""Seed content for the Phase 1 self-assessments.

STATUS: DRAFT. These questions, scoring weights, result texts and advice were
written by the development team from general styling conventions so the flow
can be built and tested end to end. They are NOT the client's methodology and
are not professionally validated. Every questionnaire is seeded with
content_status="draft"; the client (the image consultant) must review and
replace them before release. Arabic text needs native review.

Content lives in the database after seeding and is meant to be edited through
the admin panel (Assessment Management), not here.

Structure: each option carries scores {profile_key: weight}. The profile with
the highest total wins; ties go to the profile listed first.
"""


def L(en: str, ar: str) -> dict:
    return {"en": en, "ar": ar}


def LL(en: list[str], ar: list[str]) -> dict:
    return {"en": en, "ar": ar}


WARM, COOL = {"spring": 1, "autumn": 1}, {"summer": 1, "winter": 1}
LIGHT, DEEP = {"spring": 1, "summer": 1}, {"autumn": 1, "winter": 1}
BRIGHT, MUTED = {"spring": 1, "winter": 1}, {"summer": 1, "autumn": 1}

QUESTIONNAIRES = [
    {
        "key": "onboarding_quiz",
        "feature": "phase1.onboarding_quiz",
        "title": L("Style quiz", "اختبار الأسلوب"),
        "intro": L("Four quick questions so we can get to know you.", "أربعة أسئلة سريعة لنتعرّف عليك."),
        "questions": [
            ("personality", L("Which describes you best?", "أي وصف يشبهك أكثر؟"), [
                ("calm", L("Calm and composed", "هادئة ومتّزنة"), {}),
                ("warm", L("Warm and approachable", "ودودة وقريبة من الناس"), {}),
                ("bold", L("Bold and expressive", "جريئة ومعبّرة"), {}),
                ("playful", L("Playful and creative", "مرحة ومبدعة"), {}),
            ]),
            ("preference", L("What do you reach for first?", "ما الذي تختارينه أولاً؟"), [
                ("tailored", L("Tailored, polished pieces", "قطع مفصّلة وأنيقة"), {}),
                ("comfortable", L("Comfortable, easy pieces", "قطع مريحة وبسيطة"), {}),
                ("feminine", L("Soft, feminine pieces", "قطع ناعمة وأنثوية"), {}),
                ("statement", L("Statement pieces", "قطع لافتة"), {}),
            ]),
            ("challenge", L("What is your biggest dressing challenge?", "ما أكبر تحدٍّ تواجهينه عند اختيار ملابسك؟"), [
                ("fit", L("Finding clothes that fit my shape", "إيجاد ملابس تناسب شكل جسمي"), {}),
                ("colour", L("Knowing which colours suit me", "معرفة الألوان التي تناسبني"), {}),
                ("combine", L("Putting outfits together", "تنسيق الإطلالات"), {}),
                ("occasion", L("Dressing for the occasion", "اختيار ما يناسب المناسبة"), {}),
            ]),
            ("occasion", L("What do you dress for most often?", "لأي مناسبة ترتدين ملابسك غالباً؟"), [
                ("work", L("Work", "العمل"), {}),
                ("social", L("Social events", "المناسبات الاجتماعية"), {}),
                ("family", L("Family and everyday life", "العائلة والحياة اليومية"), {}),
                ("formal", L("Formal occasions", "المناسبات الرسمية"), {}),
            ]),
        ],
        "profiles": [],
    },
    {
        "key": "style",
        "feature": "phase1.style_assessment",
        "title": L("Personal style assessment", "تقييم الأسلوب الشخصي"),
        "intro": L(
            "Five questions on line, shape, colour, texture and pattern.",
            "خمسة أسئلة عن الخطوط والشكل واللون والملمس والنقوش.",
        ),
        "questions": [
            ("line", L("Which lines do you prefer in clothes?", "أي الخطوط تفضّلين في الملابس؟"), [
                ("straight", L("Clean, straight lines", "خطوط مستقيمة ونظيفة"), {"classic": 1}),
                ("relaxed", L("Relaxed, unstructured lines", "خطوط مريحة وغير محدّدة"), {"natural": 1}),
                ("curved", L("Soft, curved lines", "خطوط ناعمة ومنحنية"), {"romantic": 1}),
                ("sharp", L("Sharp, angular lines", "خطوط حادّة وزاوية"), {"dramatic": 1}),
            ]),
            ("shape", L("Which silhouette feels most like you?", "أي قصّة تشبهك أكثر؟"), [
                ("tailored", L("Tailored and balanced", "مفصّلة ومتوازنة"), {"classic": 1}),
                ("loose", L("Loose and easy", "واسعة ومريحة"), {"natural": 1}),
                ("fitted", L("Fitted at the waist and flowing", "محدّدة عند الخصر ومنسدلة"), {"romantic": 1}),
                ("oversized", L("Structured and oversized", "محدّدة وكبيرة الحجم"), {"dramatic": 1}),
            ]),
            ("colour", L("Which colours do you wear most?", "أي الألوان ترتدينها أكثر؟"), [
                ("neutrals", L("Navy, beige and other neutrals", "الكحلي والبيج والألوان المحايدة"), {"classic": 1}),
                ("earthy", L("Earthy tones", "الألوان الترابية"), {"natural": 1}),
                ("pastels", L("Pastels and soft shades", "ألوان الباستيل والدرجات الهادئة"), {"romantic": 1}),
                ("contrast", L("Black, white and strong colours", "الأسود والأبيض والألوان القوية"), {"dramatic": 1}),
            ]),
            ("texture", L("Which fabrics do you love?", "أي الأقمشة تحبّين؟"), [
                ("smooth", L("Smooth, fine fabrics", "أقمشة ناعمة ورفيعة"), {"classic": 1}),
                ("textured", L("Linen, knits and natural textures", "الكتّان والتريكو والملامس الطبيعية"), {"natural": 1}),
                ("delicate", L("Silk, lace and chiffon", "الحرير والدانتيل والشيفون"), {"romantic": 1}),
                ("glossy", L("Leather, satin and bold finishes", "الجلد والساتان والملامس الجريئة"), {"dramatic": 1}),
            ]),
            ("pattern", L("Which patterns do you choose?", "أي النقوش تختارين؟"), [
                ("subtle", L("Plain or subtle stripes", "سادة أو خطوط خفيفة"), {"classic": 1}),
                ("organic", L("Checks and organic prints", "المربّعات والنقوش الطبيعية"), {"natural": 1}),
                ("floral", L("Florals", "نقوش الأزهار"), {"romantic": 1}),
                ("graphic", L("Large, graphic prints", "نقوش كبيرة وهندسية"), {"dramatic": 1}),
            ]),
        ],
        "profiles": [
            ("classic", L("Classic", "كلاسيكي"),
             L("You favour timeless, polished pieces in balanced proportions.", "تميلين إلى القطع الأنيقة الخالدة ذات النِّسب المتوازنة."),
             {"outfits": LL(
                 ["Build around tailored blazers and straight-leg trousers.", "Keep to two or three neutral colours per outfit.", "Choose fine fabrics with a smooth finish."],
                 ["اعتمدي على السترات المفصّلة والبناطيل المستقيمة.", "اكتفي بلونين أو ثلاثة ألوان محايدة في الإطلالة.", "اختاري أقمشة رفيعة ذات ملمس ناعم."])}),
            ("natural", L("Natural", "طبيعي"),
             L("You are most at ease in relaxed shapes and natural textures.", "ترتاحين في القصّات المريحة والملامس الطبيعية."),
             {"outfits": LL(
                 ["Layer relaxed knits over wide-leg trousers.", "Pick linen, cotton and other natural fabrics.", "Earthy tones will feel most like you."],
                 ["نسّقي التريكو المريح مع البناطيل الواسعة.", "اختاري الكتّان والقطن والأقمشة الطبيعية.", "الألوان الترابية هي الأقرب إليك."])}),
            ("romantic", L("Romantic", "رومانسي"),
             L("You are drawn to soft lines, flowing fabrics and delicate detail.", "تنجذبين إلى الخطوط الناعمة والأقمشة المنسدلة والتفاصيل الرقيقة."),
             {"outfits": LL(
                 ["Choose dresses and tops that define the waist.", "Look for silk, chiffon and lace.", "Soft shades and florals suit your style."],
                 ["اختاري الفساتين والبلوزات التي تحدّد الخصر.", "ابحثي عن الحرير والشيفون والدانتيل.", "الدرجات الهادئة ونقوش الأزهار تناسب أسلوبك."])}),
            ("dramatic", L("Dramatic", "درامي"),
             L("You like strong shapes, contrast and pieces that make a statement.", "تحبّين القصّات القوية والتباين والقطع اللافتة."),
             {"outfits": LL(
                 ["Anchor outfits with one strong statement piece.", "Use high contrast, such as black with white.", "Structured shoulders and sharp tailoring work well."],
                 ["اجعلي في كل إطلالة قطعة لافتة واحدة.", "استخدمي التباين العالي مثل الأسود مع الأبيض.", "الأكتاف المحدّدة والتفصيل الحادّ يناسبانك."])}),
        ],
    },
    {
        "key": "body_shape",
        "feature": "phase1.body_shape",
        "title": L("Body shape", "شكل الجسم"),
        "intro": L(
            "Answer from how your body looks in fitted clothing. No photo is needed.",
            "أجيبي بحسب شكل جسمك في الملابس الضيّقة. لا حاجة إلى صورة.",
        ),
        "questions": [
            ("shoulders_hips", L("How do your shoulders compare with your hips?", "كيف تقارنين عرض كتفيك بعرض وركيك؟"), [
                ("shoulders_wider", L("Shoulders are wider", "الكتفان أعرض"), {"inverted_triangle": 2}),
                ("hips_wider", L("Hips are wider", "الوركان أعرض"), {"pear": 2}),
                ("equal", L("About the same", "متساويان تقريباً"), {"hourglass": 1, "rectangle": 1, "apple": 1}),
            ]),
            ("waist", L("How defined is your waist?", "ما مدى تحديد خصرك؟"), [
                ("defined", L("Clearly defined", "محدّد بوضوح"), {"hourglass": 2, "pear": 1}),
                ("slight", L("Slightly defined", "محدّد قليلاً"), {"rectangle": 1, "inverted_triangle": 1}),
                ("undefined", L("Not defined", "غير محدّد"), {"apple": 2, "rectangle": 1}),
            ]),
            ("weight", L("Where do you tend to carry weight?", "أين يتركّز الوزن عندك غالباً؟"), [
                ("lower", L("Hips and thighs", "الوركان والفخذان"), {"pear": 1}),
                ("middle", L("Around the middle", "منطقة الوسط"), {"apple": 2}),
                ("even", L("Evenly", "بشكل متساوٍ"), {"hourglass": 1, "rectangle": 1}),
                ("upper", L("Upper body", "الجزء العلوي"), {"inverted_triangle": 1}),
            ]),
        ],
        "profiles": [
            ("hourglass", L("Hourglass", "الساعة الرملية"),
             L("Shoulders and hips are balanced with a defined waist.", "الكتفان والوركان متوازنان مع خصر محدّد."),
             {"outfits": LL(
                 ["Enhance: define the waist with belts and wrap styles.", "Avoid: boxy cuts that hide your waist."],
                 ["أبرزي: حدّدي الخصر بالأحزمة والقصّات الملتفّة.", "تجنّبي: القصّات المربّعة التي تخفي الخصر."])}),
            ("pear", L("Pear", "الكمّثرى"),
             L("Hips are wider than shoulders, with a defined waist.", "الوركان أعرض من الكتفين مع خصر محدّد."),
             {"outfits": LL(
                 ["Enhance: draw the eye up with detail at the shoulders and neckline.", "Avoid: heavy detail or light colours at the hips."],
                 ["أبرزي: اجذبي النظر إلى الأعلى بتفاصيل عند الكتفين وفتحة العنق.", "تجنّبي: التفاصيل الكثيرة أو الألوان الفاتحة عند الوركين."])}),
            ("inverted_triangle", L("Inverted triangle", "المثلّث المقلوب"),
             L("Shoulders are wider than hips.", "الكتفان أعرض من الوركين."),
             {"outfits": LL(
                 ["Enhance: add volume below the waist with A-line and wide-leg shapes.", "Avoid: shoulder pads and wide necklines."],
                 ["أبرزي: أضيفي حجماً أسفل الخصر بقصّات واسعة من الأسفل.", "تجنّبي: حشوات الأكتاف وفتحات العنق العريضة."])}),
            ("rectangle", L("Rectangle", "المستطيل"),
             L("Shoulders, waist and hips are close in width.", "الكتفان والخصر والوركان متقاربة في العرض."),
             {"outfits": LL(
                 ["Enhance: create shape with layers, peplums and belts.", "Avoid: straight, shapeless cuts from shoulder to hem."],
                 ["أبرزي: اصنعي انحناءات بالطبقات والأحزمة.", "تجنّبي: القصّات المستقيمة من الكتف إلى الأسفل."])}),
            ("apple", L("Apple", "التفّاحة"),
             L("Weight sits around the middle, with slimmer legs.", "يتركّز الوزن في الوسط مع ساقين أنحف."),
             {"outfits": LL(
                 ["Enhance: choose V-necks and fabrics that skim the middle.", "Avoid: clingy fabrics and belts at the widest point."],
                 ["أبرزي: اختاري فتحة العنق على شكل V والأقمشة المنسدلة عند الوسط.", "تجنّبي: الأقمشة اللاصقة والأحزمة عند أعرض نقطة."])}),
        ],
    },
    {
        "key": "face_shape",
        "feature": "phase1.face_shape",
        "title": L("Face shape", "شكل الوجه"),
        "intro": L(
            "Pull your hair back and look straight into a mirror. Photo-based analysis will be added later.",
            "ارفعي شعرك للخلف وانظري إلى المرآة مباشرة. سيُضاف التحليل بالصور لاحقاً.",
        ),
        "questions": [
            ("length", L("How long is your face compared with its width?", "ما طول وجهك مقارنة بعرضه؟"), [
                ("equal", L("About as long as it is wide", "الطول والعرض متقاربان"), {"round": 1, "square": 1}),
                ("longer", L("Slightly longer than wide", "أطول قليلاً من العرض"), {"oval": 2, "heart": 1}),
                ("much_longer", L("Much longer than wide", "أطول بكثير من العرض"), {"oblong": 2}),
            ]),
            ("widest", L("Which part of your face is widest?", "ما أعرض جزء في وجهك؟"), [
                ("forehead", L("Forehead", "الجبهة"), {"heart": 2}),
                ("cheekbones", L("Cheekbones", "عظام الخدّين"), {"oval": 1, "round": 1}),
                ("jaw", L("Jaw", "الفكّ"), {"square": 2}),
                ("similar", L("All about the same", "متساوية تقريباً"), {"square": 1, "oblong": 1}),
            ]),
            ("jaw", L("How would you describe your jawline?", "كيف تصفين خطّ الفكّ؟"), [
                ("soft", L("Soft and rounded", "ناعم ومستدير"), {"round": 2, "oval": 1}),
                ("angular", L("Strong and angular", "قوي وزاويّ"), {"square": 2, "oblong": 1}),
                ("pointed", L("Narrow with a pointed chin", "ضيّق مع ذقن مدبّب"), {"heart": 2}),
            ]),
        ],
        "profiles": [
            ("oval", L("Oval", "بيضاوي"),
             L("Balanced proportions, slightly longer than wide.", "نِسب متوازنة وأطول قليلاً من العرض."),
             {"eyewear": LL(["Most frame shapes suit you.", "Keep frames as wide as the widest part of your face."],
                            ["معظم أشكال الإطارات تناسبك.", "اختاري إطاراً بعرض أعرض جزء في وجهك."]),
              "hair": LL(["Most lengths and partings work.", "Avoid heavy fringes that shorten the face."],
                         ["معظم الأطوال وأنواع الفَرق تناسبك.", "تجنّبي الغرّة الكثيفة التي تقصّر الوجه."])}),
            ("round", L("Round", "مستدير"),
             L("Length and width are similar, with soft curves.", "الطول والعرض متقاربان مع انحناءات ناعمة."),
             {"eyewear": LL(["Choose rectangular or square frames to add definition.", "Avoid small round frames."],
                            ["اختاري الإطارات المستطيلة أو المربّعة لإضافة تحديد.", "تجنّبي الإطارات المستديرة الصغيرة."]),
              "hair": LL(["Add height at the crown and length below the chin.", "Long layers elongate the face."],
                         ["أضيفي ارتفاعاً عند أعلى الرأس وطولاً تحت الذقن.", "الطبقات الطويلة تُطيل الوجه."])}),
            ("square", L("Square", "مربّع"),
             L("A strong jaw with similar width at forehead and jaw.", "فكّ قوي مع عرض متقارب بين الجبهة والفكّ."),
             {"eyewear": LL(["Choose round or oval frames to soften angles.", "Avoid sharp, boxy frames."],
                            ["اختاري الإطارات المستديرة أو البيضاوية لتنعيم الزوايا.", "تجنّبي الإطارات الحادّة والمربّعة."]),
              "hair": LL(["Soft waves and side partings soften the jaw.", "Avoid blunt cuts that end at the jawline."],
                         ["التموّجات الناعمة والفَرق الجانبي ينعّمان الفكّ.", "تجنّبي القصّات المستقيمة التي تنتهي عند الفكّ."])}),
            ("heart", L("Heart", "قلب"),
             L("A wider forehead narrowing to the chin.", "جبهة أعرض تضيق نحو الذقن."),
             {"eyewear": LL(["Choose frames that are wider at the bottom, or rimless styles.", "Avoid top-heavy frames."],
                            ["اختاري إطارات أعرض من الأسفل أو بلا إطار.", "تجنّبي الإطارات الثقيلة من الأعلى."]),
              "hair": LL(["Add volume around the jaw with chin-length layers.", "A side-swept fringe balances the forehead."],
                         ["أضيفي حجماً حول الفكّ بطبقات بطول الذقن.", "الغرّة الجانبية توازن الجبهة."])}),
            ("oblong", L("Oblong", "مستطيل"),
             L("Noticeably longer than wide.", "أطول من العرض بوضوح."),
             {"eyewear": LL(["Choose deep frames with decorative temples to add width.", "Avoid narrow, small frames."],
                            ["اختاري إطارات عميقة بأذرع مزخرفة لإضافة عرض.", "تجنّبي الإطارات الضيّقة الصغيرة."]),
              "hair": LL(["Add width at the sides with waves or curls.", "A fringe shortens the face."],
                         ["أضيفي عرضاً على الجانبين بالتموّجات.", "الغرّة تقصّر الوجه."])}),
        ],
    },
    {
        "key": "seasonal_color",
        "feature": "phase1.seasonal_color",
        "title": L("Seasonal colour palette", "لوحة الألوان الموسمية"),
        "intro": L(
            "An indicative result from your own observations in daylight. It is not an expert colour analysis.",
            "نتيجة استرشادية من ملاحظاتك في ضوء النهار، وليست تحليل ألوان من خبيرة.",
        ),
        "questions": [
            ("jewellery", L("Which jewellery flatters your skin more?", "أي المجوهرات تناسب بشرتك أكثر؟"), [
                ("gold", L("Gold", "الذهبي"), WARM),
                ("silver", L("Silver", "الفضّي"), COOL),
                ("both", L("Both equally", "كلاهما بالتساوي"), {"spring": 0.5, "summer": 0.5, "autumn": 0.5, "winter": 0.5}),
            ]),
            ("veins", L("What colour are the veins on your inner wrist?", "ما لون العروق في باطن معصمك؟"), [
                ("green", L("Greenish", "مائلة إلى الأخضر"), WARM),
                ("blue", L("Blue or purple", "زرقاء أو بنفسجية"), COOL),
                ("mixed", L("A mix of both", "مزيج من الاثنين"), {"spring": 0.5, "summer": 0.5, "autumn": 0.5, "winter": 0.5}),
            ]),
            ("depth", L("How would you describe your natural hair and eye colouring?", "كيف تصفين لون شعرك وعينيك الطبيعي؟"), [
                ("light", L("Light", "فاتح"), LIGHT),
                ("deep", L("Deep", "داكن"), DEEP),
            ]),
            ("clarity", L("Which colours make you look your best?", "أي الألوان تجعلك في أفضل إطلالة؟"), [
                ("bright", L("Clear, bright colours", "الألوان الصافية والزاهية"), BRIGHT),
                ("muted", L("Soft, muted colours", "الألوان الهادئة والمطفأة"), MUTED),
            ]),
        ],
        "profiles": [
            ("spring", L("Spring (indicative)", "الربيع (استرشادي)"),
             L("Warm, light and clear colouring.", "ألوان دافئة وفاتحة وصافية."),
             {"outfits": LL(["Wear warm, clear colours near your face."], ["ارتدي الألوان الدافئة الصافية قرب وجهك."])},
             ["#F7C59F", "#FF9A76", "#FFD166", "#8FD694", "#5BC0BE", "#F2E8CF"]),
            ("summer", L("Summer (indicative)", "الصيف (استرشادي)"),
             L("Cool, light and soft colouring.", "ألوان باردة وفاتحة وهادئة."),
             {"outfits": LL(["Wear cool, soft colours near your face."], ["ارتدي الألوان الباردة الهادئة قرب وجهك."])},
             ["#B8C0DC", "#D8A7B1", "#9AB8C2", "#C9B6D4", "#8E9AAF", "#EFE9F4"]),
            ("autumn", L("Autumn (indicative)", "الخريف (استرشادي)"),
             L("Warm, deep and muted colouring.", "ألوان دافئة وداكنة ومطفأة."),
             {"outfits": LL(["Wear warm, earthy colours near your face."], ["ارتدي الألوان الدافئة الترابية قرب وجهك."])},
             ["#A0522D", "#C08A3E", "#6B7A3A", "#8B3A3A", "#D9A566", "#4E5B31"]),
            ("winter", L("Winter (indicative)", "الشتاء (استرشادي)"),
             L("Cool, deep and clear colouring.", "ألوان باردة وداكنة وصافية."),
             {"outfits": LL(["Wear cool, high-contrast colours near your face."], ["ارتدي الألوان الباردة عالية التباين قرب وجهك."])},
             ["#0B132B", "#C1121F", "#1D4E89", "#5F0F40", "#FFFFFF", "#0A8754"]),
        ],
    },
]

# Recommendation category -> (feature that gates it, questionnaires whose results feed it)
RECOMMENDATION_CATEGORIES = {
    "outfits": ("phase1.outfit_recommendations", ["style", "body_shape", "seasonal_color"]),
    "eyewear": ("phase1.eyewear", ["face_shape"]),
    "hair": ("phase1.hair_preview", ["face_shape"]),
}
