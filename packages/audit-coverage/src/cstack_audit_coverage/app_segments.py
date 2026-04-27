from enum import StrEnum

# Microsoft well-known application IDs.
EXCHANGE_ONLINE_APP_ID = "00000002-0000-0ff1-ce00-000000000000"
SHAREPOINT_APP_ID = "00000003-0000-0ff1-ce00-000000000000"  # OneDrive shares this id
TEAMS_APP_ID = "cc15fd57-2c6c-4117-a88c-83b1d56b4bbe"
AZURE_PORTAL_APP_ID = "c44b4083-3bb0-49c1-b47d-974e53cbdf3c"
GRAPH_POWERSHELL_APP_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"
GRAPH_EXPLORER_APP_ID = "de8bc8b5-d9f9-48b1-a8ad-b748da725064"

M365_CORE_APP_IDS: frozenset[str] = frozenset(
    {EXCHANGE_ONLINE_APP_ID, SHAREPOINT_APP_ID, TEAMS_APP_ID}
)

ADMIN_PORTAL_APP_IDS: frozenset[str] = frozenset(
    {AZURE_PORTAL_APP_ID, GRAPH_POWERSHELL_APP_ID, GRAPH_EXPLORER_APP_ID}
)

HIGH_RISK_APP_IDS: frozenset[str] = frozenset({AZURE_PORTAL_APP_ID, GRAPH_POWERSHELL_APP_ID})

# clientAppTypes values that indicate a legacy authentication flow.
LEGACY_AUTH_CLIENT_APP_TYPES: frozenset[str] = frozenset({"other", "exchangeActiveSync"})


class AppSegment(StrEnum):
    ALL_APPS = "all_apps"
    M365_CORE = "m365_core"
    ADMIN_PORTALS = "admin_portals"
    LEGACY_AUTH = "legacy_auth"
    HIGH_RISK_APPS = "high_risk_apps"


def app_segment_ids(segment: AppSegment) -> frozenset[str]:
    """The well-known IDs that define an app segment, or empty for the
    catch-all and the legacy-auth segments which are not id-based."""
    if segment is AppSegment.M365_CORE:
        return M365_CORE_APP_IDS
    if segment is AppSegment.ADMIN_PORTALS:
        return ADMIN_PORTAL_APP_IDS
    if segment is AppSegment.HIGH_RISK_APPS:
        return HIGH_RISK_APP_IDS
    return frozenset()
