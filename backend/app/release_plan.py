"""WHAT IS LIVE IN THE APP. Developers only.

There is deliberately no screen and no API for this. To change what users see:

1. Edit PHASES (and, if needed, FEATURES) below.
2. Check it:   python -m app.cli release check
3. Apply it:   python -m app.cli release apply --note "Why this release"
               (add --at 2027-01-15T06:00:00+04:00 to schedule it instead)

Deploys apply this file automatically when the container starts.

Every release is recorded. See them with `python -m app.cli release history`
and go back with `python -m app.cli release rollback <version> --note "..."`.

A feature is live when its phase is on AND it is not switched off in FEATURES.
Feature keys and the Feature List row each one traces to are in
app/modules/phase_management/catalog.py. A release that would leave an enabled
feature without one it depends on is refused, with the reason.

Data is never deleted: switching something off hides it; switching it back on
brings everything back.
"""

PHASES: dict[str, bool] = {
    "phase1": True,   # Customer app and basic image consulting
    "phase2": True,   # Marketplace and professional consulting
    "phase3": True,   # Later release (assumed mapping)
}

# Individual features to hide inside a phase that is on. Leave empty normally.
# To hide one, uncomment its line (the value False hides it). Row = Feature List row.
FEATURES: dict[str, bool] = {
    # --- Phase 1 - Customer application and basic image consulting ---
    # "phase1.identity_verification": False,        #  1. Identity verification
    # "phase1.eligibility_verification": False,     #  2. Eligibility verification
    # "phase1.uae_only_access": False,              #  3. UAE-only launch access
    # "phase1.onboarding_quiz": False,              #  4. Visual onboarding quiz
    # "phase1.style_assessment": False,             #  5. Personal style assessment
    # "phase1.photo_assessment": False,             #  6. Photo-based assessment
    # "phase1.face_shape": False,                   #  7. Face-shape analysis
    # "phase1.body_shape": False,                   #  8. Body-shape analysis
    # "phase1.seasonal_color": False,               #  9. Preliminary seasonal color analysis
    # "phase1.outfit_recommendations": False,       # 10. Outfit recommendations
    # "phase1.virtual_tryon": False,                # 11. Virtual outfit try-on
    # "phase1.hair_preview": False,                 # 12. Hair makeover preview (enhancement)
    # "phase1.eyewear": False,                      # 13. Eyewear recommendations (enhancement)
    # "phase1.free_paid_access": False,             # 34. Free and paid feature access
    # "phase1.customer_subscriptions": False,       # 35. Customer subscriptions
    # "phase1.retail_links": False,                 # 36. Retail product recommendations
    # "phase1.paid_reports": False,                 # 37. Paid report access
    # "phase1.digital_guides": False,               # 38. Digital guide catalog
    # "phase1.free_resources": False,               # 39. Complimentary digital resources
    # "phase1.loyalty_points": False,               # 43. Loyalty points (enhancement)
    # --- Phase 2 - Marketplace and professional consulting ---
    # "phase2.stylist_onboarding": False,           # 15. Stylist onboarding
    # "phase2.credential_submission": False,        # 16. Credential submission
    # "phase2.stylist_verification": False,         # 17. Stylist verification
    # "phase2.stylist_discovery": False,            # 18. Stylist profiles and discovery
    # "phase2.booking": False,                      # 19. Consultation booking
    # "phase2.consultations": False,                # 20. In-app consultations
    # "phase2.occasion_audit": False,               # 21. Occasion-specific style audit
    # "phase2.wardrobe_audit": False,               # 22. Wardrobe audit
    # "phase2.makeup_audit": False,                 # 23. Makeup audit
    # "phase2.expert_color_analysis": False,        # 24. Expert color analysis
    # "phase2.expert_reports": False,               # 25. Standardized expert reports
    # "phase2.product_recognition": False,          # 26. Product recognition from photos (enhancement)
    # "phase2.color_workspace": False,              # 27. Consultant-only color-analysis workspace
    # "phase2.digital_draping": False,              # 28. Digital color draping
    # "phase2.metered_tool_access": False,          # 29. Metered tool access
    # "phase2.messaging": False,                    # 30. In-app messaging
    # "phase2.contact_detection": False,            # 31. Contact-sharing detection
    # "phase2.message_blocking": False,             # 32. Message blocking and warnings
    # "phase2.violation_tracking": False,           # 33. Violation tracking and suspension
    # "phase2.consultant_subscriptions": False,     # 40. Consultant subscriptions
    # "phase2.service_payments": False,             # 41. In-app service payments
    # "phase2.paid_promotion": False,               # 42. Paid consultant promotion (enhancement)
    # "phase2.reward_redemption": False,            # 44. Reward redemption
    # "phase2.testimonials": False,                 # 45. Testimonials and recognition
    # --- Phase 3 - Later release (assumed mapping) ---
    # "phase3.pmu_preview": False,                  # 14. Permanent-makeup preview (enhancement)
    # "phase3.personal_shopper": False,             # 46. In-person personal shopper booking
    # "phase3.location_discovery": False,           # 47. Location-based discovery
    # "phase3.physical_products": False,            # 48. Physical product catalog
    # "phase3.brand_advertising": False,            # 49. Brand advertising
    # "phase3.geo_promotions": False,               # 50. Location-targeted promotions
    # "phase3.vouchers": False,                     # 51. Vouchers and offers
    # "phase3.international_expansion": False,      # 52. International expansion
}
