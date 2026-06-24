"""Source adapters for news-impact.

Importing this package registers the built-in adapters into
``sources.base.SOURCE_REGISTRY`` through their ``@register`` decorators. The
pipeline only imports ``sources.base`` (which imports this package first), so
without these side-effect imports the registry would be empty at runtime and
every configured source would be reported as "unknown" and skipped. Tests that
import an adapter module directly don't exercise that path, which is why the
gap is invisible to the suite.
"""
from __future__ import annotations

from . import stubs, yahoo  # noqa: F401  (imported for @register side effects)
