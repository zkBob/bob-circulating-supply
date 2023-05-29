from fastapi import APIRouter, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .web import BobStats
from .models import BobStatsDataForTwoPeriodsAPI, BobStatsDataForTwoPeriodsToFeed, GainStatsAPI

from utils.misc import check_auth_token
from utils.models import UploadResponse

_security = HTTPBearer()

router = APIRouter()

@router.get("/", response_model=BobStatsDataForTwoPeriodsAPI)
async def provide() -> BobStatsDataForTwoPeriodsAPI:
    return BobStats().loadMainStat()

@router.get("/yield", response_model=GainStatsAPI, response_model_exclude_unset=True)
async def provide() -> GainStatsAPI:
    return BobStats().loadYieldStat()

@router.post("/upload", response_model=UploadResponse)
async def upload(data: BobStatsDataForTwoPeriodsToFeed, \
                 credentials: HTTPAuthorizationCredentials = Security(_security)) -> UploadResponse:
    if not check_auth_token(credentials.credentials):
        return UploadResponse(status="Incorrect auth token")

    BobStats().store(data)
    return UploadResponse(status="success")

@router.on_event("startup")
async def startup_event():
    BobStats()
