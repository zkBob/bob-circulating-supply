import uvicorn
from fastapi import FastAPI, Security, Request, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import PlainTextResponse
from fastapi.logger import logger as fastapi_logger

from typing import Union

from json import load, dump
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
from os import getenv
from dotenv import load_dotenv
import logging
import threading
import time
from decimal import Decimal

FORMAT = "%(levelname)s:     %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
info=logging.info
error=logging.error
warning=logging.warning

load_dotenv()

RPCS = getenv('RPCS', 'https://polygon-rpc.com,https://mainnet.optimism.io')
BOB_TOKEN = getenv('BOB_TOKEN', '0xB0B195aEFA3650A6908f15CdaC7D92F8a5791B0B')
UPDATE_INTERVAL = int(getenv('UPDATE_INTERVAL', 20))
PORT = int(getenv('PORT', 8080))
UPLOAD_TOKEN = getenv('UPLOAD_TOKEN', 'default')
SNAPSHOT_DIR = getenv('SNAPSHOT_DIR', '.')
COINGECKO_SNAPSHOT_FILE = getenv('COINGECKO_SNAPSHOT_FILE', 'bobvault-polygon-coingecko-data.json')
BOBSTAT_SNAPSHOT_FILE = getenv('BOBSTAT_SNAPSHOT_FILE', 'bobstat-data.json')

RPCS = RPCS.split(',')

info(f'RPCS = {RPCS}')
info(f'BOB_TOKEN = {BOB_TOKEN}')
info(f'UPDATE_INTERVAL = {UPDATE_INTERVAL}')
info(f'PORT = {PORT}')
if UPLOAD_TOKEN != 'default':
    info(f'UPLOAD_TOKEN is set')
else:
    info(f'UPLOAD_TOKEN = {UPLOAD_TOKEN}')
info(f'SNAPSHOT_DIR = {SNAPSHOT_DIR}')
info(f'COINGECKO_SNAPSHOT_FILE = {COINGECKO_SNAPSHOT_FILE}')
info(f'BOBSTAT_SNAPSHOT_FILE = {BOBSTAT_SNAPSHOT_FILE}')

ABI = '''
[{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
 {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"}]
'''

KTIMESTAMP = 'timestamp'
MINTIMESTAMP = 0
MAXTIMESTAMP = (2**63) - 1

tokens = []
decimals = False
for u in RPCS:
    w3 = Web3(HTTPProvider(u))
    tokens.append(w3.eth.contract(abi = ABI, address = BOB_TOKEN))

def getTotalSupply() -> Decimal:
    global decimals

    first_dec = 0
    TS = 0
    for c in tokens:
        try:
            ep_uri = c.web3.provider.endpoint_uri
            if not decimals:
                dec = int(c.functions.decimals().call())
                if first_dec == 0:
                    first_dec = dec
                    if first_dec != 18:
                        errmsg = f'decimals as 18 on {ep_uri} expected'
                        error(errmsg)
                        raise BaseException(errmsg)
                else:
                    new_dec = dec
                    if new_dec != first_dec:
                        errmsg = f'decimals on {ep_uri} do not match'
                        error(errmsg)
                        raise BaseException(errmsg)
            local_TS = Web3.fromWei(c.functions.totalSupply().call(), 'ether')
            info(f'BOB totalSupply on {ep_uri} is {local_TS}')
            TS += local_TS
        except:
            info(f'Cannot get BOB totalSupply on {ep_uri}')
            return Decimal(-1)
    if first_dec:
        decimals = True
    return TS

lastSuccessTimestamp = 0
lastErrorTimestamp = 0
totalSupply = 0
status = 'success'

def format_timestamp(_ts = None):
    if _ts == None:
        gmt = time.gmtime()
    else:
        gmt = time.gmtime(_ts)
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", gmt)

def totalSupplyUpdate():
    global totalSupply
    global status
    global lastSuccessTimestamp
    global lastErrorTimestamp

    cur_time = int(time.time())

    TS = getTotalSupply()
    if TS >= 0:
        totalSupply = TS
        lastSuccessTimestamp = cur_time
        status = 'success'
    else:
        lastErrorTimestamp = cur_time
        status = 'error'
    info(f'BOB total supply is {totalSupply} in {format_timestamp()}')

