import os
import logging
import json
import random
from motor.motor_asyncio import AsyncIOMotorClient
import aiomysql
import aiosqlite
from utils.config import Config
from bson import ObjectId

logger = logging.getLogger(__name__)

class DatabaseEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

class DatabaseManager:
    def __init__(self, config: Config):
        self.config = config
        self.mongodb_clusters = {}
        self.mariadb_pool = None
        self.sqlite_conn = None
        self.primary_type = 'mongodb'
        self.guild_shards = {}
        self.assignments_collection = 'guild_assignments'

    async def initialize(self):
        await self._init_mongodb()
        await self._init_mariadb()
        await self._init_sqlite()

        if self.mongodb_clusters:
            self.primary_type = 'mongodb'
            await self._load_sharding_assignments()
        elif self.mariadb_pool is not None:
            self.primary_type = 'mariadb'
        else:
            self.primary_type = 'sqlite'

        if self.mariadb_pool is not None:
            await self._setup_sql_tables('mariadb')
        if self.sqlite_conn is not None:
            await self._setup_sql_tables('sqlite')

        logger.info(f'All database connections initialized. Primary storage: {self.primary_type}')

    async def _init_mongodb(self):
        for name, url in self.config.MONGODB_CLUSTERS.items():
            try:
                client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=2000)
                db = client[self.config.MONGODB_DB_NAME]
                await db.command('ping')
                self.mongodb_clusters[name] = {'client': client, 'db': db}
                logger.info(f"MongoDB cluster '{name}' connected")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB cluster '{name}': {e}")

    async def _load_sharding_assignments(self):
        primary = self.mongodb_clusters.get('primary')
        if not primary:
            return
        cursor = primary['db'][self.assignments_collection].find({})
        async for doc in cursor:
            self.guild_shards[doc['_id']] = doc['cluster']
        logger.info(f'Loaded {len(self.guild_shards)} guild sharding assignments')

    async def get_cluster_name(self, guild_id: int):
        if not guild_id:
            return 'primary'
        if guild_id in self.guild_shards:
            return self.guild_shards[guild_id]
        if self.primary_type == 'mongodb':
            primary = self.mongodb_clusters.get('primary')
            if primary:
                doc = await primary['db'][self.assignments_collection].find_one({'_id': guild_id})
                if doc:
                    self.guild_shards[guild_id] = doc['cluster']
                    return doc['cluster']
            return await self.assign_guild(guild_id)
        return 'primary'

    async def assign_guild(self, guild_id: int):
        all_clusters = list(self.mongodb_clusters.keys())
        shard_options = [c for c in all_clusters if c != 'primary'] or ['primary']
        assigned_cluster = random.choice(shard_options)
        if self.primary_type == 'mongodb':
            primary = self.mongodb_clusters.get('primary')
            if primary:
                await primary['db'][self.assignments_collection].update_one(
                    {'_id': guild_id}, {'$set': {'cluster': assigned_cluster}}, upsert=True
                )
        self.guild_shards[guild_id] = assigned_cluster
        logger.info(f"Assigned guild {guild_id} to cluster '{assigned_cluster}'")
        return assigned_cluster

    def get_db(self, cluster_name: str = 'primary'):
        cluster = self.mongodb_clusters.get(cluster_name) or self.mongodb_clusters.get('primary')
        return cluster['db'] if cluster else None

    def _resolve_guild_id(self, collection: str, query: dict) -> int:
        if 'guild_id' in query and isinstance(query['guild_id'], (int, str)):
            try:
                return int(query['guild_id'])
            except Exception:
                pass
        id_val = query.get('_id') or query.get('id')
        guild_level_collections = [
            'guild_prefixes', 'guild_premium', 'automod_config', 'mod_config',
            'logging_config', 'verification_config', 'voicemaster_config',
            'greetings_config', 'autorole_config', 'afk_users', 'afk_config',
            'afk_prefs', 'leveling_config', 'ticket_config', 'booster_config',
            'antinuke_config', 'suggestions_config', 'starboard_config',
            'app_configs', 'ss_checker_config', 'customization_config',
            'invite_config', 'stats_config', 'social_alerts', 'user_playlists',
            'joined_members_map', 'status_reward_config', 'status_reward_data'
        ]
        if id_val and collection in guild_level_collections:
            try:
                return int(id_val)
            except Exception:
                pass
        if isinstance(id_val, str) and ':' in id_val and collection in ['users_xp', 'booster_users', 'active_tickets_count']:
            try:
                return int(id_val.split(':')[0])
            except Exception:
                pass
        return None

    async def find_one(self, collection: str, query: dict):
        guild_id = self._resolve_guild_id(collection, query)
        if self.primary_type == 'mongodb':
            try:
                cluster_name = await self.get_cluster_name(guild_id)
                db = self.get_db(cluster_name)
                if db is not None:
                    res = await db[collection].find_one(query)
                    if res:
                        return res
            except Exception as e:
                logger.warning(f"MongoDB Find Error: {e}. Falling back to SQLite.")
        table = collection
        id_val = query.get('_id') or query.get('id') or query.get('key')
        try:
            q = f'SELECT id, data FROM {table} WHERE id = ?'
            if table == 'premium_keys' and 'key' in query:
                id_val = query['key']
                q = f'SELECT key_str, data FROM {table} WHERE key_str = ?'
            res = await self.sqlite_fetchone(q, (id_val,))
            if res:
                item = json.loads(res[1])
                if '_id' not in item:
                    item['_id'] = res[0]
                return item
        except Exception as e:
            logger.warning(f"SQLite find_one error on '{collection}': {e}")
        return None

    async def update_one(self, collection: str, query: dict, update: dict, upsert: bool = False):
        guild_id = self._resolve_guild_id(collection, query)
        mongo_success = False
        cluster_name = 'unknown'
        if self.primary_type == 'mongodb':
            try:
                cluster_name = await self.get_cluster_name(guild_id)
                db = self.get_db(cluster_name)
                if db is not None:
                    actual_update = update if any(k.startswith('$') for k in update) else {'$set': update}
                    await db[collection].update_one(query, actual_update, upsert=upsert)
                    mongo_success = True
                else:
                    logger.warning(f"MongoDB update_one: no db for cluster '{cluster_name}', falling back to SQLite.")
            except Exception as e:
                logger.error(f"MongoDB Update Failure (Cluster: {cluster_name}): {e}. Emergency Save to SQLite initiated.")

        id_val = query.get('_id') or query.get('id') or query.get('key')
        table = collection
        try:
            existing = await self.find_one(collection, query) or {}
            is_new = not bool(existing)
            if any(k.startswith('$') for k in update):
                if '$set' in update:
                    existing.update(update['$set'])
                if '$setOnInsert' in update and is_new:
                    existing.update(update['$setOnInsert'])
                if '$inc' in update:
                    for k, v in update['$inc'].items():
                        existing[k] = existing.get(k, 0) + v
                if '$push' in update:
                    for k, v in update['$push'].items():
                        if k not in existing:
                            existing[k] = []
                        if not isinstance(existing[k], list):
                            existing[k] = [existing[k]]
                        existing[k].append(v)
                if '$addToSet' in update:
                    for k, v in update['$addToSet'].items():
                        if k not in existing:
                            existing[k] = []
                        if v not in existing[k]:
                            existing[k].append(v)
                if '$pull' in update:
                    for k, v in update['$pull'].items():
                        if k in existing and v in existing[k]:
                            existing[k].remove(v)
                if '$unset' in update:
                    for k in update['$unset']:
                        if k in existing:
                            del existing[k]
            else:
                existing.update(update)
            if is_new:
                for k, v in query.items():
                    if k not in ['$or', '$and', '$not'] and k not in existing:
                        existing[k] = v
            json_data = json.dumps(existing, cls=DatabaseEncoder)
            q = f'INSERT OR REPLACE INTO {table} (id, data) VALUES (?, ?)'
            if table == 'premium_keys' and 'key' in query:
                id_val = query['key']
                q = f'INSERT OR REPLACE INTO {table} (key_str, data) VALUES (?, ?)'
            await self.sqlite_execute(q, (id_val, json_data))
            return 1
        except Exception as e:
            logger.error(f"CRITICAL: Database Failover System Failed: {e}")
            return 0

    async def insert_one(self, collection: str, document: dict):
        guild_id = self._resolve_guild_id(collection, document)
        if self.primary_type == 'mongodb':
            try:
                cluster_name = await self.get_cluster_name(guild_id)
                db = self.get_db(cluster_name)
                if db is not None:
                    result = await db[collection].insert_one(document)
                    await self.update_one(collection, {'_id': document.get('_id')}, document, upsert=True)
                    return result.inserted_id
            except Exception as e:
                logger.error(f"MongoDB Insert Error: {e}")
        query = {'_id': document.get('_id') or document.get('id')}
        return await self.update_one(collection, query, document, upsert=True)

    async def delete_one(self, collection: str, query: dict):
        guild_id = self._resolve_guild_id(collection, query)
        if self.primary_type == 'mongodb':
            try:
                cluster_name = await self.get_cluster_name(guild_id)
                db = self.get_db(cluster_name)
                if db is not None:
                    await db[collection].delete_one(query)
            except Exception as e:
                logger.error(f"MongoDB Delete Error: {e}")
        id_val = query.get('_id') or query.get('id') or query.get('key')
        try:
            q = f'DELETE FROM {collection} WHERE id = ?'
            if collection == 'premium_keys' and 'key' in query:
                id_val = query['key']
                q = f'DELETE FROM {collection} WHERE key_str = ?'
            await self.sqlite_execute(q, (id_val,))
        except Exception as e:
            logger.warning(f"SQLite delete_one error on '{collection}': {e}")
        return 1

    async def find(self, collection: str, query: dict, sort: list = None, limit: int = 0, skip: int = 0):
        guild_id = self._resolve_guild_id(collection, query)

        if self.primary_type == 'mongodb':
            try:
                if guild_id is None and not query:
                    all_results = []
                    seen_ids = set()
                    for cluster_name, cluster_data in self.mongodb_clusters.items():
                        try:
                            db = cluster_data['db']
                            cursor = db[collection].find(query)
                            if sort:
                                cursor = cursor.sort(sort)
                            if skip:
                                cursor = cursor.skip(skip)
                            if limit:
                                cursor = cursor.limit(limit)
                            docs = await cursor.to_list(length=limit or 1000)
                            for doc in docs:
                                doc_id = doc.get('_id')
                                if doc_id not in seen_ids:
                                    seen_ids.add(doc_id)
                                    all_results.append(doc)
                        except Exception as e:
                            logger.warning(f"MongoDB find fan-out error on cluster '{cluster_name}': {e}")
                    return all_results
                else:
                    cluster_name = await self.get_cluster_name(guild_id)
                    db = self.get_db(cluster_name)
                    if db is not None:
                        cursor = db[collection].find(query)
                        if sort:
                            cursor = cursor.sort(sort)
                        if skip:
                            cursor = cursor.skip(skip)
                        if limit:
                            cursor = cursor.limit(limit)
                        return await cursor.to_list(length=limit or 1000)
            except Exception as e:
                logger.warning(f"MongoDB Find Error: {e}")

        try:
            q = f'SELECT id, data FROM {collection}'
            if collection == 'premium_keys':
                q = f'SELECT key_str, data FROM {collection}'
            res = await self.sqlite_execute_all(q)
            data = []
            for r in res:
                item = json.loads(r[1])
                if '_id' not in item:
                    item['_id'] = r[0]
                data.append(item)
            filtered = []
            for item in data:
                match = True
                for k, v in query.items():
                    if item.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(item)
            if sort:
                key, direction = sort[0]
                filtered.sort(key=lambda x: x.get(key, 0), reverse=(direction == -1))
            if skip:
                filtered = filtered[skip:]
            if limit:
                filtered = filtered[:limit]
            return filtered
        except Exception as e:
            logger.warning(f"SQLite find error on '{collection}': {e}")
            return []

    async def count(self, collection: str, query: dict):
        guild_id = self._resolve_guild_id(collection, query)
        if self.primary_type == 'mongodb':
            try:
                cluster_name = await self.get_cluster_name(guild_id)
                db = self.get_db(cluster_name)
                if db is not None:
                    return await db[collection].count_documents(query)
            except Exception as e:
                logger.warning(f"MongoDB count error: {e}")
        res = await self.find(collection, query)
        return len(res)

    async def sqlite_execute_all(self, query: str, args: tuple = None):
        if self.sqlite_conn is None:
            return []
        async with self.sqlite_conn.execute(query, args or ()) as cursor:
            return await cursor.fetchall()

    async def _setup_sql_tables(self, db_type):
        queries = [
            'CREATE TABLE IF NOT EXISTS guild_prefixes (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS premium_keys (key_str VARCHAR(255) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS guild_premium (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS no_prefix_users (id VARCHAR(50) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS guild_assignments (id BIGINT PRIMARY KEY, cluster VARCHAR(50))',
            'CREATE TABLE IF NOT EXISTS social_stats (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS mod_cases (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS mod_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS logging_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS verification_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS voicemaster_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS voicemaster_channels (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS automod_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS greetings_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS autorole_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS afk_users (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS afk_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS afk_prefs (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS ticket_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS active_tickets (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS active_tickets_count (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS booster_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS booster_users (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS leveling_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS users_xp (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS customization_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS giveaways (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS suggestions_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS suggestions (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS starboard_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS starboard_messages (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS app_configs (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS submitted_apps (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS ss_checker_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS ss_hashes (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS music_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS user_playlists (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS invite_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS invite_data (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS joined_members_map (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS status_reward_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS status_reward_data (id VARCHAR(100) PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS social_alerts (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS stats_config (id BIGINT PRIMARY KEY, data TEXT)',
            'CREATE TABLE IF NOT EXISTS antinuke_config (id BIGINT PRIMARY KEY, data TEXT)',
        ]
        for q in queries:
            if db_type == 'mariadb':
                await self.mariadb_execute(q)
            else:
                await self.sqlite_execute(q)

    async def mariadb_execute(self, query: str, args: tuple = None):
        if self.mariadb_pool is None:
            return None
        async with self.mariadb_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args or ())
                return cur.rowcount

    async def sqlite_fetchone(self, query: str, args: tuple = None):
        if self.sqlite_conn is None:
            return None
        async with self.sqlite_conn.execute(query, args or ()) as cursor:
            return await cursor.fetchone()

    async def sqlite_execute(self, query: str, args: tuple = None):
        if self.sqlite_conn is None:
            return None
        cursor = await self.sqlite_conn.execute(query, args or ())
        await self.sqlite_conn.commit()
        return cursor.rowcount

    async def _init_mariadb(self):
        try:
            self.mariadb_pool = await aiomysql.create_pool(
                host=self.config.MARIADB_HOST,
                port=self.config.MARIADB_PORT,
                user=self.config.MARIADB_USER,
                password=self.config.MARIADB_PASSWORD,
                db=self.config.MARIADB_DB_NAME,
                autocommit=True,
                connect_timeout=2
            )
            logger.info('MariaDB connection pool established')
        except Exception as e:
            logger.warning(f'MariaDB init failed (will use fallback): {e}')
            self.mariadb_pool = None

    async def _init_sqlite(self):
        try:
            os.makedirs(os.path.dirname(self.config.SQLITE_DB_PATH), exist_ok=True)
            self.sqlite_conn = await aiosqlite.connect(self.config.SQLITE_DB_PATH)
            await self.sqlite_conn.execute('PRAGMA foreign_keys = ON')
            logger.info('SQLite connection established')
        except Exception as e:
            logger.error(f'SQLite init failed: {e}')
            self.sqlite_conn = None

    async def close(self):
        for name, data in self.mongodb_clusters.items():
            data['client'].close()
        if self.mariadb_pool:
            self.mariadb_pool.close()
            await self.mariadb_pool.wait_closed()
        if self.sqlite_conn:
            await self.sqlite_conn.close()
        logger.info('All database connections closed')
