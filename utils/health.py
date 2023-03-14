from functools import cache
from typing import List, Optional, Dict, Union

from time import time

from pydantic import BaseModel, ValidationError

from .models import TimestampedBaseModel
from .misc import format_timestamp, Named
from .logging import warning, info

class WorkerHealthModelBase(BaseModel):
    status: str
    lastSuccessTimestamp: int
    lastErrorTimestamp: int
    dataTimestamp: Optional[int]

class WorkerHealthModelOut(WorkerHealthModelBase):
    lastSuccessDatetime: Optional[str]
    secondsSinceLastSuccess: Optional[int]
    lastErrorDatetime: Optional[str]
    secondsSinceLastError: Optional[int]

class HealthOut(BaseModel):
    currentDatetime: str
    modules: Dict[str, Union[WorkerHealthModelOut, Dict[str, WorkerHealthModelOut]]]

class HealthException(Exception):
    pass

class Health(Named):
    healthdata: WorkerHealthModelBase

    def _load(self) -> TimestampedBaseModel:
        warning(f'Considering {self.name()} not healthy since no data found')
        raise HealthException

    def initialize_healthdata(self):
        self.healthdata = WorkerHealthModelBase(
            status='error',
            lastSuccessTimestamp=0,
            lastErrorTimestamp=0
        )
        try:
            data = self._load()
            try:
                data_ts = data.timestamp
            except AttributeError:
                data_ts = data['timestamp']
            self.record_sucess(data_ts, False)
        except (IOError, ValidationError, HealthException):
            pass
        
    def record_sucess(self, data_ts: int, record_curtime: bool = True):
        self.healthdata.status = 'success'
        self.healthdata.dataTimestamp = data_ts
        if record_curtime:
            self.healthdata.lastSuccessTimestamp = int(time())

    def record_error(self):
        self.healthdata.status = 'error'
        self.healthdata.lastErrorTimestamp = int(time())

    def healthdata_for_publishing(self, curtime: int) -> WorkerHealthModelOut:
        info(f'Preparing {self.name()} healthdata for publishing')
        hd = WorkerHealthModelOut.parse_obj(self.healthdata)

        hd.lastSuccessDatetime = format_timestamp(hd.lastSuccessTimestamp)
        hd.lastErrorDatetime = format_timestamp(hd.lastErrorTimestamp)
        hd.secondsSinceLastSuccess = curtime - hd.lastSuccessTimestamp
        hd.secondsSinceLastError = curtime -  hd.lastErrorTimestamp

        return hd

@cache
class HealthRegistry():
    _items: List[Health]

    def __init__(self):
        self._items = []

    def append(self, item: Health) -> None:
        info(f'Registering {item.name()} for healthdata')
        self._items.append(item)

    def publish(self) -> HealthOut:
        curtime = int(time())
        retval = HealthOut(currentDatetime = format_timestamp(curtime), modules = {})
        for i in self._items:
            retval.modules.update({
                i.name(): i.healthdata_for_publishing(curtime)
            })
        return retval
