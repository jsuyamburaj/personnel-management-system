from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None
    
    async def connect(self):
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        self.db = self.client[settings.database_name]
        logger.info(f"Connected to database: {settings.database_name}")
        
        # Create indexes
        await self.db["users"].create_index("email", unique=True)
        await self.db["activity_logs"].create_index("timestamp")
        await self.db["notifications"].create_index("user_email")
        
    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Database connection closed")
    
    # ✅ THIS IS THE MAIN FIX
    def __getattr__(self, name):
        return self.db[name]

    # (optional – keep if you want)
    def get_collection(self, name):
        return self.db[name]


db = Database()

# (optional helper – safe to keep)
def get_collection(name):
    return db.db[name]