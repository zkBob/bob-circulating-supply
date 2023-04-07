from functools import cache
from time import time
from json import dump
from decimal import Decimal

from pydantic import ValidationError

from .models import *

from utils.logging import info, error, warning
from utils.settings import Settings
from utils.health import Health, HealthRegistry
from utils.misc import CustomJSONEncoder

_settings = Settings.get()

@cache
class BobStats(Health):

    def __init__(self):
        self.filename = f'{_settings.snapshot_dir}/{_settings.bobstat_snapshot_file}'

        info(f'Checking for available bob statistics')
        self.initialize_healthdata()
        HealthRegistry().append(self)

    def _dump(self, data: BobStatsDataForTwoPeriods):
        with open(self.filename, 'w') as json_file:
            dump(data.dict(), json_file, cls=CustomJSONEncoder)

    def _load(self) -> BobStatsDataForTwoPeriods:
        try:
            with open(self.filename, 'r') as json_file:
                data = ''.join(json_file.readlines())
                data = BobStatsDataForTwoPeriods.parse_raw(data)
            return data
        except IOError as e:
            warning(f'No snapshot {self.filename} found')
            raise e
        except ValidationError as e:
            error(f'Cannot parse snapshot data')
            raise e

    def store(self, data: BobStatsDataForTwoPeriods):
        info(f'New bobstat data stamped as {data.timestamp} received')

        self._dump(data)
        
        self.record_sucess(data.timestamp)

    def load(self):
        ts_checkpoint = time()

        zero = Decimal(0)

        empty_period = BobStatsPeriodData(
            timestamp=0,
            totalSupply=zero,
            collaterisedCirculatedSupply=zero,
            volumeUSD=zero,
            holders=0
        )
        empty_response = BobStatsDataForTwoPeriods(
            timestamp=int(ts_checkpoint),
            current=empty_period,
            previous=empty_period
        )

        try:
            data = self._load()
            data.timestamp=int(ts_checkpoint)
        except:
            return empty_response

        return data
