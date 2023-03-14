from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import PlainTextResponse

from asyncio import ensure_future

from .web import TotalSupply

from utils.settings import Settings
from utils.misc import async_every

_settings = Settings().get()

router = APIRouter()

tasks = BackgroundTasks()

@router.get("/", response_class=PlainTextResponse)
async def root() -> str:
    return str(TotalSupply().value)

@router.on_event("startup")
async def startup_event():
    ensure_future(async_every(
        TotalSupply().get_through_tokens,
        _settings.update_interval
    ))
