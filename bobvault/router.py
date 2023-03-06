from fastapi import APIRouter, Security, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .web import BobVaults
from .misc import verify_chain
from .models import BobVaultDataModel, ListOfPairsOut, ListOfTickersOut, OrderbookOut, PairTradesModel

from utils.misc import check_auth_token, MINTIMESTAMP, MAXTIMESTAMP
from utils.logging import info, warning
from utils.models import UploadResponse

_security = HTTPBearer()

router = APIRouter()

@router.post("/{chain}/upload", response_model = UploadResponse)
async def upload(chain: str, data: BobVaultDataModel,
                 credentials: HTTPAuthorizationCredentials = Security(_security)) -> UploadResponse:
    if not check_auth_token(credentials.credentials):
        return UploadResponse(status="Incorrect auth token")

    if not verify_chain(chain):
        return UploadResponse(status="Incorrect chain")

    BobVaults().store(chain, data)

    return UploadResponse(status="success")

@router.get("/{chain}/pairs", response_model = ListOfPairsOut)
async def bobvault_pairs(chain: str) -> ListOfPairsOut:
    if not verify_chain(chain):
        return ListOfPairsOut()

    return BobVaults().pairs(chain)

@router.get("/{chain}/tickers", response_model = ListOfTickersOut)
async def bobvault_tickers(chain: str) -> ListOfTickersOut:
    if not verify_chain(chain):
        return ListOfTickersOut()

    return BobVaults().tickers(chain)

@router.get("/{chain}/orderbook", response_model=OrderbookOut, response_model_exclude_unset=True)
async def bobvault_orderbook(chain: str, ticker_id: str, depth: int = 0) -> OrderbookOut:
    if not verify_chain(chain):
        return OrderbookOut()

    return BobVaults().orderbook(chain, ticker_id)

@router.get("/{chain}/historical_trades", response_model=PairTradesModel, response_model_exclude_none=True)
async def bobvault_historical_trades(chain: str,
                                     ticker_id: str, 
                                     type: str = Query(regex=r"^sell$|^buy$"),
                                     limit: int = 0,
                                     start_time: int = MINTIMESTAMP, 
                                     end_time: int = MAXTIMESTAMP) -> PairTradesModel:
    if not verify_chain(chain):
        return PairTradesModel()

    return BobVaults().historical_trades(chain, ticker_id, type, limit, start_time, end_time)

@router.on_event("startup")
async def startup_event():
    BobVaults()
