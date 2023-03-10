from fastapi import APIRouter, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .web import BobStats
from .models import BobStatsDataForTwoPeriods

from utils.misc import check_auth_token
from utils.models import UploadResponse

_security = HTTPBearer()

router = APIRouter()

@router.get("/data", response_model=BobStatsDataForTwoPeriods)
async def provide() -> BobStatsDataForTwoPeriods:
    return BobStats().load()

@router.post("/upload", response_model=UploadResponse)
async def upload(data: BobStatsDataForTwoPeriods, \
                 credentials: HTTPAuthorizationCredentials = Security(_security)) -> UploadResponse:
    if not check_auth_token(credentials.credentials):
        return UploadResponse(status="Incorrect auth token")

    BobStats().store(data)
    return UploadResponse(status="success")

@router.on_event("startup")
async def startup_event():
    BobStats()