# Taken from https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds/49801719#49801719
def every(delay, task):
    next_time = time.time() + delay
    while True:
        time.sleep(max(0, next_time - time.time()))
        task()
        next_time += (time.time() - next_time) // delay * delay + delay

def check_token(_token):
    return _token == UPLOAD_TOKEN

def initialize_healthdata_from_snapshot(fname):
    health = {}
    health['lastSuccessTimestamp'] = 0
    health['lastErrorTimestamp'] = 0
    try:
        with open(fname, 'r') as json_file:
            data = load(json_file)
        health['status'] = 'success'
        health['dataTimestamp'] = data['timestamp']
        del data
    except IOError:
        warning(f'No snapshot {fname} found')
        health['status'] = 'error'
    return health

info(f'Checking for previous bobvault data')
bobvaults_data_health = {}
bobvaults_data_health['polygon'] = initialize_healthdata_from_snapshot(f'{SNAPSHOT_DIR}/{COINGECKO_SNAPSHOT_FILE}')

info(f'Checking for available bob statistics')
bobstat_data_health = {}
bobstat_data_health = initialize_healthdata_from_snapshot(f'{SNAPSHOT_DIR}/{BOBSTAT_SNAPSHOT_FILE}')

app = FastAPI(docs_url=None, redoc_url=None)
security = HTTPBearer()
bg_task = threading.Thread(target=lambda: every(UPDATE_INTERVAL, totalSupplyUpdate))

@app.get("/", response_class=PlainTextResponse)
async def root() -> str:
    if totalSupply == int(totalSupply):
        return f'{str(totalSupply)}.0'
    else:
        return str(totalSupply)

@app.get("/health")
async def health() -> dict:
    cur_time = int(time.time())
    secondsSinceLastSuccess = cur_time - lastSuccessTimestamp
    secondsSinceLastError = cur_time - lastErrorTimestamp
    health_response = {"status": status,
            "currentDatetime": format_timestamp(),
            "lastSuccessDatetime": format_timestamp(lastSuccessTimestamp),
            "secondsSinceLastSuccess": secondsSinceLastSuccess,
            "lastErrorDatetime": format_timestamp(lastErrorTimestamp),
            "secondsSinceLastError": secondsSinceLastError,
            "supplyRefreshInterval": UPDATE_INTERVAL,
            "BobVault": {},
            "BobStat": {}
        }
    
    health_response["BobStat"] = bobstat_data_health
    health_response["BobStat"]['lastSuccessDatetime'] = format_timestamp(bobstat_data_health['lastSuccessTimestamp'])
    health_response["BobStat"]['lastErrorDatetime'] = format_timestamp(bobstat_data_health['lastErrorTimestamp'])
    health_response["BobStat"]['secondsSinceLastSuccess'] = cur_time - bobstat_data_health['lastSuccessTimestamp']
    health_response["BobStat"]['secondsSinceLastError'] = cur_time -  bobstat_data_health['lastErrorTimestamp']
    
    for chain in bobvaults_data_health:
        health_response["BobVault"][chain] = bobvaults_data_health[chain]
        health_response["BobVault"][chain]['lastSuccessDatetime'] = format_timestamp(bobvaults_data_health[chain]['lastSuccessTimestamp'])
        health_response["BobVault"][chain]['lastErrorDatetime'] = format_timestamp(bobvaults_data_health[chain]['lastErrorTimestamp'])
        health_response["BobVault"][chain]['secondsSinceLastSuccess'] = cur_time - bobvaults_data_health[chain]['lastSuccessTimestamp']
        health_response["BobVault"][chain]['secondsSinceLastError'] = cur_time -  bobvaults_data_health[chain]['lastErrorTimestamp']
    
    return health_response

