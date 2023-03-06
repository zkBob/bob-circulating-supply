from functools import cache

from pydantic import BaseSettings
from pydantic.utils import GetterDict

from typing import Any, List

from .logging import info

__secrets__ = {
    'upload_token': 'default'
}

__comma_separated_params__ = ['rpcs' , 'bobvault_chains']

class Settings(BaseSettings):
    rpcs: List[str] = ['https://polygon-rpc.com', 'https://mainnet.optimism.io']
    bob_token: str = '0xB0B195aEFA3650A6908f15CdaC7D92F8a5791B0B'
    update_interval: int = 3600
    port: int = 8080
    upload_token: str = __secrets__['upload_token']
    abi_dir: str = '.'
    snapshot_dir: str = '.'
    coingecko_snapshot_file_template: str = 'bobvault-{chain}-coingecko-data.json'
    bobstat_snapshot_file: str = 'bobstat-data.json'
    bobvault_chains: List[str] = ['polygon']
    web3_retry_attemtps: int = 2
    web3_retry_delay: int = 5

    @classmethod
    @cache
    def get(cls):
        settings = cls()

        for (key, value) in settings:
            if (key in __secrets__) and (value != __secrets__[key]):
                info(f'{key.upper()} is set')
            else:
                info(f'{key.upper()} = {value}')

        return settings

    class Config:
        env_file = ".env"
        getter_dict = GetterDict

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name in __comma_separated_params__:
                return [x for x in raw_val.split(',')]
            return cls.json_loads(raw_val)