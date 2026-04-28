from datetime import datetime

from cstack_schemas.graph._base import GraphModel


class GeoCoordinates(GraphModel):
    latitude: float | None = None
    longitude: float | None = None


class SignInLocation(GraphModel):
    city: str | None = None
    state: str | None = None
    country_or_region: str | None = None
    geo_coordinates: GeoCoordinates | None = None


class DeviceDetail(GraphModel):
    device_id: str | None = None
    display_name: str | None = None
    operating_system: str | None = None
    browser: str | None = None
    is_compliant: bool | None = None
    is_managed: bool | None = None
    trust_type: str | None = None


class SignInStatus(GraphModel):
    error_code: int | None = None
    failure_reason: str | None = None
    additional_details: str | None = None


class SignIn(GraphModel):
    """Microsoft Graph signIn entity, narrowed to fields the anomaly model uses."""

    id: str
    created_date_time: datetime
    user_id: str
    user_principal_name: str
    app_id: str | None = None
    app_display_name: str | None = None
    client_app_used: str | None = None
    device_detail: DeviceDetail | None = None
    location: SignInLocation | None = None
    ip_address: str | None = None
    status: SignInStatus | None = None
    risk_level_aggregated: str | None = None
    risk_level_during_signin: str | None = None
    risk_state: str | None = None
    conditional_access_status: str | None = None
    authentication_requirement: str | None = None
    authentication_methods_used: list[str] | None = None
    is_interactive: bool | None = None
