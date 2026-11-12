"""Builds docs/Requirements_Traceability_Matrix.xlsx.

    python docs/build_rtm.py <path to the client's Feature List v1.0 .xlsx>

Columns B-G of the client's workbook are copied verbatim, so the original
wording and phase labels cannot drift. Feature keys, release phase and
dependencies come from the same catalog the backend seeds from.
"""

import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.modules.phase_management import catalog  # noqa: E402

A = "/api/v1"
# S.No -> (MoM reference, planned API, database entities, screens, acceptance criteria)
MAP = {
    1: ("p3 Safety; Decisions", f"{A}/identity/uae-pass/*, {A}/identity/documents", "identity_verifications, users", "Verify identity; ID upload; Admin: verification queue", "User completes UAE Pass sign-in or uploads a national ID; unverified users cannot reach assessments; ID files are private and retention-limited"),
    2: ("p3 Safety; Decisions; Open items", f"{A}/identity/eligibility", "identity_verifications, user_profiles", "Eligibility result; Not eligible", "Age and women-only rules are evaluated from verified data; method per open decision 65; teenagers handled per decision 63"),
    3: ("p3 Launch; Decisions", f"{A}/identity/eligibility, country config", "countries, user_profiles", "Region not supported", "Only UAE-verified residents can register at launch; allowed countries are configuration, not code"),
    4: ("p1 Consulting process", f"{A}/assessments/onboarding", "questionnaires, questions, options, assessment_answers", "Onboarding quiz (image choices), EN and AR", "Quiz captures personality, style preferences, dressing challenges, occasion and role with image options; answers are saved and editable"),
    5: ("p1 Five elements of style", f"{A}/assessments/style", "assessments, assessment_answers, assessment_results", "Style assessment; Style result", "Result covers line, shape, colour, texture and pattern; rules are configurable by admin"),
    6: ("p2 Free entry-level assessment", f"{A}/assessment-images", "assessment_images, consents", "Photo guide; Capture/upload; Retake prompt", "Consent recorded before upload; format, size and quality validated; poor photos are rejected with a reason; images stored privately"),
    7: ("p2 Product range", f"{A}/analysis/face-shape", "ai_analysis_jobs, assessment_results, ai_models", "Face shape result with confidence", "Returns a face shape with confidence and an uncertainty message; labelled indicative; evaluated against expert labels before release"),
    8: ("p1 Image audit", f"{A}/analysis/body-shape", "ai_analysis_jobs, assessment_results", "Body shape (photo or measurements); Enhance/avoid advice", "Works from photo or questionnaire; shows what to enhance or avoid; low confidence falls back to questionnaire"),
    9: ("p2 Accuracy of AI-based analysis", f"{A}/analysis/seasonal-color", "ai_analysis_jobs, assessment_results, palettes", "Indicative palette", "Palette is labelled indicative and distinct from expert-verified analysis; evaluated across skin tones and lighting"),
    10: ("p2 Product range", f"{A}/recommendations/outfits", "style_rules, recommendations", "Outfit recommendations", "Suggestions follow assessment results and stated preferences; each links to its reason"),
    11: ("Not in MoM", f"{A}/previews/outfit", "ai_analysis_jobs, preview_images", "Outfit preview", "Definition pending (generated try-on vs outfit board); model licence must allow commercial use"),
    12: ("p2 Product range", f"{A}/previews/hair, {A}/recommendations/hair", "ai_analysis_jobs, style_rules, preview_images", "Hair recommendations; Hair preview", "Recommendations follow face shape; colour preview on the user photo; cut/style preview subject to licensed model"),
    13: ("p2 Product range; p5 Open items", f"{A}/recommendations/eyewear", "style_rules, recommendations", "Eyewear recommendations", "Frame shapes follow face shape; Phase 1 inclusion is an open item in the MoM"),
    14: ("p5 Open items", f"{A}/previews/makeup", "ai_analysis_jobs, preview_images", "Brow and lip preview", "Simulated brow and lip colour on the user photo, labelled as a preview; phase is an open item in the MoM"),
    15: ("p3 Stylist verification", f"{A}/stylists/applications", "stylists, users", "Stylist sign-up; Application status", "A consultant can apply; application has a visible status; not listed until approved"),
    16: ("p3 Stylist verification; Action items", f"{A}/stylists/applications/{{id}}/documents", "stylist_documents", "Credential upload checklist", "Collects certification, invoices, testimonials, referrals and UAE trade licence; checklist is admin-configurable"),
    17: ("p3 Stylist verification; Decisions", f"{A}/admin/stylists/{{id}}/review", "stylists, stylist_documents, audit_logs", "Admin: stylist review", "Manual approve/reject with reason; only approved UAE-licensed businesses can offer services; decisions audited"),
    18: ("p2 Revenue model", f"{A}/stylists, {A}/stylists/{{id}}", "stylists, stylist_services, testimonials, availability_slots", "Stylist list; Filters; Stylist profile", "Shows services, testimonials and availability for approved stylists only; ranking per open decision 66"),
    19: ("p1 Live session about one hour", f"{A}/bookings", "bookings, availability_slots, payments", "Pick slot; Checkout; My bookings", "Customer books and pays for a slot (30-minute format supported); no double booking; cancel and reschedule rules applied"),
    20: ("p3 Decisions", f"{A}/consultations", "consultations, conversations", "Consultation room; Stylist: consultations", "Customer and stylist consult inside the app; modality (chat/voice/video) pending clarification"),
    21: ("p2 Product range", f"{A}/audits/occasion", "audits, audit_images, reports", "Occasion audit request; Audit report", "Customer submits outfit photos, occasion, role and personality; stylist returns a standard report"),
    22: ("p2 Product range", f"{A}/audits/wardrobe", "audits, audit_images, reports", "Wardrobe upload; Keep/remove/add report", "Stylist marks items keep, remove or add and suggests restyling; delivered as a report"),
    23: ("p2 Product range", f"{A}/audits/makeup", "audits, audit_images, reports", "Makeup audit request; Report", "Blocked until seasonal colour analysis exists; product photos assessed against personal colouring"),
    24: ("p2 Paid levels", f"{A}/consultations/{{id}}/color-analysis", "assessment_results, reports", "Stylist: colour analysis form; Customer: expert result", "Records temperature, contrast, makeup, hair, clothing and metals; shown as expert-verified, replacing the indicative label"),
    25: ("p2 Product range", f"{A}/reports, {A}/admin/report-templates", "reports, report_templates", "Report viewer; PDF (EN/AR)", "All expert reports use the common template with suitability decisions, explanations and recommendations; PDF in both languages"),
    26: ("p2 Product range", f"{A}/analysis/product-recognition", "ai_analysis_jobs, products", "Product photo result", "Identifies product from a photo or reports it cannot; never guesses silently"),
    27: ("p2 Revenue model", f"{A}/color-workspace/sessions", "workspace_sessions, assessment_images", "Stylist: colour workspace", "Only approved stylists can open it; uses the customer's consented photos"),
    28: ("p2 Revenue model", f"{A}/color-workspace/sessions/{{id}}/drapes", "workspace_sessions, palettes", "Stylist: draping view", "Drape colours are placed around the customer photo and can be compared side by side"),
    29: ("p2 Revenue model; p5 Open items", f"{A}/color-workspace/usage", "usage_charges, payments", "Stylist: usage and charges", "Each analysis is charged per use at a configurable price; usage is itemised"),
    30: ("p3 Decisions", f"{A}/conversations, {A}/messages", "conversations, messages", "Chat list; Chat", "Customer and stylist can message only inside the app; history retained"),
    31: ("p3 Safety; Action items", "messaging service (internal)", "message_flags", "Admin: flagged messages", "Detects phone numbers, emails, bank details and contact links, including Arabic digits and spaced-out forms"),
    32: ("p3 Safety", f"{A}/messages (blocked response)", "messages, message_flags", "Chat: blocked-message warning", "A flagged message is not delivered and the sender sees a warning in their language"),
    33: ("p3 Decisions; Action items", f"{A}/admin/moderation", "violations, account_actions", "Admin: violations; Suspension notice", "Violations counted per user; ban applied at the agreed threshold (to be confirmed); actions audited"),
    34: ("p2 Product range", f"{A}/entitlements", "entitlements, plans", "Paywall; Unlock prompts", "Free tier shows introductory results; paid items are locked until entitled; boundaries per open decision 62"),
    35: ("p2 Revenue model; Decisions", f"{A}/subscriptions", "plans, subscriptions, payments", "Plans; Checkout; Manage subscription", "Annual plan with auto-renewal; renewal, cancellation and failed-payment states handled; structure per open decision 61"),
    36: ("p2 Shopping links", f"{A}/recommendations/retail", "retailer_links, recommendations", "Shop the look (external links)", "Recommended items open on the retailer's site or app; links are admin-managed"),
    37: ("p2 Paid levels", f"{A}/reports/{{id}}/purchase", "reports, payments, entitlements", "Report preview; Purchase; Download", "A detailed report or full style guide can be bought once and re-downloaded"),
    38: ("p2 Digital products first", f"{A}/digital-products", "digital_products, entitlements", "Guide catalog; Guide detail", "Lists palettes, lipstick/blush palettes, body-shape guides and style guides with price or free status"),
    39: ("p2 Low price points", f"{A}/digital-products?free=true", "digital_products", "Free resources", "Selected guides are available without payment; selection is admin-managed"),
    40: ("p2 Revenue model; Decisions", f"{A}/stylists/subscription", "plans, subscriptions, payments", "Stylist: membership", "Stylist pays a yearly fee; lapsed membership removes the listing"),
    41: ("p3 Decisions", f"{A}/payments", "payments, bookings", "Checkout; Receipts", "Consultation and service payments are collected in the app; no off-platform payment path"),
    42: ("p2 Revenue model", f"{A}/stylists/promotions", "promotions, payments", "Stylist: promote my profile", "Stylist can buy featured placement; featured items are labelled"),
    43: ("p2 Gamification; Action items", f"{A}/rewards/balance", "reward_rules, reward_ledger", "Points balance; Activity", "Points are awarded by configurable rules and recorded in a ledger"),
    44: ("p2 Gamification", f"{A}/rewards/redeem", "reward_ledger, bookings", "Redeem points", "Points redeem for a free consultation or styling session; balance cannot go negative"),
    45: ("p2 Revenue model", f"{A}/testimonials", "testimonials, consultations", "Leave testimonial; Profile testimonials", "Only customers with a completed consultation can post; testimonials feed stylist visibility per decision 66"),
    46: ("p3 Launch; p5 Open items", f"{A}/bookings (type=in_person)", "bookings, stylist_services", "Book a shopper for a day", "Customer hires a stylist or shopper for a day in a chosen city; phase is an open item in the MoM"),
    47: ("Not in MoM", f"{A}/stylists?near=", "stylists (location), consents", "Nearby stylists", "Shows nearby consultants only after location consent"),
    48: ("p2 Physical products later", f"{A}/physical-products, {A}/orders", "physical_products, orders, shipments", "Shop; Cart; Order tracking", "Sells keychains, fabric palettes, pocket guides and printed books with delivery"),
    49: ("p2 Revenue model", f"{A}/admin/campaigns", "brands, campaigns", "Admin: campaigns; In-app placements", "A brand can buy placement; placements are labelled as promoted"),
    50: ("p2 Geo-fenced promotions", f"{A}/promotions/nearby", "campaigns (area, radius), consents", "Nearby offers", "Promotions target an area or radius; shown only with location consent"),
    51: ("Not in MoM", f"{A}/vouchers", "vouchers, voucher_redemptions", "My vouchers", "Vouchers for partner services can be issued and redeemed once"),
    52: ("p3 Launch", "country, currency, language, timezone, payment config", "countries, languages, currencies", "Country and language settings", "A new country is added by configuration: language, currency, timezone and payment settings"),
    53: ("Not in MoM (inferred)", f"{A}/admin/users, {A}/admin/stylists", "users, stylists, audit_logs", "Admin: users; stylist approvals", "Admin approves or rejects eligibility and stylist applications with a reason"),
    54: ("Not in MoM (inferred)", f"{A}/admin/stylists/{{id}}/documents", "stylist_documents", "Admin: credential review", "Each submitted credential can be viewed, accepted or rejected"),
    55: ("Not in MoM (inferred)", f"{A}/admin/plans", "plans, entitlements", "Admin: plans and pricing", "Plans, prices and entitlements are edited without a deploy; no price is hardcoded"),
    56: ("Not in MoM (inferred)", f"{A}/admin/report-templates", "report_templates", "Admin: report templates", "Templates are versioned; reports record the template version used"),
    57: ("Not in MoM (inferred)", f"{A}/admin/digital-products", "digital_products", "Admin: guides and palettes", "Guides and palettes are created, priced, translated and published"),
    58: ("Not in MoM (inferred)", f"{A}/admin/moderation", "message_flags, violations, account_actions", "Admin: moderation cases", "Flagged messages are reviewed; actions are recorded and reversible"),
    59: ("Not in MoM (inferred)", f"{A}/admin/reward-rules", "reward_rules", "Admin: reward rules", "Accrual and redemption rules are configurable"),
    60: ("Not in MoM (inferred)", f"{A}/admin/placements", "promotions, campaigns", "Admin: placements", "Paid placements are scheduled, priced and reported"),
}
DECISION = "Open decision. Client answer required before the dependent features are finalised."
ADMIN_PHASE = {53: "With 1-2 (P1) and 15-17 (P2)", 54: "With 16-17 (P2)", 55: "With 34-35 (P1)", 56: "With 25 (P2)",
               57: "With 38-39 (P1)", 58: "With 31-33 (P2)", 59: "With 43 (P1) and 44 (P2)", 60: "With 42 (P2) and 49 (P3)"}
