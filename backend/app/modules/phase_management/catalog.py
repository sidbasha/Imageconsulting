"""Feature catalog: the single source for feature keys, seeded into the database.

Every entry traces to a row of "Image Consulting Feature List v1.0" (S.No).
Phase assignment follows the Excel "Suggested phase" column. The Excel has no
"Phase 3": rows labelled "Later release" / "Later enhancement" are mapped to
phase3 as a documented assumption. Moving a feature between phases afterwards
is a data change (feature_flags.phase_id), not a code change.
"""

PHASES = [
    ("phase1", "Phase 1 - Customer application and basic image consulting", 1),
    ("phase2", "Phase 2 - Marketplace and professional consulting", 2),
    ("phase3", "Phase 3 - Later release (assumed mapping)", 3),
]

MODULES = [
    ("users", "Users, identity and eligibility"),
    ("assessments", "Assessments and questionnaires"),
    ("image_processing", "Image upload and quality"),
    ("ai_analysis", "AI analysis and previews"),
    ("recommendations", "Recommendations"),
    ("reports", "Reports"),
    ("subscriptions", "Subscriptions and payments"),
    ("products", "Digital and physical products"),
    ("stylists", "Stylists"),
    ("bookings", "Bookings"),
    ("consultations", "Consultations and audits"),
    ("messaging", "Messaging and moderation"),
    ("rewards", "Rewards"),
    ("promotions", "Promotions"),
]

# (excel_row, key, name, module, phase, excel_phase_label, is_enhancement)
FEATURES = [
    (1, "phase1.identity_verification", "Identity verification", "users", "phase1", "Phase 1", False),
    (2, "phase1.eligibility_verification", "Eligibility verification", "users", "phase1", "Phase 1", False),
    (3, "phase1.uae_only_access", "UAE-only launch access", "users", "phase1", "Phase 1", False),
    (4, "phase1.onboarding_quiz", "Visual onboarding quiz", "assessments", "phase1", "Phase 1", False),
    (5, "phase1.style_assessment", "Personal style assessment", "assessments", "phase1", "Phase 1", False),
    (6, "phase1.photo_assessment", "Photo-based assessment", "image_processing", "phase1", "Phase 1", False),
    (7, "phase1.face_shape", "Face-shape analysis", "ai_analysis", "phase1", "Phase 1", False),
    (8, "phase1.body_shape", "Body-shape analysis", "ai_analysis", "phase1", "Phase 1", False),
    (9, "phase1.seasonal_color", "Preliminary seasonal color analysis", "ai_analysis", "phase1", "Phase 1", False),
    (10, "phase1.outfit_recommendations", "Outfit recommendations", "recommendations", "phase1", "Phase 1", False),
    (11, "phase1.virtual_tryon", "Virtual outfit try-on", "ai_analysis", "phase1", "Phase 1", False),
    (12, "phase1.hair_preview", "Hair makeover preview", "ai_analysis", "phase1", "Phase 1 / enhancement", True),
    (13, "phase1.eyewear", "Eyewear recommendations", "recommendations", "phase1", "Phase 1 / enhancement", True),
    (14, "phase3.pmu_preview", "Permanent-makeup preview", "ai_analysis", "phase3", "Later enhancement", True),
    (15, "phase2.stylist_onboarding", "Stylist onboarding", "stylists", "phase2", "Phase 2", False),
    (16, "phase2.credential_submission", "Credential submission", "stylists", "phase2", "Phase 2", False),
    (17, "phase2.stylist_verification", "Stylist verification", "stylists", "phase2", "Phase 2", False),
    (18, "phase2.stylist_discovery", "Stylist profiles and discovery", "stylists", "phase2", "Phase 2", False),
    (19, "phase2.booking", "Consultation booking", "bookings", "phase2", "Phase 2", False),
    (20, "phase2.consultations", "In-app consultations", "consultations", "phase2", "Phase 2", False),
    (21, "phase2.occasion_audit", "Occasion-specific style audit", "consultations", "phase2", "Phase 2", False),
    (22, "phase2.wardrobe_audit", "Wardrobe audit", "consultations", "phase2", "Phase 2", False),
    (23, "phase2.makeup_audit", "Makeup audit", "consultations", "phase2", "Phase 2", False),
    (24, "phase2.expert_color_analysis", "Expert color analysis", "consultations", "phase2", "Phase 2", False),
    (25, "phase2.expert_reports", "Standardized expert reports", "reports", "phase2", "Phase 2", False),
    (26, "phase2.product_recognition", "Product recognition from photos", "ai_analysis", "phase2", "Phase 2 / enhancement", True),
    (27, "phase2.color_workspace", "Consultant-only color-analysis workspace", "ai_analysis", "phase2", "Phase 2", False),
    (28, "phase2.digital_draping", "Digital color draping", "ai_analysis", "phase2", "Phase 2", False),
    (29, "phase2.metered_tool_access", "Metered tool access", "subscriptions", "phase2", "Phase 2", False),
    (30, "phase2.messaging", "In-app messaging", "messaging", "phase2", "Phase 2", False),
    (31, "phase2.contact_detection", "Contact-sharing detection", "messaging", "phase2", "Phase 2", False),
    (32, "phase2.message_blocking", "Message blocking and warnings", "messaging", "phase2", "Phase 2", False),
    (33, "phase2.violation_tracking", "Violation tracking and suspension", "messaging", "phase2", "Phase 2", False),
    (34, "phase1.free_paid_access", "Free and paid feature access", "subscriptions", "phase1", "Phase 1", False),
    (35, "phase1.customer_subscriptions", "Customer subscriptions", "subscriptions", "phase1", "Phase 1", False),
    (36, "phase1.retail_links", "Retail product recommendations", "products", "phase1", "Phase 1", False),
    (37, "phase1.paid_reports", "Paid report access", "reports", "phase1", "Phase 1", False),
    (38, "phase1.digital_guides", "Digital guide catalog", "products", "phase1", "Phase 1", False),
    (39, "phase1.free_resources", "Complimentary digital resources", "products", "phase1", "Phase 1", False),
    (40, "phase2.consultant_subscriptions", "Consultant subscriptions", "subscriptions", "phase2", "Phase 2", False),
    (41, "phase2.service_payments", "In-app service payments", "subscriptions", "phase2", "Phase 2", False),
    (42, "phase2.paid_promotion", "Paid consultant promotion", "promotions", "phase2", "Phase 2 / later", True),
    (43, "phase1.loyalty_points", "Loyalty points", "rewards", "phase1", "Phase 1 / enhancement", True),
    (44, "phase2.reward_redemption", "Reward redemption", "rewards", "phase2", "Phase 2", False),
    (45, "phase2.testimonials", "Testimonials and recognition", "stylists", "phase2", "Phase 2", False),
    (46, "phase3.personal_shopper", "In-person personal shopper booking", "bookings", "phase3", "Later release", False),
    (47, "phase3.location_discovery", "Location-based discovery", "stylists", "phase3", "Later release", False),
    (48, "phase3.physical_products", "Physical product catalog", "products", "phase3", "Later release", False),
    (49, "phase3.brand_advertising", "Brand advertising", "promotions", "phase3", "Later release", False),
    (50, "phase3.geo_promotions", "Location-targeted promotions", "promotions", "phase3", "Later release", False),
    (51, "phase3.vouchers", "Vouchers and offers", "promotions", "phase3", "Later release", False),
    (52, "phase3.international_expansion", "International expansion", "users", "phase3", "Later release", False),
]

