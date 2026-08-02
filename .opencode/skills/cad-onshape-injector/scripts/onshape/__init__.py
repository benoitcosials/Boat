"""Onshape session-based API client.

Drives Onshape's own REST backend through an authenticated browser session
(cookies + X-XSRF-TOKEN) instead of API keys. Session calls are NOT counted
against the Free-plan annual API quota, so iterations are effectively unlimited.

Layers:
    DocumentContext     parse an Onshape document URL -> (base_url, did, wid)
    OnshapeSession      transport: persistent Playwright context, cookie + XSRF
    FeatureStudioClient one .fs file  == one Feature Studio  (sync)
    PartStudioClient    instantiate features, colour/name parts
    VersionsClient      commit = create an immutable Version snapshot
    get_length_unit     read the document's workspace length unit
"""

from .context import DocumentContext
from .feature_studio import FeatureStudioClient
from .part_studio import PartStudioClient
from .session import OnshapeError, OnshapeSession
from .units import get_length_unit
from .versions import VersionsClient

__all__ = [
    "DocumentContext",
    "OnshapeError",
    "OnshapeSession",
    "FeatureStudioClient",
    "PartStudioClient",
    "VersionsClient",
    "get_length_unit",
]