DECISION_AFFECTS = {61: "35, 40", 62: "34-39", 63: "2, 3", 64: "7, 8, 9", 65: "1, 2, 6", 66: "18, 42, 45, 47"}

HEADERS = [
    ("S.No", 6), ("Document reference", 22), ("Module (Excel)", 24), ("Original feature name", 28),
    ("Business requirement (Excel, verbatim)", 48), ("Suggested phase (Excel, verbatim)", 18),
    ("Requirement basis (Excel)", 20), ("Notes / dependencies (Excel)", 26), ("MoM reference", 24),
    ("Release phase", 22), ("Feature key", 30), ("Application module", 18), ("Planned backend API", 38),
    ("Database entities", 32), ("Frontend screens", 34), ("Depends on (feature keys)", 34),
    ("Acceptance criteria", 56), ("Build status", 14), ("Testing status", 14),
]
BUILD = ["Not started", "In progress", "Built", "Blocked"]
# S.No -> (build status, testing status, note appended to the acceptance criteria)
PROGRESS = {
    4: ("Built", "Tests passing", "BUILT with draft content; image-based options await client images."),
    5: ("Built", "Tests passing", "BUILT with draft content pending client review."),
    6: ("Built", "Tests passing", "BUILT: consent, validation, quality gate, private storage, delete. Thresholds need tuning on real photos."),
    7: ("In progress", "Tests passing", "PARTIAL: guided self-assessment only. Photo-based AI analysis not built (landmark model not yet available)."),
    8: ("In progress", "Tests passing", "PARTIAL: questionnaire path only. Photo path not built."),
    9: ("In progress", "Tests passing", "PARTIAL: indicative self-assessment only. Photo-based AI analysis not built."),
    10: ("Built", "Tests passing", "BUILT as rule-based advice from assessment results; draft content."),
    12: ("In progress", "Tests passing", "PARTIAL: hairstyle recommendations only. Preview on photo not built."),
    13: ("Built", "Tests passing", "BUILT from self-assessed face shape; draft content."),
}
TEST = ["Not tested", "Tests passing", "Tests failing"]


