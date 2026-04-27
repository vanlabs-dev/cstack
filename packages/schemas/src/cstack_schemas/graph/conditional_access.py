from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from cstack_schemas.graph._base import GraphModel

ConditionalAccessPolicyState = Literal[
    "enabled",
    "disabled",
    "enabledForReportingButNotEnforced",
]


class Applications(GraphModel):
    include_applications: list[str] | None = None
    exclude_applications: list[str] | None = None
    include_user_actions: list[str] | None = None
    include_authentication_context_class_references: list[str] | None = None


class Users(GraphModel):
    include_users: list[str] | None = None
    exclude_users: list[str] | None = None
    include_groups: list[str] | None = None
    exclude_groups: list[str] | None = None
    include_roles: list[str] | None = None
    exclude_roles: list[str] | None = None
    include_guests_or_external_users: dict[str, Any] | None = None
    exclude_guests_or_external_users: dict[str, Any] | None = None


class Platforms(GraphModel):
    include_platforms: list[str] | None = None
    exclude_platforms: list[str] | None = None


class Locations(GraphModel):
    include_locations: list[str] | None = None
    exclude_locations: list[str] | None = None


class ClientApplications(GraphModel):
    include_service_principals: list[str] | None = None
    exclude_service_principals: list[str] | None = None
    service_principal_filter: dict[str, Any] | None = None


class Conditions(GraphModel):
    applications: Applications | None = None
    users: Users | None = None
    platforms: Platforms | None = None
    locations: Locations | None = None
    client_applications: ClientApplications | None = None
    client_app_types: list[str] | None = None
    user_risk_levels: list[str] | None = None
    sign_in_risk_levels: list[str] | None = None
    service_principal_risk_levels: list[str] | None = None
    devices: dict[str, Any] | None = None


GrantOperator = Annotated[Literal["AND", "OR"], Field(description="all or any of controls")]


class GrantControls(GraphModel):
    operator: GrantOperator | None = None
    built_in_controls: list[str] | None = None
    custom_authentication_factors: list[str] | None = None
    terms_of_use: list[str] | None = None
    authentication_strength: dict[str, Any] | None = None


class SessionControls(GraphModel):
    application_enforced_restrictions: dict[str, Any] | None = None
    cloud_app_security: dict[str, Any] | None = None
    persistent_browser: dict[str, Any] | None = None
    sign_in_frequency: dict[str, Any] | None = None
    continuous_access_evaluation: dict[str, Any] | None = None
    secure_sign_in_session: dict[str, Any] | None = None


class ConditionalAccessPolicy(GraphModel):
    id: str
    display_name: str
    state: ConditionalAccessPolicyState | None = None
    created_date_time: datetime | None = None
    modified_date_time: datetime | None = None
    conditions: Conditions | None = None
    grant_controls: GrantControls | None = None
    session_controls: SessionControls | None = None
