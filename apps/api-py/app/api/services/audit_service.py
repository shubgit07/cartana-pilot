"""Deprecated legacy audit service tombstone.

PR verification and trust brief generation are orchestrated by
``app.api.services.pr_trust_service`` and ``app.core.workflow.pr_verification_graph``.
The legacy requirement-to-task coverage audit engine has been retired.
"""
from __future__ import annotations
