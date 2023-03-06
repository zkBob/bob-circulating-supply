from functools import cache

from decimal import Decimal

from time import time

from web3 import Web3, HTTPProvider

from utils.settings import Settings
from utils.health import Health, HealthRegistry
from utils.web3 import ERC20Token
from utils.logging import info, error
from utils.misc import format_timestamp

_settings = Settings.get()

@cache
class TotalSupply(Health):
    @property
    def value(self):
        try:
            return self._value
        except:
            return Decimal(0)

    def __init__(self):
        self.initialize_healthdata()
        HealthRegistry().append(self)
        
        self._tokens = []
        for u in _settings.rpcs:
            w3 = Web3(HTTPProvider(u))
            self._tokens.append(ERC20Token(w3, _settings.bob_token))

    def get_through_tokens(self):
        total = Decimal(0)
        collected_successfully = True
        for t in self._tokens:
            try: 
                total += t.totalSupply()
            except:
                error(f'Cannot get BOB totalSupply on {t.contract.web3.provider.endpoint_uri}')
                collected_successfully = False
                break
        if collected_successfully:
            self._value = total
            self.record_sucess(int(time()))
            info(f'Token total supply is {total} in {format_timestamp()}')
        else:
            self.record_error()