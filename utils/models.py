from typing import Optional, Dict

from pydantic import BaseModel

class TimestampedBaseModel(BaseModel):
    timestamp: int

class UploadResponse(BaseModel):
    status: str