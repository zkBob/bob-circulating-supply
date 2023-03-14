from decimal import Decimal
from typing import Any, Callable

from time import sleep

from functools import cache

from web3 import Web3
from web3.eth import Contract

from .settings import Settings
from .logging import info, error
from .abi import ABI, get_abi

__settings = Settings.get()

def make_web3_call(func: Callable, *args, **kwargs) -> Any:
    attempts = 0
    while attempts < __settings.web3_retry_attemtps:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error(f'Not able to get data')
        attempts += 1
        info(f'Repeat attempt in {__settings.web3_retry_delay} seconds')
        sleep(__settings.web3_retry_delay)
    raise e

#TODO make the class cachable for the same chain and token if different 
#     objects of the class are created 
class ERC20Token():
    contract: Contract

    def __init__(self, w3: Web3, address: str):
        self.contract = w3.eth.contract(abi = get_abi(ABI.ERC20), address = address)

    @cache
    def decimals(self) -> int:
        info(f'Getting decimals for {self.contract.address}')
        retval = make_web3_call(self.contract.functions.decimals().call)
        info(f'Decimals {retval}')
        return retval

    def totalSupply(self, normalize = True) -> Decimal:
        retval = make_web3_call(self.contract.functions.totalSupply().call)
        if normalize:
            denominator_power = self.decimals()
            retval = Decimal(retval / 10 ** denominator_power)
        else:
            retval = Decimal(retval)
        info(f'totalSupply on {self.contract.web3.provider.endpoint_uri} is {retval}')
        return retval

