from decimal import Decimal
from typing import Optional, List

from pydantic import Extra, BaseModel, Field

from utils.models import TimestampedBaseModel

class OneTokenAcc(BaseModel):
    symbol: str
    amount: Decimal

GainSet = List[OneTokenAcc]

class GainStats(BaseModel):
    fees: GainSet
    interest: Optional[GainSet]

    def is_empty(self) -> bool:
        retval = True
        if not self.is_fees_empty():
            retval = False
        if not self.is_interest_empty():
            retval = False
        return retval
    
    def is_fees_empty(self) -> bool:
        retval = True
        if self.fees and len(self.fees) > 0:
            retval = False
        return retval

    def is_interest_empty(self) -> bool:
        retval = True
        if self.interest and len(self.interest) > 0:
            retval = False
        return retval

    def adjust(self, source):
        def adjust_gain_set(fees_source: GainSet, fees_target: GainSet):
            for f in fees_source:
                found = False
                for target in fees_target:
                    if target.symbol == f.symbol:
                        found = True
                        target.amount += f.amount
                        break
                if not found:
                    fees_target.append(f)
            
        if not source.is_fees_empty():
            if not self.fees:
                self.fees = []
            adjust_gain_set(source.fees, self.fees)
        if not source.is_interest_empty():
            if not self.interest:
                self.interest = []
            adjust_gain_set(source.interest, self.interest)

class GainStatsTimeStamped(GainStats, extra=Extra.forbid):
    timestamp: int

class GainStatsAPI(TimestampedBaseModel, extra=Extra.forbid):
    timestamp: int
    gain: GainStatsTimeStamped = Field(..., alias='yield') 

class BobStatsPeriodDataAPI(TimestampedBaseModel):
    totalSupply: Decimal
    collaterisedCirculatedSupply: Decimal
    volumeUSD: Decimal
    holders: int

class BobStatsPeriodDataToFeed(BobStatsPeriodDataAPI, extra=Extra.forbid):
    gain: Optional[GainStats]

class BobStatsDataForTwoPeriodsAPI(TimestampedBaseModel, extra=Extra.forbid):
    current: BobStatsPeriodDataAPI
    previous: BobStatsPeriodDataAPI

class BobStatsDataForTwoPeriodsToFeed(TimestampedBaseModel, extra=Extra.forbid):
    current: BobStatsPeriodDataToFeed
    previous: BobStatsPeriodDataToFeed

