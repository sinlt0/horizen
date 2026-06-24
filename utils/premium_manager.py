import time
import uuid
from datetime import datetime, timedelta
from utils.database import DatabaseManager

class PremiumManager:

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.premium_collection = 'guild_premium'
        self.keys_collection = 'premium_keys'
        self.durations = {'7d': timedelta(days=7), '2week': timedelta(weeks=2), '1month': timedelta(days=30), '1y': timedelta(days=365), '2y': timedelta(days=730), 'lifetime': None}

    async def get_premium_status(self, guild_id: int):
        doc = await self.db_manager.find_one(self.premium_collection, {'_id': guild_id})
        if not doc:
            return (False, None)
        expiry = doc.get('expiry')
        if expiry is None:
            return (True, None)
        if time.time() > expiry:
            await self.db_manager.delete_one(self.premium_collection, {'_id': guild_id})
            return (False, None)
        return (True, expiry)

    async def add_premium(self, guild_id: int, duration_key: str):
        delta = self.durations.get(duration_key)
        expiry = None
        if delta:
            current_status = await self.get_premium_status(guild_id)
            base_time = current_status[1] if current_status[0] and current_status[1] else time.time()
            expiry = base_time + delta.total_seconds()
        await self.db_manager.update_one(self.premium_collection, {'_id': guild_id}, {'expiry': expiry}, upsert=True)
        return expiry

    async def generate_key(self, duration_key: str):
        key = f'HORIZEN-{uuid.uuid4().hex[:12].upper()}'
        await self.db_manager.insert_one(self.keys_collection, {'key': key, 'duration': duration_key, 'created_at': time.time()})
        return key

    async def claim_key(self, guild_id: int, key_str: str):
        key_doc = await self.db_manager.find_one(self.keys_collection, {'key': key_str})
        if not key_doc:
            return (False, 'Invalid Key')
        duration_key = key_doc['duration']
        expiry = await self.add_premium(guild_id, duration_key)
        await self.db_manager.delete_one(self.keys_collection, {'key': key_str})
        return (True, expiry)