# (feature, requires, basis, reason). basis: "excel" = stated in the workbook,
# "mom" = follows from a recorded decision, "proposed" = engineering proposal
# to be confirmed. Dependencies are data and can be edited without a deploy.
DEPENDENCIES = [
    ("phase1.face_shape", "phase1.photo_assessment", "proposed", "Needs an uploaded photo"),
    ("phase1.body_shape", "phase1.photo_assessment", "proposed", "Needs an uploaded photo"),
    ("phase1.seasonal_color", "phase1.photo_assessment", "proposed", "Needs an uploaded photo"),
    ("phase1.outfit_recommendations", "phase1.style_assessment", "proposed", "Recommendations use assessment results"),
    ("phase1.virtual_tryon", "phase1.photo_assessment", "proposed", "Preview is drawn on the user photo"),
    ("phase1.virtual_tryon", "phase1.outfit_recommendations", "proposed", "Previews recommended outfits"),
    ("phase1.hair_preview", "phase1.face_shape", "proposed", "Excel: previews are based on face shape"),
    ("phase1.eyewear", "phase1.face_shape", "proposed", "Frame advice is based on face shape"),
    ("phase1.customer_subscriptions", "phase1.free_paid_access", "proposed", "Plans grant entitlements"),
    ("phase1.paid_reports", "phase1.free_paid_access", "proposed", "Purchases grant entitlements"),
    ("phase1.free_resources", "phase1.digital_guides", "proposed", "Free items live in the guide catalog"),
    ("phase2.credential_submission", "phase2.stylist_onboarding", "proposed", "Credentials belong to an application"),
    ("phase2.stylist_verification", "phase2.credential_submission", "proposed", "Vetting reviews submitted credentials"),
    ("phase2.stylist_discovery", "phase2.stylist_verification", "mom", "Only verified stylists may offer services"),
    ("phase2.booking", "phase2.stylist_discovery", "proposed", "A booking selects a stylist"),
    ("phase2.booking", "phase2.service_payments", "mom", "Consultations are paid and payments stay in the app"),
    ("phase2.consultations", "phase2.booking", "proposed", "A consultation fulfils a booking"),
    ("phase2.occasion_audit", "phase2.consultations", "proposed", "Delivered as a stylist consultation"),
    ("phase2.wardrobe_audit", "phase2.consultations", "proposed", "Delivered as a stylist consultation"),
    ("phase2.makeup_audit", "phase2.consultations", "proposed", "Delivered as a stylist consultation"),
    ("phase2.makeup_audit", "phase1.seasonal_color", "excel", "Row 23 note: requires completed seasonal color analysis"),
    ("phase2.expert_color_analysis", "phase2.consultations", "proposed", "Delivered as a stylist consultation"),
    ("phase2.digital_draping", "phase2.color_workspace", "proposed", "Draping is a tool inside the workspace"),
    ("phase2.metered_tool_access", "phase2.color_workspace", "proposed", "Meters use of the workspace"),
    ("phase2.messaging", "phase2.message_blocking", "mom", "Decision: contact sharing is blocked in chat"),
    ("phase2.contact_detection", "phase2.messaging", "proposed", "Screens chat messages"),
    ("phase2.message_blocking", "phase2.contact_detection", "proposed", "Blocks what detection flags"),
    ("phase2.violation_tracking", "phase2.contact_detection", "proposed", "Counts detected violations"),
    ("phase2.reward_redemption", "phase1.loyalty_points", "proposed", "Redeems earned points"),
    ("phase2.reward_redemption", "phase2.booking", "proposed", "Excel: points redeem for consultations"),
    ("phase2.testimonials", "phase2.consultations", "proposed", "Testimonials follow a completed consultation"),
    ("phase2.paid_promotion", "phase2.stylist_discovery", "proposed", "Promotes placement in discovery"),
    ("phase3.pmu_preview", "phase1.photo_assessment", "proposed", "Preview is drawn on the user photo"),
    ("phase3.personal_shopper", "phase2.booking", "proposed", "Uses the booking workflow"),
    ("phase3.location_discovery", "phase2.stylist_discovery", "proposed", "Extends stylist discovery"),
    ("phase3.geo_promotions", "phase3.brand_advertising", "proposed", "Targets brand campaigns"),
]

