from functools import cache 
from json import load

from enum import Enum

from .logging import info, error
from .settings import Settings

class ABI(Enum):
    ERC20 = "erc20.json"

@cache
def __abi_dir():
    return Settings.get().abi_dir

@cache
def get_abi(fname: ABI) -> dict:
    full_fname = f'{__abi_dir()}/{fname.value}'
    try:
        with open(full_fname) as f:
            abi = load(f)
    except IOError as e:
        error(f'Cannot read {full_fname}')
        raise e
    info(f'{full_fname} loaded')
    return abi
