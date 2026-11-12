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
FEATURES: dict[str, bool] = {
    # "phase1.eyewear": False,
    # "phase2.product_recognition": False,
}
