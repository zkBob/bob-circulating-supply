from typing import Callable, Any
from decimal import Decimal

from time import gmtime, strftime, sleep, time
from json import JSONEncoder

from asyncio import sleep as asleep
from starlette.concurrency import run_in_threadpool

from .settings import Settings
from .logging import info

MINTIMESTAMP = 0
MAXTIMESTAMP = (2**63) - 1

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        else:
            return super().default(obj)

class Named():
    def name(self):
        try:
            name = self._name
        except:
            name = type(self).__name__
        return name

def format_timestamp(ts: int = None) -> str:
    if ts == None:
        gmt = gmtime()
    else:
        gmt = gmtime(ts)
    return strftime("%Y-%m-%d %H:%M:%S UTC", gmt)

def check_auth_token(authtoken: str) -> bool:
    return authtoken == Settings.get().upload_token

# Based on
# - https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds/49801719#49801719
def every(task: Callable, delay: int) -> None:
    first_time = True
    next_time = time() + delay
    while True:
        if not first_time:
            sleep(max(0, next_time - time()))
        else:
            first_time = False
        task()
        next_time += (time() - next_time) // delay * delay + delay

# Based on
# - https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/tasks.py
# - https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds/49801719#49801719
async def async_every(task: Callable, delay: int) -> None:
    first_time = True
    next_time = time() + delay
    while True:
        if not first_time:
            await asleep(max(0, next_time - time()))
        else:
            first_time = False
        await run_in_threadpool(task)
        next_time += (time() - next_time) // delay * delay + delay

def execute_request_with_time_measurement(func: Callable, *args, **kwargs) -> Any:
    ts_checkpoint = time()
    ret = func(*args, **kwargs)
    info(f'Response prepared in {time() - ts_checkpoint}')
    return ret
