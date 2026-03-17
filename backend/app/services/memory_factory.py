"""
Memory Provider工厂
根据配置返回对应的记忆提供者实例
"""

import threading
from typing import Optional

from ..config import Config
from ..utils.logger import get_logger
from .memory_provider import MemoryProvider

logger = get_logger('mirofish.memory_factory')

_provider_instance: Optional[MemoryProvider] = None
_lock = threading.Lock()


def get_memory_provider() -> MemoryProvider:
    """
    获取配置的记忆提供者实例（单例，线程安全）

    根据 Config.MEMORY_PROVIDER 返回:
    - 'zep': ZepProvider (默认)
    - 'mem0': Mem0Provider
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    with _lock:
        # Double-check after acquiring lock
        if _provider_instance is not None:
            return _provider_instance

        provider_name = Config.MEMORY_PROVIDER

        if provider_name == 'mem0':
            from .mem0_provider import Mem0Provider
            _provider_instance = Mem0Provider()
            logger.info("Memory provider initialized: Mem0")
        else:
            from .zep_provider import ZepProvider
            _provider_instance = ZepProvider()
            logger.info("Memory provider initialized: Zep")

    return _provider_instance


def reset_provider():
    """Reset the singleton (useful for testing)"""
    global _provider_instance
    with _lock:
        _provider_instance = None
