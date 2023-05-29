from functools import cache
from time import time
from json import dump, load
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

    def _dump(self, data: BobStatsDataForTwoPeriodsToFeed):
        with open(self.filename, 'w') as json_file:
            dump(data.dict(exclude_unset=True), json_file, cls=CustomJSONEncoder)

    def _load_json_as_dict(self) -> dict:
        try:
            with open(self.filename, 'r') as json_file:
                data = load(json_file)
            return data
        except IOError as e:
            warning(f'No snapshot {self.filename} found')
            raise e

    def _loadMainStat(self) -> BobStatsDataForTwoPeriodsAPI:
        data = self._load_json_as_dict()
        try:
            return BobStatsDataForTwoPeriodsAPI.parse_obj(data)
        except ValidationError as e:
            error(f'Cannot parse snapshot data')
            raise e

    def _loadYieldStat(self) -> GainStatsTimeStamped:
        data = self._load_json_as_dict()
        info(f"{type(data)}")
        try:
            out = data['current']['gain']
            out['timestamp'] = data['current']['timestamp']
            return GainStatsTimeStamped.parse_obj(out)
        except ValidationError as e:
            error(f'Cannot parse snapshot data')
            raise e

    def _load(self) -> BobStatsDataForTwoPeriodsAPI:
        return self._loadMainStat()

    def store(self, data: BobStatsDataForTwoPeriodsToFeed):
        info(f'New bobstat data stamped as {data.timestamp} received')

        self._dump(data)
        
        self.record_sucess(data.timestamp)

    def loadMainStat(self) -> BobStatsDataForTwoPeriodsAPI:
        ts_checkpoint = int(time())

        zero = Decimal(0)

        empty_period = BobStatsPeriodDataAPI(
            timestamp=0,
            totalSupply=zero,
            collaterisedCirculatedSupply=zero,
            volumeUSD=zero,
            holders=0
        )
        empty_response = BobStatsDataForTwoPeriodsAPI(
            timestamp=ts_checkpoint,
            current=empty_period,
            previous=empty_period
        )

        try:
            data = self._loadMainStat()
            data.timestamp=ts_checkpoint
        except:
            return empty_response

        return data

    def loadYieldStat(self) -> GainStatsAPI:
        ts_checkpoint = int(time())

        empty_response = GainStatsAPI(**{
            'timestamp': ts_checkpoint,
            'yield': GainStatsTimeStamped(
                timestamp = 0,
                fees = []
            )
        })

        try:
            data = GainStatsAPI(**{
                'timestamp': ts_checkpoint,
                'yield': self._loadYieldStat()
            })
        except:
            return empty_response

        return data
