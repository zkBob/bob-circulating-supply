from utils.settings import Settings

_settings = Settings().get()

def verify_chain(chain: str) -> bool:
    return chain in _settings.bobvault_chains