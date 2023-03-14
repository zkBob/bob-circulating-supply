from functools import cache
from typing import Dict
from json import dump

from pydantic import ValidationError

from .models import BobVaultDataModel, ListOfPairsOut, PairOutDataModel, \
    TickerBaseModel, TickerOutDataModel, ListOfTickersOut, PairOrderbookModel, \
    OrderbookOut, PairTradesModel

from utils.logging import info, warning, error
from utils.health import Health, HealthRegistry, WorkerHealthModelOut
from utils.settings import Settings
from utils.misc import CustomJSONEncoder, MINTIMESTAMP, MAXTIMESTAMP, Named

_settings = Settings.get()

class BobVault(Health):

    def __init__(self, chain: str):
        self.filename = f'{_settings.snapshot_dir}/' + \
                        _settings.coingecko_snapshot_file_template.format(chain=chain)
        info(f'Checking for available bobvault data for {chain}')
        self._name = f'{type(self).__name__}/{chain}'
        self.initialize_healthdata()

    def _dump(self, data: BobVaultDataModel):
        with open(self.filename, 'w') as json_file:
            dump(data.dict(), json_file, cls=CustomJSONEncoder)

    def _load(self) -> BobVaultDataModel:
        try:
            with open(self.filename, 'r') as json_file:
                data = ''.join(json_file.readlines())
                data = BobVaultDataModel.parse_raw(data)
            return data
        except IOError as e:
            warning(f'No snapshot {self.filename} found')
            raise e
        except ValidationError as e:
            error(f'Cannot parse snapshot data')
            raise e

    def store(self, data: BobVaultDataModel):
        data_ts = data["timestamp"]
        pairs = data.pairs()
        if len(pairs) > 0:
            delimiter = '/'
            info(f'Coingecko data stamped as {data_ts} contains {delimiter.join(pairs)}')
        else:
            warning(f'No pairs found in data stamped as {data_ts}')

        self._dump(data)
        
        self.record_sucess(data_ts)

    def pairs(self) -> ListOfPairsOut:
        info(f'Request to get pairs for {self.name()} received')
        ret = ListOfPairsOut()
        try:
            data=self._load()
        except:
            return ret
        
        pairs = data.pairs()
        for pair in pairs:
            ret.append(PairOutDataModel(
                ticker_id = pair,
                base = data[pair].base_currency,
                target = data[pair].target_currency,
                pool_id = data[pair].pool_id
            ))
        return ret

    def tickers(self) -> ListOfTickersOut:
        info(f'Request to get tickers for {self.name()} received')
        ret = ListOfTickersOut()
        try:
            data=self._load()
        except:
            return ret
        
        pairs = data.pairs()
        for pair in pairs:
            ticker = TickerBaseModel.parse_obj(data[pair]).dict()
            ticker.update({
                'ticker_id': pair
            })
            ret.append(TickerOutDataModel.parse_obj(ticker))
        return ret

    def orderbook(self, ticker_id: str) -> OrderbookOut:
        info(f'Request to get orderbook for {ticker_id} in {self.name()} received')
        try:
            data=self._load()
        except:
            return OrderbookOut()

        if not ticker_id in data.pairs():
            return OrderbookOut()
        
        ob = PairOrderbookModel.parse_obj(data[ticker_id].orderbook).dict()
        ob.update({
            'ticker_id': ticker_id,
            'timestamp': data[ticker_id].timestamp
        })
        return OrderbookOut.parse_obj(ob)

    def historical_trades(self, ticker_id: str, 
                                type: str,
                                limit: int,
                                start_time: int, 
                                end_time: int) -> PairTradesModel:
        info(f'Request to get {type} trades for {ticker_id} in {self.name()} received')
        try:
            data=self._load()
        except:
            return PairTradesModel()

        if not ticker_id in data.pairs():
            warning(f'Ticker {ticker_id} not found')
            return PairTradesModel()

        tmp = getattr(data[ticker_id].trades, type, None)
        if not tmp:
            info(f'no trades for "{type}" found')
            return PairTradesModel()
        else:
            if limit == 0 and start_time == MINTIMESTAMP and end_time == MAXTIMESTAMP:
                response = { type: tmp }
            elif limit != 0 and start_time == MINTIMESTAMP and end_time == MAXTIMESTAMP:
                response = { type: tmp[-limit:] }
            else:
                response = { type: [] }
                count = 0
                for trade in tmp:
                    if trade.trade_timestamp >= start_time and trade.trade_timestamp <= end_time:
                        response[type].append(trade.dict())
                        count += 1
                        if count == limit:
                            break
            return PairTradesModel.parse_obj(response)

@cache
class BobVaults(Named):

    def __init__(self):
        self.vaults = {}
        for c in _settings.bobvault_chains:
            self.vaults[c] = BobVault(c)

        HealthRegistry().append(self)

    def healthdata_for_publishing(self, curtime: int) -> Dict[str, WorkerHealthModelOut]:
        ret = {}
        info(f'Preparing {self.name()} healthdata for publishing')
        for c in self.vaults:
            ret.update({
                c: self.vaults[c].healthdata_for_publishing(curtime)
            })
        return ret

    def store(self, chain: str, data: BobVaultDataModel):
        info(f'Received new coingecko data for bobvault in {chain}')
        self.vaults[chain].store(data)
 
    def pairs(self, chain: str) -> ListOfPairsOut:
        return self.vaults[chain].pairs()

    def tickers(self, chain: str) -> ListOfTickersOut:
        return self.vaults[chain].tickers()

    def orderbook(self, chain: str, ticker_id: str) -> OrderbookOut:
        return self.vaults[chain].orderbook(ticker_id)

    def historical_trades(self, chain: str, 
                                ticker_id: str, 
                                type: str,
                                limit: int,
                                start_time: int, 
                                end_time: int) -> PairTradesModel:
        return self.vaults[chain].historical_trades(ticker_id, type, limit, start_time, end_time)
