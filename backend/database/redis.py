from redis import asyncio as aioredis
from core.config import settings
import logging
import os
from typing import Optional, Any

class RedisClient:
    redis: Optional[aioredis.Redis] = None

    @classmethod
    async def connect_redis(cls) -> None:
        """Connect to Redis/Azure Cache for Redis"""
        try:
            if cls.redis is None:
                # Get connection string from environment or settings
                redis_url = os.getenv('REDIS_URL', settings.REDIS_URL)
                
                # Handle Azure Redis connection string if present
                is_azure_redis = 'rediscache.windows.net' in redis_url

                connection_kwargs = {
                    "encoding": "utf-8",
                    "decode_responses": True
                }

                if is_azure_redis:
                    # For Azure Redis, we need to handle the connection differently
                    connection_kwargs.update({
                        "ssl_cert_reqs": None,  # Disable certificate verification
                        "connection_timeout": 30,
                        "retry_on_timeout": True
                    })

                cls.redis = await aioredis.from_url(
                    redis_url,
                    **connection_kwargs
                )
                
                # Verify connection
                await cls.redis.ping()
                logging.info("Successfully connected to Redis")
        except Exception as e:
            logging.error(f"Redis connection error: {str(e)}")
            cls.redis = None  # Don't raise error, allow app to work without caching

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