from datetime import datetime

from pydantic import Field

from cstack_schemas.graph._base import GraphModel


class SignInActivity(GraphModel):
    last_sign_in_date_time: datetime | None = None
    last_non_interactive_sign_in_date_time: datetime | None = None
    last_sign_in_request_id: str | None = None


class User(GraphModel):
    id: str
    display_name: str | None = None
    user_principal_name: str | None = None
    account_enabled: bool | None = None
    user_type: str | None = None
    sign_in_activity: SignInActivity | None = None


class Group(GraphModel):
    id: str
    display_name: str | None = None
    mail_enabled: bool | None = None
    security_enabled: bool | None = None
    members: list[str] = Field(default_factory=list)


class DirectoryRole(GraphModel):
    id: str
    display_name: str | None = None
    description: str | None = None
    role_template_id: str | None = None
    members: list[str] = Field(default_factory=list)


class RoleAssignment(GraphModel):
    id: str
    principal_id: str | None = None
    role_definition_id: str | None = None
    directory_scope_id: str | None = None
