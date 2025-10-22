
from pydantic import BaseModel, field_serializer
from typing import Optional, Any, Dict
import datetime

class APIResponse(BaseModel):
    success: bool
    message: str
    errors: Optional[Dict[str, Any]] = None
    data: Optional[Any] = None
    timestamp: datetime.datetime

    @field_serializer('timestamp')
    def serialize_dt(self, dt: datetime.datetime, _info):
        return dt.isoformat()

def create_response(success: bool, message: str, data: Optional[Any] = None, errors: Optional[Dict[str, Any]] = None) -> APIResponse:
    return APIResponse(
        success=success,
        message=message,
        data=data,
        errors=errors,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )