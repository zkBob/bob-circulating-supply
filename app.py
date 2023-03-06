import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from fastapi.middleware.cors import CORSMiddleware

from os import getenv
from utils.logging import LoggerProvider

from bobstats.router import router as stats_router
from supply.router import router as supply_router
from bobvault.router import router as vault_router
from utils.settings import Settings
from utils.health import HealthRegistry, HealthOut

settings = Settings.get()
app = FastAPI(docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
)

app.include_router(stats_router, prefix="/bobstat")
app.include_router(vault_router, prefix="/coingecko/bobvault")
app.include_router(supply_router, prefix="/supply")

@app.get("/", response_class=RedirectResponse)
async def root() -> str:
    return '/supply'

@app.get("/health", response_model=HealthOut, response_model_exclude_none=True)
async def health():
    return HealthRegistry().publish()

@app.on_event("startup")
async def startup_event():
    LoggerProvider().switch_to_uvicorn()

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=settings.port, proxy_headers=True)