"""
lcache — 轻量级缓存装饰器库。

特性：
    - LRU 内存缓存
    - 磁盘持久化
    - TTL 过期控制
    - 装饰器模式，一行启用缓存

典型用法：
    from lcache import cached

    @cached(ttl=300, maxsize=128)
    def fetch_user(user_id: int) -> dict:
        return requests.get(f"/api/users/{user_id}").json()
"""

from lcache.cache import cached, Cache
from lcache.lru import LRUCache
from lcache.disk import DiskCache

__version__ = "0.7.1"

__all__ = [
    "cached",
    "Cache",
    "LRUCache",
    "DiskCache",
]
