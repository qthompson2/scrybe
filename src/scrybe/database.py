from mysql.connector.aio import MySQLConnectionPool

from typing import TypedDict

DATABASE_NAME = "scrybe_db"

async def setup_database(pool: MySQLConnectionPool) -> None:
	connector = await pool.get_connection()
	cursor = await connector.cursor()
	await cursor.execute("SHOW DATABASES")
	results = await cursor.fetchall()
	for row in results:
		if row[0] == DATABASE_NAME:
			return

	await cursor.execute(f"CREATE DATABASE {DATABASE_NAME}")
	await cursor.execute(f"USE {DATABASE_NAME}")
	await cursor.execute("CREATE TABLE workspace (workspace_id INT AUTO_INCREMENT, workspace_name VARCHAR(64) NOT NULL UNIQUE, PRIMARY KEY (workspace_id))")
	await cursor.execute("CREATE TABLE page (page_id INT AUTO_INCREMENT, workspace_id INT, page_name VARCHAR(64) NOT NULL, content text, PRIMARY KEY (page_id), FOREIGN KEY (workspace_id) REFERENCES workspace(workspace_id))")

	await connector.commit()
	await cursor.close()

async def create_page(pool: MySQLConnectionPool, page_name: str, workspace_name: str) -> int:
	async with pool.get_connection() as connector:
		cursor = await connector.cursor()
		await cursor.execute(f"USE {DATABASE_NAME}")
		await cursor.fetchall()

		await cursor.execute("SELECT workspace_id FROM workspace WHERE workspace_name = %s", [workspace_name])
		
		results = await cursor.fetchall()
		workspace_id = -1
		if len(results) == 1 and len(results[0]) == 1:
			workspace_id = results[0][0]
		else:
			raise Exception(f"No workspace with name '{workspace_name}' exists!")

		await cursor.execute("INSERT INTO page (workspace_id, page_name) values (%s, %s)", [workspace_id, page_name])
		page_id = cursor.lastrowid

		await connector.commit()
		await cursor.close()

		return page_id

async def get_page_content(pool: MySQLConnectionPool, page_id: int) -> str:
	async with pool.get_connection() as connector:
		cursor = await connector.cursor()
		await cursor.execute(f"USE {DATABASE_NAME}")
		await cursor.execute("SELECT content FROM page WHERE page_id = %s", [page_id])
		
		results = await cursor.fetchall()
		if len(results) != 1 and len(results[0]) != 1:
			raise Exception(f"No page with id #{page_id} exists!")
		
		await cursor.close()

		return results[0][0]

class Page(TypedDict):
	page_id: int
	page_name: str

async def get_pages(pool: MySQLConnectionPool, workspace_name: str) -> list[Page]:
	async with pool.get_connection() as connector:
		cursor = await connector.cursor()
		await cursor.execute(f"USE {DATABASE_NAME}")
		await cursor.execute("SELECT workspace_id FROM workspace WHERE workspace_name = %s", [workspace_name])
		
		results = await cursor.fetchall()
		workspace_id = -1
		if len(results) == 1 and len(results[0]) == 1:
			workspace_id = results[0][0]
		else:
			raise Exception(f"No workspace with name '{workspace_name}' exists!")
		
		await cursor.execute("SELECT page_id, page_name FROM page WHERE workspace_id = %s", [workspace_id])
		results = await cursor.fetchall()
		await cursor.close()

		r_list = [{"page_id" : x[0], "page_name" : x[1]} for x in results]
		return r_list

async def create_workspace(pool: MySQLConnectionPool, workspace_name: str) -> int:
	async with pool.get_connection() as connector:
		cursor = await connector.cursor()
		await cursor.execute(f"USE {DATABASE_NAME}")

		await cursor.execute("SELECT * FROM workspace WHERE workspace_name = %s", [workspace_name])
		results = await cursor.fetchall()
		if len(results) > 0:
			raise Exception(f"Workspace with name '{workspace_name}' already exists!")

		await cursor.execute("INSERT INTO workspace (workspace_name) values (%s)", [workspace_name])
		workspace_id = cursor.lastrowid

		await connector.commit()
		await cursor.close()

		return workspace_id

async def get_workspaces(pool: MySQLConnectionPool) -> list[str]:
	async with pool.get_connection() as connector:
		cursor = await connector.cursor()
		await cursor.execute(f"USE {DATABASE_NAME}")

		await cursor.execute("SELECT workspace_name FROM workspace")
		results = await cursor.fetchall()

		await cursor.close()

		return [x[0] for x in results]

async def delete_workspace(pool: MySQLConnectionPool, workspace_name: str) -> None:
	async with pool.get_connection() as connector:
		cursor = await connector.cursor()
		await cursor.execute(f"USE {DATABASE_NAME}")

		await cursor.execute("SELECT workspace_id FROM workspace WHERE workspace_name = %s", [workspace_name])
		results = await cursor.fetchall()
		if len(results) == 0:
			raise Exception(f"Workspace with name '{workspace_name}' does not exist!")

		await cursor.execute("DELETE FROM page WHERE workspace_id = %s", (results[0][0],))
		await cursor.execute("DELETE FROM workspace WHERE workspace_id = %s", (results[0][0],))

		await connector.commit()
		await cursor.close()