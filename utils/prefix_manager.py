from utils.database import DatabaseManager

class PrefixManager:

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.guild_prefixes_collection = 'guild_prefixes'
        self.no_prefix_users_collection = 'no_prefix_users'
        self._guild_cache = {}
        self._no_prefix_cache = set()
        self._cache_initialized = False

    async def initialize_cache(self):
        try:
            no_prefix_doc = await self.db_manager.find_one(self.no_prefix_users_collection, {'_id': 'global'})
            if no_prefix_doc and 'user_ids' in no_prefix_doc:
                self._no_prefix_cache = set(no_prefix_doc['user_ids'])
            self._cache_initialized = True
        except Exception as e:
            print(f'Failed to initialize prefix cache: {e}')

    async def _get_guild_data(self, guild_id: int):
        if guild_id in self._guild_cache:
            return self._guild_cache[guild_id]
        try:
            doc = await self.db_manager.find_one(self.guild_prefixes_collection, {'_id': guild_id})
            if doc:
                data = {'prefix': doc.get('prefix', self.db_manager.config.DEFAULT_PREFIX), 'enabled': doc.get('use_guild_prefix', True), 'categories': doc.get('category_prefixes', {})}
            else:
                data = {'prefix': self.db_manager.config.DEFAULT_PREFIX, 'enabled': True, 'categories': {}}
            self._guild_cache[guild_id] = data
            return data
        except Exception:
            return {'prefix': self.db_manager.config.DEFAULT_PREFIX, 'enabled': True, 'categories': {}}

    async def get_prefix(self, guild_id: int) -> str:
        data = await self._get_guild_data(guild_id)
        return data['prefix'] if data['enabled'] else ''

    async def set_prefix(self, guild_id: int, prefix: str):
        await self.db_manager.update_one(self.guild_prefixes_collection, {'_id': guild_id}, {'$set': {'prefix': prefix}}, upsert=True)
        data = await self._get_guild_data(guild_id)
        data['prefix'] = prefix
        self._guild_cache[guild_id] = data

    async def toggle_prefix(self, guild_id: int, enable: bool=None):
        data = await self._get_guild_data(guild_id)
        new_state = not data['enabled'] if enable is None else enable
        await self.db_manager.update_one(self.guild_prefixes_collection, {'_id': guild_id}, {'$set': {'use_guild_prefix': new_state}}, upsert=True)
        data['enabled'] = new_state
        self._guild_cache[guild_id] = data
        return new_state

    async def is_prefix_enabled(self, guild_id: int) -> bool:
        data = await self._get_guild_data(guild_id)
        return data['enabled']

    async def set_category_prefix(self, guild_id: int, category: str, prefix: str):
        await self.db_manager.update_one(self.guild_prefixes_collection, {'_id': guild_id}, {'$set': {f'category_prefixes.{category}': prefix}}, upsert=True)
        data = await self._get_guild_data(guild_id)
        data['categories'][category] = prefix
        self._guild_cache[guild_id] = data

    async def get_category_prefix(self, guild_id: int, category: str) -> str:
        data = await self._get_guild_data(guild_id)
        return data['categories'].get(category)

    async def remove_category_prefix(self, guild_id: int, category: str):
        await self.db_manager.update_one(self.guild_prefixes_collection, {'_id': guild_id}, {'$unset': {f'category_prefixes.{category}': ''}})
        data = await self._get_guild_data(guild_id)
        if category in data['categories']:
            del data['categories'][category]
            self._guild_cache[guild_id] = data

    async def get_all_category_prefixes(self, guild_id: int) -> list:
        data = await self._get_guild_data(guild_id)
        return list(data['categories'].values())

    async def get_category_for_prefix(self, guild_id: int, prefix: str) -> str:
        data = await self._get_guild_data(guild_id)
        for category, cat_prefix in data['categories'].items():
            if cat_prefix == prefix:
                return category
        return None

    async def add_no_prefix_user(self, user_id: int):
        await self.db_manager.update_one(self.no_prefix_users_collection, {'_id': 'global'}, {'$addToSet': {'user_ids': user_id}}, upsert=True)
        self._no_prefix_cache.add(user_id)

    async def remove_no_prefix_user(self, user_id: int):
        await self.db_manager.update_one(self.no_prefix_users_collection, {'_id': 'global'}, {'$pull': {'user_ids': user_id}})
        if user_id in self._no_prefix_cache:
            self._no_prefix_cache.remove(user_id)

    async def is_no_prefix_user(self, user_id: int) -> bool:
        if not self._cache_initialized:
            await self.initialize_cache()
        return user_id in self._no_prefix_cache

    async def get_no_prefix_users(self) -> list:
        return list(self._no_prefix_cache)