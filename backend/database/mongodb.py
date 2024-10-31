from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings
import logging
import os
from typing import Optional

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    async def connect_db(cls) -> None:
        """Connect to MongoDB/Cosmos DB"""
        try:
            if cls.client is None:
                # Get connection string from environment or settings
                connection_string = os.getenv('MONGODB_URL', settings.MONGODB_URL)
                
                # Handle Azure Cosmos DB connection string if present
                if 'cosmos' in connection_string.lower():
                    # Add required parameters for Cosmos DB
                    if '?' not in connection_string:
                        connection_string += '?'
                    if 'retryWrites=false' not in connection_string:
                        connection_string += '&retryWrites=false'
                    if 'ssl=true' not in connection_string:
                        connection_string += '&ssl=true'

                cls.client = AsyncIOMotorClient(connection_string)
                cls.db = cls.client[settings.MONGODB_DB]
                
                # Verify connection
                await cls.client.admin.command('ping')
                logging.info("Successfully connected to MongoDB/Cosmos DB")
        except Exception as e:
            logging.error(f"MongoDB connection error: {str(e)}")
            raise

    @classmethod
    async def close_db(cls) -> None:
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logging.info("MongoDB connection closed")

    @classmethod
    async def get_db(cls):
        """Get database instance"""
        if cls.db is None:
            await cls.connect_db()
        return cls.db

    @classmethod
    async def get_collection(cls, collection_name: str):
        """Get collection from database"""
        if cls.db is None:
            await cls.connect_db()
        return cls.db[collection_name]

    @classmethod
    def is_connected(cls) -> bool:
        """Check if connected to database"""
        return cls.client is not None and cls.db is not None

    @classmethod
    async def ping(cls) -> bool:
        """Test database connection"""
        try:
            if cls.client:
                await cls.client.admin.command('ping')
                return True
            return False
        except Exception:
            return False