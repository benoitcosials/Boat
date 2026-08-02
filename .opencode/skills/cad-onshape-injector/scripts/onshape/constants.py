"""Constants for the Onshape REST API.

Values verified live 2026-08-01 on a Free-plan account.
"""

# API version prefix (path is /api/<API_VERSION>/...).
API_VERSION = "v10"

# Default production stack. Enterprise accounts use https://<company>.onshape.com.
DEFAULT_BASE_URL = "https://cad.onshape.com"

# Well-known part metadata property IDs. These are stable across all documents.
PROP_APPEARANCE = "57f3fb8efa3416c06701d60c"  # value: {"color": {red, green, blue}, "opacity"}
PROP_NAME = "57f3fb8efa3416c06701d60d"  # value: str
PROP_DESCRIPTION = "57f3fb8efa3416c06701d60e"  # value: str

# BTType discriminators used when building request bodies.
BT_FEATURE = "BTMFeature-134"
BT_PARAM_QUANTITY = "BTMParameterQuantity-147"
