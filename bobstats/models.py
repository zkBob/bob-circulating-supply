from decimal import Decimal

from pydantic import Extra

from utils.models import TimestampedBaseModel

class BobStatsPeriodData(TimestampedBaseModel, extra=Extra.forbid):
    totalSupply: Decimal
    collaterisedCirculatedSupply: Decimal
    volumeUSD: Decimal
    holders: int

class BobStatsDataForTwoPeriods(TimestampedBaseModel, extra=Extra.forbid):
    current: BobStatsPeriodData
    previous: BobStatsPeriodData

