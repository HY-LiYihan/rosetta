# Agent Onboarding

Last updated: 2026-05-08

Before editing Rosetta:

1. Read the docs index.
2. Read the architecture boundaries.
3. Check the workflow and changelog requirements.
4. Keep UI code thin; place behavior in workflows or services.
5. Update docs and changelog with behavior changes.

Useful entrypoints:

1. `streamlit_app.py` for app navigation.
2. `app/ui/pages/` for Streamlit pages.
3. `app/workflows/` for workflow behavior.
4. `app/services/annotation_service.py` for runtime annotation prompt contracts.

Canonical Chinese reference: [Agent Onboarding](../../developer/AGENT_ONBOARDING.md).
