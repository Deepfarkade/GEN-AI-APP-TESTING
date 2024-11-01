from redis import asyncio as aioredis
from backend.core.config import settings
import logging
import os
from typing import Optional, Any
import ssl
import urllib.parse
import socket

class RedisClient:
    redis: Optional[aioredis.Redis] = None

    @classmethod
    async def connect_redis(cls) -> None:
        """Connect to Redis/Azure Cache for Redis"""
        try:
            if cls.redis is None:
                logging.info("Connecting to Redis...")
                
                # Get Redis connection details
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', '6380'))  # Azure Redis SSL port
                redis_password = os.getenv('REDIS_PASSWORD', '')

                # Check if redis_password is not empty
                if not redis_password:
                    raise ValueError("Redis password is not configured")
                
                if not all([redis_host, redis_port, redis_password]):
                    raise ValueError("Redis connection details not properly configured")

                # Construct connection URL for Azure Redis (using rediss:// for SSL)
                connection_url = f"rediss://:{urllib.parse.quote(str(redis_password))}@{redis_host}:{redis_port}"

                # Create Redis client without SSL configuration for testing
                cls.redis = aioredis.from_url(
                    connection_url,
                    decode_responses=True,
                    socket_timeout=30.0,
                    socket_connect_timeout=30.0,
                    socket_keepalive=True,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    max_connections=10
                )
                
                # Test connection with increased timeout
                await cls.redis.ping()
                logging.info("Successfully connected to Redis")

        except Exception as e:
            logging.error(f"Redis connection error: {str(e)}")
            if cls.redis:
                await cls.close_redis()
            raise

    @classmethod
    async def close_redis(cls) -> None:
        """Close Redis connection"""
        if cls.redis:
            await cls.redis.close()
            cls.redis = None
            logging.info("Redis connection closed")

    @classmethod
    async def get_cache(cls, key: str) -> Optional[str]:
        """Get value from cache"""
        if cls.redis:
            try:
                return await cls.redis.get(key)
            except Exception as e:
                logging.error(f"Redis get error: {str(e)}")
                return None
        return None

    @classmethod
    async def set_cache(cls, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if cls.redis:
            try:
                if ttl is None:
                    ttl = settings.REDIS_TTL
                await cls.redis.set(key, value, ex=ttl)
                return True
            except Exception as e:
                logging.error(f"Redis set error: {str(e)}")
                return False
        return False

    @classmethod
    async def delete_cache(cls, key: str) -> bool:
        """Delete value from cache"""
        if cls.redis:
            try:
                await cls.redis.delete(key)
                return True
            except Exception as e:
                logging.error(f"Redis delete error: {str(e)}")
                return False
        return False

    @classmethod
    async def ping(cls) -> bool:
        """Test Redis connection"""
        try:
            if cls.redis:
                await cls.redis.ping()
                return True
            return False
        except Exception:
            return False

    @classmethod
    async def clear_cache(cls) -> bool:
        """Clear all cache"""
        if cls.redis:
            try:
                await cls.redis.flushdb()
                return True
            except Exception as e:
                logging.error(f"Redis clear error: {str(e)}")
                return False
        return False
