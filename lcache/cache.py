"""
缓存装饰器实现。
"""

from __future__ import annotations

import functools
import hashlib
import json
from typing import Any, Callable

from lcache.lru import LRUCache
from lcache.disk import DiskCache


def _make_key(args: tuple, kwargs: dict) -> str:
    """根据函数参数生成缓存键。"""
    key_data = {
        "args": args,
        "kwargs": dict(sorted(kwargs.items())),
    }
    raw = json.dumps(key_data, default=str, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class Cache:
    """缓存管理器，组合 LRU 内存缓存和磁盘缓存。

    典型用法：
        cache = Cache(maxsize=128, ttl=300, persist_dir="/tmp/cache")
        cache.set("key", value)
        value = cache.get("key")
    """

    def __init__(
        self,
        maxsize: int = 128,
        ttl: float | None = None,
        persist_dir: str | None = None,
    ) -> None:
        """初始化缓存管理器。

        Args:
            maxsize: LRU 缓存最大容量。
            ttl: 条目生存时间（秒）。
            persist_dir: 磁盘持久化目录，None 表示不持久化。
        """
        self._lru = LRUCache(maxsize=maxsize, ttl=ttl)
        self._disk = DiskCache(directory=persist_dir, ttl=ttl) if persist_dir else None

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值（先查内存，再查磁盘）。"""
        value = self._lru.get(key)
        if value is not None:
            return value
        if self._disk:
            value = self._disk.get(key)
            if value is not None:
                self._lru.set(key, value)  # 回填内存
            return value
        return default

    def set(self, key: str, value: Any) -> None:
        """设置缓存值（同时写入内存和磁盘）。"""
        self._lru.set(key, value)
        if self._disk:
            self._disk.set(key, value)

    def delete(self, key: str) -> bool:
        """删除缓存条目。"""
        result = self._lru.delete(key)
        if self._disk:
            result = self._disk.delete(key) or result
        return result

    def clear(self) -> None:
        """清空所有缓存。"""
        self._lru.clear()
        if self._disk:
            self._disk.clear()

    @property
    def lru(self) -> LRUCache:
        """底层 LRU 缓存。"""
        return self._lru

    @property
    def disk(self) -> DiskCache | None:
        """底层磁盘缓存。"""
        return self._disk


def cached(
    func: Callable | None = None,
    *,
    ttl: float | None = None,
    maxsize: int = 128,
    persist_dir: str | None = None,
    key_prefix: str = "",
) -> Callable:
    """缓存装饰器。

    自动缓存函数返回值，支持 LRU 淘汰、TTL 过期、磁盘持久化。

    Args:
        func: 被装饰的函数（自动传入）。
        ttl: 缓存生存时间（秒）。
        maxsize: 最大缓存条目数。
        persist_dir: 磁盘持久化目录。
        key_prefix: 缓存键前缀，用于区分不同函数。

    典型用法：
        @cached(ttl=300, maxsize=64)
        def expensive_computation(x, y):
            return x ** y

        @cached(persist_dir="/tmp/cache", ttl=3600)
        def fetch_data(url):
            return requests.get(url).json()
    """
    cache = Cache(maxsize=maxsize, ttl=ttl, persist_dir=persist_dir)

    def decorator(fn: Callable) -> Callable:
        prefix = key_prefix or f"{fn.__module__}.{fn.__qualname__}"

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = f"{prefix}:{_make_key(args, kwargs)}"
            value = cache.get(key)
            if value is not None:
                return value
            value = fn(*args, **kwargs)
            cache.set(key, value)
            return value

        wrapper.cache = cache  # type: ignore
        wrapper.cache_clear = cache.clear  # type: ignore
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