@app.post("/coingecko/bobvault/polygon/upload")
async def bobvault_upload(data: Request, credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    global bobvaults_data_health

    if not check_token(credentials.credentials):
        return {"status": "Incorrect auth token"}

    cur_time = int(time.time())
    try:
        cg_data = await data.json()
    except:
        bobvaults_data_health['polygon']['status'] = 'error'
        bobvaults_data_health['polygon']['lastErrorTimestamp'] = cur_time
        error('Incorrect data received')
        return {"status": "Incorrect data"}

    if not KTIMESTAMP in cg_data:
        bobvaults_data_health['polygon']['status'] = 'error'
        bobvaults_data_health['polygon']['lastErrorTimestamp'] = cur_time
        error(f'{KTIMESTAMP} missed in new coingecko data')
        return {"status": "Incorrect data"}

    s = set(cg_data.keys())
    s.discard(KTIMESTAMP)
    if len(s) == 0:
        bobvaults_data_health['polygon']['status'] = 'error'
        bobvaults_data_health['polygon']['lastErrorTimestamp'] = cur_time
        error('No market data')
        return {"status": "No market data provided"}

    delimiter = '/'
    info(f'New coingecko data stamped as {cg_data[KTIMESTAMP]} contains {delimiter.join(s)}' + 
          f'in {format_timestamp()}')
    
    with open(f'{SNAPSHOT_DIR}/{COINGECKO_SNAPSHOT_FILE}', 'w') as json_file:
        dump(cg_data, json_file)

    bobvaults_data_health['polygon']['status'] = 'success'
    bobvaults_data_health['polygon']['dataTimestamp'] = cg_data[KTIMESTAMP]
    bobvaults_data_health['polygon']['lastSuccessTimestamp'] = cur_time

    return {"status": "success"}

@app.get("/coingecko/bobvault/polygon/pairs")
async def bobvault_pairs() -> dict:
    ts_checkpoint = time.time()
    try:
        with open(f'{SNAPSHOT_DIR}/{COINGECKO_SNAPSHOT_FILE}', 'r') as json_file:
            cg_data = load(json_file)
    except IOError:
        warning(f'No snapshot {COINGECKO_SNAPSHOT_FILE} found')
        return []
    response = []
    s = set(cg_data.keys())
    s.discard(KTIMESTAMP)
    for pair in s:
        response.append({
            'ticker_id': pair,
            'base': cg_data[pair]['base_currency'],
            'target': cg_data[pair]['target_currency'],
            'pool_id': cg_data[pair]['pool_id']
        })
    del cg_data
    info(f'Response prepared in {time.time() - ts_checkpoint}')
    return response

@app.get("/coingecko/bobvault/polygon/tickers")
async def bobvault_tickers() -> dict:
    ts_checkpoint = time.time()
    try:
        with open(f'{SNAPSHOT_DIR}/{COINGECKO_SNAPSHOT_FILE}', 'r') as json_file:
            cg_data = load(json_file)
    except IOError:
        warning(f'No snapshot {COINGECKO_SNAPSHOT_FILE} found')
        return []
    response = []
    s = set(cg_data.keys())
    s.discard(KTIMESTAMP)
    for pair in s:
        response.append({
            'ticker_id': pair,
            'base_currency': cg_data[pair]['base_currency'],
            'target_currency': cg_data[pair]['target_currency'],
            'last_price': cg_data[pair]['last_price'],
            'base_volume': cg_data[pair]['base_volume'],
            'target_volume': cg_data[pair]['target_volume'],
            'pool_id': cg_data[pair]['pool_id'],
            'bid': cg_data[pair]['bid'],
            'ask': cg_data[pair]['ask'],
            'high': cg_data[pair]['high'],
            'low': cg_data[pair]['low']
        })
    del cg_data
    info(f'Response prepared in {time.time() - ts_checkpoint}')
    return response

@app.get("/coingecko/bobvault/polygon/orderbook")
async def bobvault_orderbook(ticker_id: str, depth: int = 0) -> dict:
    ts_checkpoint = time.time()
    try:
        with open(f'{SNAPSHOT_DIR}/{COINGECKO_SNAPSHOT_FILE}', 'r') as json_file:
            cg_data = load(json_file)
    except IOError:
        warning(f'No snapshot {COINGECKO_SNAPSHOT_FILE} found')
        return {}

    if not ticker_id in cg_data:
        return {}

    response = {
        'ticker_id': ticker_id,
        'timestamp': cg_data[ticker_id]['timestamp'],
        'bids': cg_data[ticker_id]['orderbook']['bids'],
        'asks': cg_data[ticker_id]['orderbook']['asks']
    }
    del cg_data
    info(f'Response prepared in {time.time() - ts_checkpoint}')
    return response

@app.get("/coingecko/bobvault/polygon/historical_trades")
async def bobvault_historical_trades(
    ticker_id: str, 
    type: str = Query(regex=r"^sell$|^buy$"),
    limit: int = 0,
    start_time: int = MINTIMESTAMP, 
    end_time: int = MAXTIMESTAMP
    ) -> dict:
    ts_checkpoint = time.time()
    try:
        with open(f'{SNAPSHOT_DIR}/{COINGECKO_SNAPSHOT_FILE}', 'r') as json_file:
            cg_data = load(json_file)
    except IOError:
        warning(f'No snapshot {COINGECKO_SNAPSHOT_FILE} found')
        return {}

    if not ticker_id in cg_data:
        return {}

    if limit == 0 and start_time == MINTIMESTAMP and end_time == MAXTIMESTAMP:
        response = { type: cg_data[ticker_id]['trades'][type] }
    elif limit != 0 and start_time == MINTIMESTAMP and end_time == MAXTIMESTAMP:
        response = { type: cg_data[ticker_id]['trades'][type][-limit:] }
    else:
        response = { type: [] }
        count = 0
        for trade in cg_data[ticker_id]['trades'][type]:
            if trade['trade_timestamp'] >= start_time and trade['trade_timestamp'] <= end_time:
                response[type].append(trade)
                count += 1
                if count == limit:
                    break
    del cg_data
    info(f'Response prepared in {time.time() - ts_checkpoint}')
    return response

@app.post("/bobstat/upload")
async def bobstat_upload(data: Request, credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    global bobstat_data_health

    if not check_token(credentials.credentials):
        return {"status": "Incorrect auth token"}

    cur_time = int(time.time())
    try:
        data = await data.json()
    except:
        bobstat_data_health['status'] = 'error'
        bobstat_data_health['lastErrorTimestamp'] = cur_time
        error('Incorrect data received')
        return {"status": "Incorrect data"}

    if not KTIMESTAMP in data:
        bobstat_data_health['status'] = 'error'
        bobstat_data_health['lastErrorTimestamp'] = cur_time
        error(f'{KTIMESTAMP} missed in new bobstat data')
        return {"status": "Incorrect data"}

    info(f'New bobstat data stamped as {data[KTIMESTAMP]} received')
    
    with open(f'{SNAPSHOT_DIR}/{BOBSTAT_SNAPSHOT_FILE}', 'w') as json_file:
        dump(data, json_file)

    bobstat_data_health['status'] = 'success'
    bobstat_data_health['dataTimestamp'] = data[KTIMESTAMP]
    bobstat_data_health['lastSuccessTimestamp'] = cur_time

    return {"status": "success"}

@app.get("/bobstat")
async def bobvault_pairs() -> dict:
    ts_checkpoint = time.time()

    empty_response = {
        KTIMESTAMP: int(ts_checkpoint),
        'current': {
            'timestamp': int(ts_checkpoint - 23),
            'totalSupply': 17500250.946412587857161492,
            'collaterisedCirculatedSupply': 5131885.9515,
            'volumeUSD': 2956494.05,
            'holders': 2420
        },
        'previous': {
            'timestamp': int(ts_checkpoint - 23) - 24 * 60 * 60,
            'totalSupply': 17500250.946412587857161492,
            'collaterisedCirculatedSupply': 4861467.674,
            'volumeUSD': 2956494.05 - 55348.17,
            'holders': 2406
        }
    }

    try:
        with open(f'{SNAPSHOT_DIR}/{BOBSTAT_SNAPSHOT_FILE}', 'r') as json_file:
            data = load(json_file)
    except IOError:
        warning(f'No snapshot {BOBSTAT_SNAPSHOT_FILE} found')
        return empty_response

    info(f'Response prepared in {time.time() - ts_checkpoint}')
    return data

@app.on_event("startup")
async def startup_event():
    global info
    global warning
    global error

    local_logger=logging.getLogger()
    uvicorn_access_logger = logging.getLogger("uvicorn.error")
    fastapi_logger.handlers = uvicorn_access_logger.handlers
    local_logger.handlers = uvicorn_access_logger.handlers
    log_level = uvicorn_access_logger.level
    local_logger.setLevel(log_level)
    fastapi_logger.setLevel(log_level)
    info=uvicorn_access_logger.info
    warning=uvicorn_access_logger.warning
    error=uvicorn_access_logger.error

    bg_task.daemon = True
    bg_task.start()

if __name__ == '__main__':
    info(f'Initializing BOB totalSupply')
    totalSupplyUpdate()
    uvicorn.run(app, host="0.0.0.0", port=PORT, proxy_headers=True)