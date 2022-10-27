import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.logger import logger as fastapi_logger

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

if not load_dotenv('./.env'):
    RPCS = getenv('RPCS', 'https://polygon-rpc.com,https://mainnet.optimism.io')
    BOB_TOKEN = getenv('BOB_TOKEN', '0xB0B195aEFA3650A6908f15CdaC7D92F8a5791B0B')
    UPDATE_INTERVAL = int(getenv('UPDATE_INTERVAL', 20))
    PORT = int(getenv('PORT', 8080))

RPCS = RPCS.split(',')

info(f'RPCS = {RPCS}')
info(f'BOB_TOKEN = {BOB_TOKEN}')
info(f'UPDATE_INTERVAL = {UPDATE_INTERVAL}')
info(f'PORT = {PORT}')

ABI = '''
[{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
 {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"}]
'''

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
                        info(errmsg)
                        raise BaseException(errmsg)
                else:
                    new_dec = dec
                    if new_dec != first_dec:
                        errmsg = f'decimals as 18 on {ep_uri} expected'
                        info(errmsg)
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

def totalSupplyUpdate():
    global totalSupply
    global status
    global lastSuccessTimestamp
    global lastErrorTimestamp

    TS = getTotalSupply()
    if TS >= 0:
        totalSupply = TS
        lastSuccessTimestamp = time.time()
        status = 'success'
    else:
        lastErrorTimestamp = time.time()
        status = 'error'
    info(f'BOB total supply is {totalSupply} in {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}')

# Taken from https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds/49801719#49801719
def every(delay, task):
    next_time = time.time() + delay
    while True:
        time.sleep(max(0, next_time - time.time()))
        task()
        next_time += (time.time() - next_time) // delay * delay + delay

app = FastAPI(docs_url=None, redoc_url=None)
bg_task = threading.Thread(target=lambda: every(UPDATE_INTERVAL, totalSupplyUpdate))

@app.get("/", response_class=PlainTextResponse)
async def root() -> str:
    if totalSupply == int(totalSupply):
        return f'{str(totalSupply)}.0'
    else:
        return str(totalSupply)

@app.get("/health")
async def root() -> dict:
    secondsSinceLastSuccess = int(time.time() - lastSuccessTimestamp)
    secondsSinceLastError = int(time.time() - lastErrorTimestamp)
    return {"status": status,
            "currentDatetime": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "lastSuccessDatetime": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(lastSuccessTimestamp)),
            "secondsSinceLastSuccess": secondsSinceLastSuccess,
            "lastErrorDatetime": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(lastErrorTimestamp)),
            "secondsSinceLastError": secondsSinceLastError,
            "supplyRefreshInterval": UPDATE_INTERVAL}

@app.on_event("startup")
async def startup_event():
    global info
    local_logger=logging.getLogger()
    uvicorn_access_logger = logging.getLogger("uvicorn.error")
    fastapi_logger.handlers = uvicorn_access_logger.handlers
    local_logger.handlers = uvicorn_access_logger.handlers
    log_level = uvicorn_access_logger.level
    local_logger.setLevel(log_level)
    fastapi_logger.setLevel(log_level)
    info=uvicorn_access_logger.info

    bg_task.daemon = True
    bg_task.start()

if __name__ == '__main__':
    info(f'Initializing BOB totalSupply')
    totalSupplyUpdate()
    uvicorn.run(app, host="0.0.0.0", port=PORT, proxy_headers=True)