"""PDF guides and reports (rows 37, 38, 39) in the user's language.

Content comes from the assessment result profiles (their titles, summaries,
advice and palettes), so it is as DRAFT as that content is (see
assessments/content.py). Lip and blush shades below are DRAFT too.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.integrations import pdf
from app.modules.ai_analysis.service import latest_for_questionnaire
from app.modules.assessments.models import Questionnaire, ResultProfile
from app.modules.assessments.service import latest, tr
from app.modules.auth.models import User
from app.modules.commerce.models import Product

LIP_BLUSH = {  # DRAFT shades, to be replaced by the client
    "spring": ["#e8735a", "#f28c6f", "#f4a582", "#e06c75", "#f5b7a5", "#d9825b"],
    "summer": ["#c76b8e", "#d58ba3", "#b5657f", "#e0a3b6", "#a85a7a", "#cf8fa8"],
    "autumn": ["#a8452f", "#b8613f", "#c97a52", "#8e3b2c", "#d0875e", "#9c5a3c"],
    "winter": ["#a3123a", "#c2185b", "#8b0a32", "#d81b60", "#6d0f2c", "#e91e63"],
}

T = {
    "en": {
        "prepared": "Prepared for {name} on {date}",
        "footer": "Draft content for review by the consultant. Automated and self-assessed results are indicative, not an expert assessment.",
        "palette": "Your colours", "advice": "Advice", "summary": "Summary", "basis_photo": "From photo analysis",
        "basis_self": "From your answers", "confidence": "Confidence", "measurements": "Measurements",
        "lip_blush": "Lipstick and blush shades", "missing": "Not completed yet", "results": "Your results",
        "scores": "How close each result was",
    },
    "ar": {
        "prepared": "أُعدّ لـ {name} بتاريخ {date}",
        "footer": "محتوى مبدئي بانتظار مراجعة المستشارة. النتائج الآلية والذاتية إرشادية وليست تقييماً من خبيرة.",
        "palette": "ألوانك", "advice": "نصائح", "summary": "الملخّص", "basis_photo": "من تحليل الصورة",
        "basis_self": "من إجاباتك", "confidence": "درجة الثقة", "measurements": "القياسات",
        "lip_blush": "درجات أحمر الشفاه والخدود", "missing": "لم يكتمل بعد", "results": "نتائجك",
        "scores": "مدى قرب كل نتيجة",
    },
}

ADVICE_NAMES = {
    "outfits": {"en": "Outfits", "ar": "الإطلالات"}, "eyewear": {"en": "Eyewear", "ar": "النظّارات"},
    "hair": {"en": "Hair", "ar": "الشعر"}, "makeup": {"en": "Makeup", "ar": "المكياج"},
}


def _profile(db: Session, questionnaire_key: str, profile_key: str) -> tuple[Questionnaire, ResultProfile]:
    questionnaire = db.execute(select(Questionnaire).where(Questionnaire.key == questionnaire_key)).scalar_one()
    return questionnaire, next(p for p in questionnaire.profiles if p.key == profile_key)


def user_results(db: Session, user: User) -> dict[str, dict]:
    """questionnaire key -> {profile, basis, analysis} for the user's latest result of each."""
    out = {}
    for questionnaire in db.scalars(select(Questionnaire).where(Questionnaire.is_active).order_by(Questionnaire.sort_order)):
        if not questionnaire.profiles:
            continue
        assessment = latest(db, user, questionnaire)
        analysis = latest_for_questionnaire(db, user, questionnaire.key)
        profile_key, basis, source = None, None, None
        if assessment:
            profile_key, basis, source = assessment.profile_key, "self", assessment
        if analysis and (assessment is None or analysis.created_at > assessment.created_at):
            profile_key, basis, source = analysis.profile_key, "photo", analysis
        profile = profile_key and next((p for p in questionnaire.profiles if p.key == profile_key), None)
        out[questionnaire.key] = {"questionnaire": questionnaire, "profile": profile, "basis": basis, "source": source}
    return out


def _advice_sections(profile: ResultProfile, language: str, prefix: str = "") -> list[pdf.Section]:
    sections = []
    for category, items in profile.advice.items():
        name = ADVICE_NAMES.get(category, {}).get(language, category)
        sections.append(pdf.Section(heading=f"{prefix}{name}", bullets=tr(items, language) or []))
    return sections


def _result_sections(result: dict, language: str, detailed: bool) -> list[pdf.Section]:
    t = T[language]
    questionnaire, profile = result["questionnaire"], result["profile"]
    heading = f"{tr(questionnaire.title, language)}: {tr(profile.title, language)}"
    basis = t["basis_photo"] if result["basis"] == "photo" else t["basis_self"]
    sections = [pdf.Section(heading=heading, paragraphs=[basis, tr(profile.summary, language)], palette=profile.palette)]
    if detailed and result["basis"] == "photo":
        analysis = result["source"]
        names = {p.key: tr(p.title, language) for p in questionnaire.profiles}
        rows = [(t["confidence"], f"{round(analysis.confidence * 100)}%")]
        rows += [(names.get(k, k), f"{round(v * 100)}%") for k, v in sorted(analysis.scores.items(), key=lambda kv: -kv[1])]
        sections.append(pdf.Section(heading=t["scores"], rows=rows))
        measured = [(k, str(v)) for k, v in analysis.measurements.items() if not isinstance(v, (list, dict))]
        if measured:
            sections.append(pdf.Section(heading=t["measurements"], rows=measured))
    sections += _advice_sections(profile, language)
    return sections


def render(db: Session, user: User, product: Product, language: str) -> tuple[str, bytes]:
    t = T[language]
    payload = product.payload
    document = payload.get("document")
    title = tr(product.title, language)
    sections: list[pdf.Section] = []

    if document == "seasonal_palette":
        _, profile = _profile(db, "seasonal_color", payload["season"])
        sections = [pdf.Section(heading=t["palette"], paragraphs=[tr(profile.summary, language)], palette=profile.palette)]
        sections += _advice_sections(profile, language)
    elif document == "lip_blush_palette":
        _, profile = _profile(db, "seasonal_color", payload["season"])
        sections = [pdf.Section(heading=t["lip_blush"], paragraphs=[tr(profile.title, language)], palette=LIP_BLUSH[payload["season"]])]
        sections += [s for s in _advice_sections(profile, language) if s.bullets]
    elif document == "body_shape_guide":
        _, profile = _profile(db, "body_shape", payload["shape"])
        sections = [pdf.Section(heading=t["summary"], paragraphs=[tr(profile.summary, language)])]
        sections += _advice_sections(profile, language)
    elif document in ("personal_style_guide", "full_assessment_report"):
        detailed = document == "full_assessment_report"
        results = user_results(db, user)
        done = [r for r in results.values() if r["profile"]]
        if not done:
            raise AppError(409, "no_results_yet")
        for result in done:
            sections += _result_sections(result, language, detailed)
        missing = [tr(r["questionnaire"].title, language) for r in results.values() if not r["profile"]]
        if missing:
            sections.append(pdf.Section(heading=t["missing"], bullets=missing))
    else:
        raise AppError(404, "not_found")

    today = datetime.now(UTC).date().isoformat()
    data = pdf.build(title=title, subtitle=t["prepared"].format(name=user.full_name, date=pdf.ltr(today)),
                     sections=sections, language=language, footer=t["footer"])
    return f"{product.key}-{language}.pdf", data
