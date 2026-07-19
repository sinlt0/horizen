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
    GUILD_TABLES = [
        ('guild_prefixes', 'id BIGINT'),
        ('premium_keys', 'key_str VARCHAR(255)'),
        ('guild_premium', 'id BIGINT'),
        ('no_prefix_users', 'id VARCHAR(50)'),
        ('guild_assignments', 'id BIGINT'),
        ('social_stats', 'id VARCHAR(100)'),
        ('mod_cases', 'id VARCHAR(100)'),
        ('mod_config', 'id BIGINT'),
        ('logging_config', 'id BIGINT'),
        ('verification_config', 'id BIGINT'),
        ('voicemaster_config', 'id BIGINT'),
        ('voicemaster_channels', 'id BIGINT'),
        ('automod_config', 'id BIGINT'),
        ('greetings_config', 'id BIGINT'),
        ('autorole_config', 'id BIGINT'),
        ('afk_users', 'id VARCHAR(100)'),
        ('afk_config', 'id BIGINT'),
        ('afk_prefs', 'id BIGINT'),
        ('ticket_config', 'id BIGINT'),
        ('active_tickets', 'id BIGINT'),
        ('active_tickets_count', 'id VARCHAR(100)'),
        ('booster_config', 'id BIGINT'),
        ('booster_users', 'id VARCHAR(100)'),
        ('leveling_config', 'id BIGINT'),
        ('users_xp', 'id VARCHAR(100)'),
        ('customization_config', 'id BIGINT'),
        ('giveaways', 'id BIGINT'),
        ('suggestions_config', 'id BIGINT'),
        ('suggestions', 'id BIGINT'),
        ('starboard_config', 'id BIGINT'),
        ('starboard_messages', 'id BIGINT'),
        ('app_configs', 'id BIGINT'),
        ('submitted_apps', 'id BIGINT'),
        ('ss_checker_config', 'id BIGINT'),
        ('ss_hashes', 'id VARCHAR(100)'),
        ('music_config', 'id BIGINT'),
        ('user_playlists', 'id BIGINT'),
        ('invite_config', 'id BIGINT'),
        ('invite_data', 'id VARCHAR(100)'),
        ('joined_members_map', 'id VARCHAR(100)'),
        ('status_reward_config', 'id BIGINT'),
        ('status_reward_data', 'id VARCHAR(100)'),
        ('social_alerts', 'id BIGINT'),
        ('stats_config', 'id BIGINT'),
        ('antinuke_config', 'id BIGINT'),
        ('custom_commands', 'id BIGINT'),
        ('reaction_roles', 'id BIGINT'),
        ('polls', 'id BIGINT'),
        ('bump_config', 'id BIGINT'),
        ('birthday_config', 'id BIGINT'),
        ('birthdays', 'id VARCHAR(100)'),
        ('counting_config', 'id BIGINT'),
        ('confession_config', 'id BIGINT'),
        ('scheduled_messages', 'id VARCHAR(200)'),
        ('mod_notes', 'id VARCHAR(100)'),
        ('sticky_messages', 'id BIGINT'),
        ('reminders', 'id BIGINT'),
        ('todos', 'id BIGINT'),
        ('reputation', 'id VARCHAR(100)'),
        ('reputation_config', 'id BIGINT'),
        ('saved_quotes', 'id BIGINT'),
        ('server_analytics', 'id BIGINT'),
        ('user_weather', 'id BIGINT'),
    ]

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

        if self.sqlite_conn is not None:
            import asyncio
            asyncio.create_task(self._run_sync_tasks())

        logger.info(f'All database connections initialized. Primary storage: {self.primary_type}')

    async def _run_sync_tasks(self):
        if self.primary_type == 'mongodb' and getattr(self.config, 'AUTO_HYDRATE_SQLITE', True):
            await self._hydrate_sqlite_from_mongo()
        if self.mongodb_clusters and getattr(self.config, 'AUTO_REVERSE_SYNC', True):
            await self._reverse_sync_mongo_from_sqlite()

    async def _hydrate_sqlite_from_mongo(self):
        logger.info('Checking SQLite for empty tables to hydrate from MongoDB...')
        hydrated_tables = 0
        hydrated_docs = 0

        for name, _ in self.GUILD_TABLES:
            if name == 'guild_assignments':
                continue
            try:
                count_row = await self.sqlite_fetchone(f'SELECT COUNT(*) FROM {name}')
                count = count_row[0] if count_row else 0
                if count > 0:
                    continue

                docs = await self.find(name, {})
                if not docs:
                    continue

                for doc in docs:
                    id_val = doc.get('_id')
                    if id_val is None:
                        continue
                    try:
                        json_data = json.dumps(doc, cls=DatabaseEncoder)
                        if name == 'premium_keys':
                            key_val = doc.get('key') or id_val
                            q = f'INSERT OR REPLACE INTO {name} (key_str, data) VALUES (?, ?)'
                            await self.sqlite_execute(q, (key_val, json_data))
                        else:
                            q = f'INSERT OR REPLACE INTO {name} (id, data) VALUES (?, ?)'
                            await self.sqlite_execute(q, (id_val, json_data))
                        hydrated_docs += 1
                    except Exception as e:
                        logger.warning(f"Hydration: failed to insert doc into '{name}': {e}")

                hydrated_tables += 1
                logger.info(f"Hydrated SQLite table '{name}' with {len(docs)} document(s) from MongoDB.")
            except Exception as e:
                logger.warning(f"Hydration: failed to process table '{name}': {e}")

        if hydrated_tables:
            logger.info(f'SQLite hydration complete: {hydrated_docs} document(s) across {hydrated_tables} table(s).')
        else:
            logger.info('SQLite hydration skipped: all tables already have data or MongoDB had nothing to offer.')

    async def _reverse_sync_mongo_from_sqlite(self):
        logger.info('Checking SQLite for data missing in MongoDB...')
        synced_tables = 0
        synced_docs = 0

        for name, _ in self.GUILD_TABLES:
            if name in ('guild_assignments', 'premium_keys'):
                continue
            try:
                id_col = 'id'
                rows = await self.sqlite_execute_all(f'SELECT {id_col}, data FROM {name}')
                if not rows:
                    continue

                table_synced = 0
                for id_val, raw_data in rows:
                    try:
                        doc = json.loads(raw_data)
                        if '_id' not in doc:
                            doc['_id'] = id_val

                        guild_id = self._resolve_guild_id(name, {'_id': id_val})
                        cluster_name = await self.get_cluster_name(guild_id)
                        db = self.get_db(cluster_name)
                        if db is None:
                            continue

                        existing = await db[name].find_one({'_id': doc['_id']})
                        if existing:
                            continue

                        await db[name].update_one({'_id': doc['_id']}, {'$set': doc}, upsert=True)
                        table_synced += 1
                        synced_docs += 1
                    except Exception as e:
                        logger.warning(f"Reverse sync: failed to push doc into MongoDB '{name}': {e}")

                if table_synced:
                    synced_tables += 1
                    logger.info(f"Reverse synced {table_synced} document(s) from SQLite into MongoDB table '{name}'.")
            except Exception as e:
                logger.warning(f"Reverse sync: failed to process table '{name}': {e}")

        if synced_tables:
            logger.info(f'Reverse sync complete: {synced_docs} document(s) pushed to MongoDB across {synced_tables} table(s).')
        else:
            logger.info('Reverse sync skipped: MongoDB already has everything SQLite has, or SQLite was empty.')

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
        mongo_reachable = False
        if self.primary_type == 'mongodb':
            try:
                cluster_name = await self.get_cluster_name(guild_id)
                db = self.get_db(cluster_name)
                if db is not None:
                    mongo_reachable = True
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
                if mongo_reachable and self.primary_type == 'mongodb':
                    import asyncio
                    asyncio.create_task(self._repair_mongo_doc(collection, item))
                return item
        except Exception as e:
            logger.warning(f"SQLite find_one error on '{collection}': {e}")
        return None

    async def _repair_mongo_doc(self, collection: str, doc: dict):
        try:
            guild_id = self._resolve_guild_id(collection, {'_id': doc.get('_id')})
            cluster_name = await self.get_cluster_name(guild_id)
            db = self.get_db(cluster_name)
            if db is None:
                return
            await db[collection].update_one({'_id': doc.get('_id')}, {'$set': doc}, upsert=True)
            logger.info(f"Repaired MongoDB '{collection}' doc '{doc.get('_id')}' from SQLite (was missing upstream).")
        except Exception as e:
            logger.warning(f"Failed to repair MongoDB '{collection}' doc from SQLite: {e}")

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
                    for k, v in update['$set'].items():
                        if '.' in k:
                            parts = k.split('.')
                            d = existing
                            for part in parts[:-1]:
                                d = d.setdefault(part, {})
                            d[parts[-1]] = v
                        else:
                            existing[k] = v
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
                        if '.' in k:
                            parts = k.split('.')
                            d = existing
                            for part in parts[:-1]:
                                if not isinstance(d, dict) or part not in d:
                                    d = None
                                    break
                                d = d[part]
                            if d and isinstance(d, dict) and parts[-1] in d:
                                del d[parts[-1]]
                        elif k in existing:
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
        queries = []
        for name, pk in self.GUILD_TABLES:
            if name == 'guild_assignments':
                queries.append(f'CREATE TABLE IF NOT EXISTS {name} ({pk} PRIMARY KEY, cluster VARCHAR(50))')
            else:
                queries.append(f'CREATE TABLE IF NOT EXISTS {name} ({pk} PRIMARY KEY, data TEXT)')
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