# Initial release required by the delivery strategy: only Phase 1 visible.
INITIAL_PHASE_STATE = {"phase1": True, "phase2": False, "phase3": False}

ROLES = [
    ("super_admin", "Super Admin"),
    ("admin", "Admin"),
    ("support_manager", "Support Manager"),
    ("stylist_manager", "Stylist Manager"),
    ("content_manager", "Content Manager"),
    ("finance_manager", "Finance Manager"),
    ("stylist", "Stylist"),
    ("customer", "Customer"),
]

# Only permissions that code actually checks are seeded. Release control is
# Super Admin only; the client-facing "admin" role deliberately has neither.
PERMISSIONS = {
    "release.view": ["super_admin"],
    "release.manage": ["super_admin"],
    # Supporting administration, Feature List rows 53-60 (inferred by the vendor,
    # not confirmed by the client). Role assignment is a proposal.
    "users.review": ["super_admin", "admin", "support_manager"],  # row 53: eligibility and identity
    "stylists.review": ["super_admin", "admin", "stylist_manager"],  # rows 53, 54: applications, credentials
    "pricing.manage": ["super_admin", "admin", "finance_manager"],  # row 55: plans, prices, entitlements
    "orders.manage": ["super_admin", "admin", "finance_manager"],  # fulfilment and refunds
    "content.manage": ["super_admin", "admin", "content_manager"],  # rows 56, 57: report templates, guides, retail links
    "moderation.manage": ["super_admin", "admin", "support_manager"],  # row 58
    "rewards.manage": ["super_admin", "admin", "finance_manager"],  # row 59
    "promotions.manage": ["super_admin", "admin", "content_manager"],  # row 60
    "settings.manage": ["super_admin", "admin"],  # policy values awaiting client decisions
    "stylist.practice": ["stylist"],  # a verified stylist's own tools
}