def main(source: str) -> None:
    src = load_workbook(source).worksheets[0]
    by_row = {f[0]: f for f in catalog.FEATURES}
    deps: dict[str, list[str]] = {}
    for feature, requires, _basis, _reason in catalog.DEPENDENCIES:
        deps.setdefault(feature, []).append(requires)
    phase_label = {"phase1": "Phase 1", "phase2": "Phase 2", "phase3": "Phase 3 (assumed)"}

    wb = Workbook()
    ws = wb.active
    ws.title = "RTM"
    font = Font(name="Arial", size=10)
    head_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", start_color="1F3864")
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    fills = {"Phase 1": "E2EFDA", "Phase 2": "DDEBF7", "Phase 3 (assumed)": "FFF2CC"}

    for col, (title, width) in enumerate(HEADERS, 1):
        cell = ws.cell(1, col, title)
        cell.font, cell.fill, cell.border = head_font, head_fill, border
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[1].height = 32

    module = None
    for r in range(2, src.max_row + 1):
        sno = src.cell(r, 1).value
        if sno is None:
            continue
        module = src.cell(r, 2).value or module  # merged module cells in the source
        name, scope, phase, basis, notes = (src.cell(r, c).value or "" for c in (3, 4, 5, 6, 7))
        if sno in by_row:
            _, key, _, app_module, phase_key, _, _ = by_row[sno]
            release, depends = phase_label[phase_key], ", ".join(deps.get(key, []))
            mom, api, entities, screens, accept = MAP[sno]
        elif sno in ADMIN_PHASE:
            key, app_module, release, depends = "(no own switch)", "admin", ADMIN_PHASE[sno], ""
            mom, api, entities, screens, accept = MAP[sno]
        else:
            key, app_module, release = "(not a feature)", "", "Decision"
            depends = f"Affects rows {DECISION_AFFECTS[sno]}"
            mom, api, entities, screens, accept = "p5 Open items" if sno in (61, 64, 65) else "p3-p5", "", "", "", DECISION
        built, tested, progress_note = PROGRESS.get(sno, ("Not started", "Not tested", ""))
        accept = f"{accept} [{progress_note}]" if progress_note else accept
        values = [sno, f"Feature List v1.0, row {r}", module, name, scope, phase, basis, notes, mom, release, key,
                  app_module, api, entities, screens, depends, accept, built, tested]
        for col, value in enumerate(values, 1):
            cell = ws.cell(r, col, value)
            cell.font, cell.border = font, border
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        if release in fills:
            ws.cell(r, 10).fill = PatternFill("solid", start_color=fills[release])

    last = ws.max_row
    ws.freeze_panes = "E2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{last}"
    for col, options in ((18, BUILD), (19, TEST)):
        dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=False)
        ws.add_data_validation(dv)
        dv.add(f"{get_column_letter(col)}2:{get_column_letter(col)}{last}")

    summary = wb.create_sheet("Summary")
    summary.column_dimensions["A"].width = 44
    for col in "BCDE":
        summary.column_dimensions[col].width = 16
    rows = [["Release phase", "Rows", "Built", "Tests passing"]]
    for label in ("Phase 1", "Phase 2", "Phase 3 (assumed)"):
        n = len(rows) + 1
        rows.append([label, f"=COUNTIF(RTM!$J$2:$J${last},A{n})",
                     f'=COUNTIFS(RTM!$J$2:$J${last},A{n},RTM!$R$2:$R${last},"Built")',
                     f'=COUNTIFS(RTM!$J$2:$J${last},A{n},RTM!$S$2:$S${last},"Tests passing")'])
    rows.append(["Discussed features (rows with a feature key)", "=SUM(B2:B4)", "=SUM(C2:C4)", "=SUM(D2:D4)"])
    rows.append(["Admin functions (inferred, rows 53-60)", f'=COUNTIF(RTM!$K$2:$K${last},"(no own switch)")', "", ""])
    rows.append(["Open decisions (rows 61-66)", f'=COUNTIF(RTM!$J$2:$J${last},"Decision")', "", ""])
    rows.append(["All rows", "=B5+B6+B7", "", ""])
    rows += [[], ["How to read this workbook"],
             ["Columns C-H are copied verbatim from the client's Feature List v1.0. Do not edit them here."],
             ["Release phase follows the Excel. 'Phase 3 (assumed)' = Excel 'Later release' / 'Later enhancement'; neither source document names a Phase 3."],
             ["'Phase 1 / enhancement' and 'Phase 2 / enhancement|later' rows sit in that phase with their own switch."],
             ["Planned API, entities and screens are the design target, not a statement that they exist. Build status says what exists."],
             ["Build status and Testing status (columns R, S) are the only cells to update as work lands. Example: Built / Tests passing."],
             ["Every one of the 52 feature keys has a tested release switch. Build status shows which features exist; bracketed notes in Acceptance criteria say what is partial."],
             ["Dependencies: only row 23 -> row 9 is stated in the Excel. The rest are engineering proposals (see catalog.py, basis column)."]]
    for r, row in enumerate(rows, 1):
        for c, value in enumerate(row, 1):
            cell = summary.cell(r, c, value)
            cell.font = Font(name="Arial", size=10, bold=(r in (1, 5, 8, 10)))
    for c in range(1, 5):
        summary.cell(1, c).fill, summary.cell(1, c).font = head_fill, head_font

    out = ROOT / "docs" / "Requirements_Traceability_Matrix.xlsx"
    wb.save(out)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1])
