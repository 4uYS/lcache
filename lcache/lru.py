"""
LRU 缓存实现。
"""

from __future__ import annotations

import time
import threading
from collections import OrderedDict
from typing import Any, Callable


class LRUCache:
    """LRU（最近最少使用）缓存。

    特性：
        - 固定容量，超出时淘汰最久未使用的条目
        - 可选 TTL 过期
        - 线程安全

    典型用法：
        cache = LRUCache(maxsize=128, ttl=300)
        cache.set("key", "value")
        value = cache.get("key")
    """

    def __init__(
        self,
        maxsize: int = 128,
        ttl: float | None = None,
    ) -> None:
        """初始化 LRU 缓存。

        Args:
            maxsize: 最大缓存条目数。
            ttl: 条目生存时间（秒），None 表示永不过期。
        """
        self._maxsize = max(1, maxsize)
        self._ttl = ttl
        self._data: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    @property
    def maxsize(self) -> int:
        """最大缓存容量。"""
        return self._maxsize

    @property
    def ttl(self) -> float | None:
        """TTL 设置。"""
        return self._ttl

    def __len__(self) -> int:
        with self._lock:
            self._cleanup_expired()
            return len(self._data)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值。

        Args:
            key: 缓存键。
            default: 键不存在时的默认值。

        Returns:
            缓存值或默认值。
        """
        with self._lock:
            self._cleanup_expired()
            if key not in self._data:
                return default
            value, timestamp = self._data.pop(key)
            if self._ttl is not None and (time.time() - timestamp) > self._ttl:
                return default
            self._data[key] = (value, timestamp)
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存值。

        Args:
            key: 缓存键。
            value: 缓存值。
        """
        with self._lock:
            self._cleanup_expired()
            if key in self._data:
                self._data.pop(key)
            elif len(self._data) >= self._maxsize:
                self._data.popitem(last=False)  # 淘汰最久未使用的
            self._data[key] = (value, time.time())

    def delete(self, key: str) -> bool:
        """删除缓存条目。

        Args:
            key: 缓存键。

        Returns:
            是否成功删除。
        """
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存。"""
        with self._lock:
            self._data.clear()

    def keys(self) -> list[str]:
        """返回所有缓存键。"""
        with self._lock:
            self._cleanup_expired()
            return list(self._data.keys())

    def _cleanup_expired(self) -> None:
        """清理过期条目（需在持有锁时调用）。"""
        if self._ttl is None:
            return
        now = time.time()
        expired_keys = [
            key for key, (_, ts) in self._data.items()
            if (now - ts) > self._ttl
        ]
        for key in expired_keys:
            del self._data[key]

    def __repr__(self) -> str:
        return f"LRUCache(maxsize={self._maxsize}, ttl={self._ttl}, size={len(self)})"
