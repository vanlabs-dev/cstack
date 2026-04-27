from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class GraphModel(BaseModel):
    """Base class for Microsoft Graph entity models.

    Allowing extra fields keeps parsing forward-compatible when Graph adds
    properties; populating by either alias or python name lets callers pass
    raw Graph payloads or build models directly in Python.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        alias_generator=to_camel,
    )
