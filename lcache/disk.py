"""
磁盘持久化缓存实现。
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import time
from pathlib import Path
from typing import Any


class DiskCache:
    """磁盘持久化缓存。

    将缓存数据序列化后存储到文件系统，支持 TTL 过期。

    典型用法：
        cache = DiskCache(directory="/tmp/lcache", ttl=3600)
        cache.set("key", {"data": [1, 2, 3]})
        value = cache.get("key")
    """

    def __init__(
        self,
        directory: str | Path = ".lcache",
        ttl: float | None = None,
        serializer: str = "pickle",
    ) -> None:
        """初始化磁盘缓存。

        Args:
            directory: 缓存文件存储目录。
            ttl: 条目生存时间（秒），None 表示永不过期。
            serializer: 序列化方式 'pickle' 或 'json'。
        """
        self._directory = Path(directory)
        self._ttl = ttl
        self._serializer = serializer
        self._directory.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        """缓存目录路径。"""
        return self._directory

    @property
    def ttl(self) -> float | None:
        """TTL 设置。"""
        return self._ttl

    def _key_to_path(self, key: str) -> Path:
        """将键转换为文件路径。"""
        hashed = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self._directory / f"{hashed}.cache"

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值。

        Args:
            key: 缓存键。
            default: 键不存在或过期时的默认值。

        Returns:
            缓存值或默认值。
        """
        path = self._key_to_path(key)
        if not path.exists():
            return default

        try:
            with open(path, "rb") as f:
                data = pickle.load(f)

            value, timestamp = data["value"], data["timestamp"]

            if self._ttl is not None and (time.time() - timestamp) > self._ttl:
                path.unlink(missing_ok=True)
                return default

            return value
        except Exception:
            return default

    def set(self, key: str, value: Any) -> None:
        """设置缓存值。

        Args:
            key: 缓存键。
            value: 缓存值（需可 pickle 序列化）。
        """
        path = self._key_to_path(key)
        data = {
            "key": key,
            "value": value,
            "timestamp": time.time(),
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def delete(self, key: str) -> bool:
        """删除缓存条目。"""
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        """清空所有缓存。

        Returns:
            删除的文件数。
        """
        count = 0
        for f in self._directory.glob("*.cache"):
            f.unlink()
            count += 1
        return count

    def cleanup(self) -> int:
        """清理过期条目。

        Returns:
            清理的条目数。
        """
        if self._ttl is None:
            return 0

        count = 0
        now = time.time()
        for f in self._directory.glob("*.cache"):
            try:
                with open(f, "rb") as fh:
                    data = pickle.load(fh)
                if (now - data["timestamp"]) > self._ttl:
                    f.unlink()
                    count += 1
            except Exception:
                f.unlink(missing_ok=True)
                count += 1
        return count

    def __repr__(self) -> str:
        count = len(list(self._directory.glob("*.cache")))
        return f"DiskCache(dir={self._directory}, ttl={self._ttl}, entries={count})"
