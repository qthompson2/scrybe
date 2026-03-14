import mysql.connector
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncMysqlWrapper:
    def __init__(self, **config):
        self._config = config
        self._conn = None
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def __aenter__(self):
        loop = asyncio.get_running_loop()
        # Run the blocking connect() in a thread
        self._conn = await loop.run_in_executor(
            self._executor,
            lambda: mysql.connector.connect(**self._config)
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._conn.close)

    async def execute(self, query, params=None):
        loop = asyncio.get_running_loop()

        def _execute():
            cursor = self._conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            cursor.close()
            return rows

        return await loop.run_in_executor(self._executor, _execute)