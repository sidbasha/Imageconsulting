"""Seed expert report templates (rows 24, 25, 56).

STATUS: DRAFT. Every template shares the standard frame the Feature List asks
for: a suitability decision, a technical explanation, and recommendations,
plus fields specific to the service. Wording and options are placeholders for
the client's own report format; edit them in the admin (row 56).
"""


def L(en, ar):
    return {"en": en, "ar": ar}


SUITABILITY = {"key": "suitability", "title": L("Suitability", "مدى الملاءمة"), "type": "decision",
               "options": ["suitable", "adjust", "not_suitable"], "required": True}
EXPLANATION = {"key": "explanation", "title": L("Explanation", "الشرح"), "type": "text", "required": True}
RECOMMENDATIONS = {"key": "recommendations", "title": L("Recommendations", "التوصيات"), "type": "list", "required": True}

TEMPLATES = [
    {"key": "consultation.standard", "service_kind": "consultation", "title": L("Consultation report", "تقرير الاستشارة"),
     "sections": [SUITABILITY, EXPLANATION, RECOMMENDATIONS]},
    {"key": "occasion_audit.standard", "service_kind": "occasion_audit", "title": L("Occasion style audit", "تقييم الإطلالة للمناسبة"),
     "sections": [SUITABILITY, EXPLANATION, RECOMMENDATIONS,
                  {"key": "alternatives", "title": L("Alternatives to consider", "بدائل مقترحة"), "type": "list", "required": False}]},
    {"key": "wardrobe_audit.standard", "service_kind": "wardrobe_audit", "title": L("Wardrobe audit", "تقييم خزانة الملابس"),
     "sections": [SUITABILITY, EXPLANATION, RECOMMENDATIONS,
                  {"key": "keep", "title": L("Keep", "احتفظي بها"), "type": "list", "required": False},
                  {"key": "restyle", "title": L("Restyle", "أعيدي تنسيقها"), "type": "list", "required": False},
                  {"key": "remove", "title": L("Remove", "استغني عنها"), "type": "list", "required": False},
                  {"key": "add", "title": L("Add", "أضيفي"), "type": "list", "required": False}]},
    {"key": "makeup_audit.standard", "service_kind": "makeup_audit", "title": L("Makeup audit", "تقييم المكياج"),
     "sections": [SUITABILITY, EXPLANATION, RECOMMENDATIONS]},
    {"key": "expert_color.standard", "service_kind": "expert_color", "title": L("Expert colour analysis", "تحليل الألوان من خبيرة"),
     "sections": [
         {"key": "season", "title": L("Season", "الموسم"), "type": "choice", "options": ["spring", "summer", "autumn", "winter"], "required": True},
         {"key": "temperature", "title": L("Temperature", "درجة الدفء"), "type": "choice", "options": ["warm", "cool", "neutral"], "required": True},
         {"key": "contrast", "title": L("Contrast", "التباين"), "type": "choice", "options": ["low", "medium", "high"], "required": True},
         {"key": "palette", "title": L("Your palette", "لوحة ألوانك"), "type": "palette", "required": True},
         {"key": "makeup", "title": L("Makeup", "المكياج"), "type": "list", "required": True},
         {"key": "hair", "title": L("Hair colour", "لون الشعر"), "type": "list", "required": True},
         {"key": "clothing", "title": L("Clothing", "الملابس"), "type": "list", "required": True},
         {"key": "metals", "title": L("Accessory metals", "معادن الإكسسوارات"), "type": "choice", "options": ["gold", "silver", "rose_gold", "mixed"], "required": True},
         SUITABILITY, EXPLANATION, RECOMMENDATIONS,
     ]},
    {"key": "personal_shopper_day.standard", "service_kind": "personal_shopper_day", "title": L("Shopping day summary", "ملخّص يوم التسوّق"),
     "sections": [SUITABILITY, EXPLANATION, RECOMMENDATIONS]},
]

OPTION_LABELS = {
    "suitable": L("Suitable", "مناسب"), "adjust": L("Suitable with changes", "مناسب مع تعديلات"),
    "not_suitable": L("Not suitable", "غير مناسب"), "spring": L("Spring", "الربيع"), "summer": L("Summer", "الصيف"),
    "autumn": L("Autumn", "الخريف"), "winter": L("Winter", "الشتاء"), "warm": L("Warm", "دافئ"), "cool": L("Cool", "بارد"),
    "neutral": L("Neutral", "محايد"), "low": L("Low", "منخفض"), "medium": L("Medium", "متوسّط"), "high": L("High", "مرتفع"),
    "gold": L("Gold", "الذهبي"), "silver": L("Silver", "الفضّي"), "rose_gold": L("Rose gold", "الذهبي الوردي"), "mixed": L("Mixed", "مزيج"),
}
