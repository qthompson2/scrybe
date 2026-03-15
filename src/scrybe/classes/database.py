from mysql.connector import connect, MySQLConnection
from asyncio import Lock, get_running_loop
from concurrent.futures import ThreadPoolExecutor

from typing import TypedDict

class Database:
	NAME = "scrybe_db"

	def __init__(self, host, username, password):
		self._login = {
			"host": host,
			"user": username,
			"password": password,
		}
		self._connector: MySQLConnection = None

		self._lock = Lock()
		self._exec = ThreadPoolExecutor(max_workers=4)

	async def __aenter__(self):
		loop = get_running_loop()

		self._connector = await loop.run_in_executor(
			self._exec,
			lambda: connect(**self._login)
		)
		return self
	
	async def __aexit__(self, exc_type, exc, tb):
		loop = get_running_loop()
		await loop.run_in_executor(self._exec, self._connector.close)

	async def _execute(self, query, params=None, database=None):
		loop = get_running_loop()

		def _execute():
			self._connector.reconnect()
			cursor = self._connector.cursor()
			if database:
				cursor.execute(f"USE {database}")
				cursor.fetchall()
			cursor.execute(query, params or ())
			rows = cursor.fetchall()
			cursor.close()
			return rows

		return await loop.run_in_executor(self._exec, _execute)
	
	async def _execute_get_rowid(self, query, params=None, database=None):
		loop = get_running_loop()

		def _execute():
			self._connector.reconnect()
			cursor = self._connector.cursor()
			if database:
				cursor.execute(f"USE {database}")
				cursor.fetchall()
			cursor.execute(query, params or ())
			cursor.fetchall()
			rowid = cursor.lastrowid
			cursor.close()
			return rowid

		return await loop.run_in_executor(self._exec, _execute)

	async def setup(self) -> None:
		async with self._lock:
			results = await self._execute("SHOW DATABASES")
			for row in results:
				if row[0] == Database.NAME:
					return

			await self._execute(f"CREATE DATABASE {Database.NAME}")
			await self._execute("CREATE TABLE workspace (workspace_id INT AUTO_INCREMENT, workspace_name VARCHAR(64) NOT NULL UNIQUE, PRIMARY KEY (workspace_id))", database=Database.NAME)
			await self._execute("CREATE TABLE page (page_id INT AUTO_INCREMENT, workspace_id INT, page_name VARCHAR(64) NOT NULL, content text, PRIMARY KEY (page_id), FOREIGN KEY (workspace_id) REFERENCES workspace(workspace_id))", database=Database.NAME)

			self._connector.commit()
	
	async def create_page(self, page_name:str, workspace_name: str) -> int:
		async with self._lock:
			results = await self._execute("SELECT workspace_id FROM workspace WHERE workspace_name = %s", params=[workspace_name], database=Database.NAME)
			
			workspace_id = -1
			if len(results) == 1 and len(results[0]) == 1:
				workspace_id = results[0][0]
			else:
				raise Exception(f"No workspace with name '{workspace_name}' exists!")

			page_id = await self._execute_get_rowid("INSERT INTO page (workspace_id, page_name) values (%s, %s)", params=[workspace_id, page_name], database=Database.NAME)

			self._connector.commit()

			return page_id
		
	async def delete_page(self, page_id:int) -> None:
		async with self._lock:
			results = await self._execute("SELECT page_name FROM page WHERE page_id = %s", params=[page_id], database=Database.NAME)

			if len(results) != 1:
				raise Exception(f"No page with id #{page_id} exists!")
			
			await self._execute("DELETE FROM page WHERE page_id = %s", params=[page_id], database=Database.NAME)
			self._connector.commit()
		
	async def get_page_content(self, page_id: int) -> str:
		async with self._lock:
			results = await self._execute("SELECT content FROM page WHERE page_id = %s", params=[page_id], database=Database.NAME)
			
			if len(results) != 1 and len(results[0]) != 1:
				raise Exception(f"No page with id #{page_id} exists!")
			elif type(results[0][0]) == str:
				return results[0][0]
			else:
				return ""
					
	async def update_page_content(self, page_id: int, new_content: str) -> None:
		async with self._lock:
			results = await self._execute("SELECT 1 FROM page WHERE page_id = %s", params=[page_id], database=Database.NAME)

			if len(results) != 1 and len(results[0]) != 1:
				raise Exception(f"No page with id #{page_id} exists!")

			await self._execute("UPDATE page SET content = %s WHERE page_id = %s", params=[new_content, page_id], database=Database.NAME)
			self._connector.commit()
		
	class Page(TypedDict):
		page_id: int
		page_name: str

	async def get_pages(self, workspace_name: str) -> list[Page]:
		async with self._lock:
			results = await self._execute("SELECT workspace_id FROM workspace WHERE workspace_name = %s", params=[workspace_name], database=Database.NAME)
			
			workspace_id = -1
			if len(results) == 1 and len(results[0]) == 1:
				workspace_id = results[0][0]
			else:
				raise Exception(f"No workspace with name '{workspace_name}' exists!")
			
			results = await self._execute("SELECT page_id, page_name FROM page WHERE workspace_id = %s", params=[workspace_id], database=Database.NAME)

			r_list = [{"page_id" : x[0], "page_name" : x[1]} for x in results]
			return r_list
		
	async def create_workspace(self, workspace_name: str) -> int:
		async with self._lock:
			results = await self._execute("SELECT * FROM workspace WHERE workspace_name = %s", params=[workspace_name], database=Database.NAME)
			if len(results) > 0:
				raise Exception(f"Workspace with name '{workspace_name}' already exists!")

			workspace_id = await self._execute_get_rowid("INSERT INTO workspace (workspace_name) values (%s)", params=[workspace_name], database=Database.NAME)

			self._connector.commit()

			return workspace_id
		
	async def get_workspaces(self) -> list[str]:
		async with self._lock:
			results = await self._execute("SELECT workspace_name FROM workspace", database=Database.NAME)

			return [x[0] for x in results]
		
	async def delete_workspace(self, workspace_name: str) -> None:
		async with self._lock:
			results = await self._execute("SELECT workspace_id FROM workspace WHERE workspace_name = %s", params=[workspace_name], database=Database.NAME)
			if len(results) == 0:
				raise Exception(f"Workspace with name '{workspace_name}' does not exist!")

			await self._execute("DELETE FROM page WHERE workspace_id = %s", params=[results[0][0]], database=Database.NAME)
			self._connector.commit()
			await self._execute("DELETE FROM workspace WHERE workspace_id = %s", params=[results[0][0]], database=Database.NAME)
			self._connector.commit()