import os
import sqlite3
from decimal import Decimal
from typing import Dict, List

try:
	import psycopg2
	from psycopg2.extras import RealDictCursor
except ImportError:
	psycopg2 = None
	RealDictCursor = None


_DB_INITIALIZED = False


DEFAULT_PRICE_SEED = [
	{"category": "Normal Orders", "package_cp": 10900, "price": Decimal("67")},
	{"category": "Normal Orders", "package_cp": 5040, "price": Decimal("34")},
	{"category": "Normal Orders", "package_cp": 2400, "price": Decimal("16")},
	{"category": "Normal Orders", "package_cp": 880, "price": Decimal("8.5")},
	{"category": "Normal Orders", "package_cp": 420, "price": Decimal("4.5")},
	{"category": "Normal Orders", "package_cp": 80, "price": Decimal("1")},
	{"category": "Special Packs", "package_cp": 24000, "price": Decimal("141")},
	{"category": "Special Packs", "package_cp": 21600, "price": Decimal("127")},
	{"category": "Special Packs", "package_cp": 19200, "price": Decimal("113")},
	{"category": "Special Packs", "package_cp": 16800, "price": Decimal("99.5")},
	{"category": "Special Packs", "package_cp": 15700, "price": Decimal("95.5")},
	{"category": "Special Packs", "package_cp": 14400, "price": Decimal("86")},
	{"category": "Special Packs", "package_cp": 12000, "price": Decimal("72")},
	{"category": "Special Packs", "package_cp": 9600, "price": Decimal("58")},
	{"category": "Special Packs", "package_cp": 7200, "price": Decimal("44.5")},
	{"category": "Special Packs", "package_cp": 4800, "price": Decimal("31")},
]


class _SqliteCursorWrapper:
	def __init__(self, cursor, is_dict=False):
		self.cursor = cursor
		self.is_dict = is_dict
		self.rowcount = -1

	def execute(self, sql, params=()):
		sql_converted = sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
		sql_converted = sql_converted.replace("%s", "?")
		new_params = [float(p) if isinstance(p, Decimal) else p for p in params]
		res = self.cursor.execute(sql_converted, new_params)
		self.rowcount = self.cursor.rowcount
		return res

	def fetchone(self):
		row = self.cursor.fetchone()
		if row is None:
			return None
		if self.is_dict:
			return dict(row)
		return tuple(row)

	def fetchall(self):
		rows = self.cursor.fetchall()
		if self.is_dict:
			return [dict(r) for r in rows]
		return [tuple(r) for r in rows]

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.cursor.close()


class _SqliteConnectionWrapper:
	def __init__(self, db_path="local.db"):
		self.conn = sqlite3.connect(db_path)
		self.conn.row_factory = sqlite3.Row

	def cursor(self, cursor_factory=None):
		is_dict = cursor_factory is not None and (cursor_factory == RealDictCursor or getattr(cursor_factory, "__name__", "") == "RealDictCursor")
		return _SqliteCursorWrapper(self.conn.cursor(), is_dict=is_dict)

	def commit(self):
		self.conn.commit()

	def close(self):
		self.conn.close()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		if exc_type:
			self.conn.rollback()
		else:
			self.conn.commit()
		self.conn.close()


def _get_database_url() -> str:
	return os.getenv("DATABASE_URL", "")


def _get_connection():
	database_url = _get_database_url()
	if database_url and (database_url.startswith("postgres://") or database_url.startswith("postgresql://")):
		return psycopg2.connect(database_url)
	return _SqliteConnectionWrapper("local.db")


def _initialize_prices_table() -> None:
	create_table_sql = """
	CREATE TABLE IF NOT EXISTS prices (
		id SERIAL PRIMARY KEY,
		category VARCHAR(20) NOT NULL,
		package_cp INTEGER NOT NULL,
		price DECIMAL(10,2) NOT NULL,
		active BOOLEAN DEFAULT TRUE,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	"""

	create_index_sql = """
	CREATE UNIQUE INDEX IF NOT EXISTS idx_prices_category_package_cp
	ON prices (category, package_cp);
	"""

	with _get_connection() as conn:
		with conn.cursor() as cur:
			cur.execute(create_table_sql)
			cur.execute(create_index_sql)
		conn.commit()


def _seed_prices_if_empty() -> None:
	with _get_connection() as conn:
		with conn.cursor() as cur:
			cur.execute("SELECT COUNT(*) FROM prices")
			count = cur.fetchone()[0]
			if count > 0:
				return

		with conn.cursor() as cur:
			for item in DEFAULT_PRICE_SEED:
				cur.execute(
					"""
					INSERT INTO prices (category, package_cp, price, active, updated_at)
					VALUES (%s, %s, %s, TRUE, CURRENT_TIMESTAMP)
					ON CONFLICT (category, package_cp)
					DO UPDATE SET
						price = EXCLUDED.price,
						active = TRUE,
						updated_at = CURRENT_TIMESTAMP
					""",
					(item["category"], item["package_cp"], item["price"]),
				)
		conn.commit()


def ensure_prices_schema() -> None:
	global _DB_INITIALIZED
	if _DB_INITIALIZED:
		return

	try:
		_initialize_prices_table()
		_seed_prices_if_empty()
		_DB_INITIALIZED = True
		print("Prices table is initialized and ready.")
	except Exception as exc:
		print(f"Failed to initialize prices table: {exc}")


def get_categories() -> List[str]:
	ensure_prices_schema()
	conn = None
	try:
		conn = _get_connection()
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT DISTINCT category
				FROM prices
				WHERE active = TRUE
				ORDER BY category ASC
				"""
			)
			rows = cur.fetchall()
			return [row[0] for row in rows]
	except Exception as exc:
		print(f"Failed to fetch categories: {exc}")
		return []
	finally:
		if conn:
			conn.close()


def get_packages(category: str) -> List[Dict]:
	ensure_prices_schema()
	conn = None
	try:
		conn = _get_connection()
		with conn.cursor(cursor_factory=RealDictCursor) as cur:
			cur.execute(
				"""
				SELECT package_cp, price
				FROM prices
				WHERE active = TRUE
				  AND category = %s
				ORDER BY package_cp DESC
				""",
				(category,),
			)
			return list(cur.fetchall())
	except Exception as exc:
		print(f"Failed to fetch packages for category '{category}': {exc}")
		return []
	finally:
		if conn:
			conn.close()


def get_price(package_cp: int):
	ensure_prices_schema()
	conn = None
	try:
		conn = _get_connection()
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT price
				FROM prices
				WHERE active = TRUE
				  AND package_cp = %s
				ORDER BY updated_at DESC
				LIMIT 1
				""",
				(package_cp,),
			)
			row = cur.fetchone()
			return row[0] if row else None
	except Exception as exc:
		print(f"Failed to fetch price for package_cp '{package_cp}': {exc}")
		return None
	finally:
		if conn:
			conn.close()


def update_price(package_cp: int, new_price):
	ensure_prices_schema()
	conn = None
	try:
		conn = _get_connection()
		with conn.cursor() as cur:
			cur.execute(
				"""
				UPDATE prices
				SET price = %s,
					updated_at = CURRENT_TIMESTAMP
				WHERE package_cp = %s
				""",
				(new_price, package_cp),
			)
			updated = cur.rowcount
		conn.commit()
		return updated
	except Exception as exc:
		print(f"Failed to update price for package_cp '{package_cp}': {exc}")
		return 0
	finally:
		if conn:
			conn.close()


def bulk_update_prices(price_data: List[Dict]) -> int:
	ensure_prices_schema()
	if not price_data:
		return 0

	updated_count = 0
	try:
		with _get_connection() as conn:
			with conn.cursor() as cur:
				for item in price_data:
					category = item.get("category")
					package_cp = item.get("package_cp")
					price = item.get("price")
					active = item.get("active", True)

					if category is None or package_cp is None or price is None:
						continue

					cur.execute(
						"""
						INSERT INTO prices (category, package_cp, price, active, updated_at)
						VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
						ON CONFLICT (category, package_cp)
						DO UPDATE SET
							price = EXCLUDED.price,
							active = EXCLUDED.active,
							updated_at = CURRENT_TIMESTAMP
						""",
						(category, package_cp, price, active),
					)
					updated_count += 1
			conn.commit()
	except Exception as exc:
		print(f"Failed to bulk update prices: {exc}")
		return 0

	return updated_count


def update_package_price(category: str, package_cp: int, new_price) -> bool:
	ensure_prices_schema()
	conn = None
	try:
		conn = _get_connection()
		with conn.cursor() as cur:
			cur.execute(
				"""
				UPDATE prices
				SET price = %s,
					active = TRUE,
					updated_at = CURRENT_TIMESTAMP
				WHERE category = %s AND package_cp = %s
				""",
				(new_price, category, package_cp),
			)
			updated = cur.rowcount
		conn.commit()
		return updated > 0
	except Exception as exc:
		print(f"Failed to update package price for '{category}' - '{package_cp}': {exc}")
		return False
	finally:
		if conn:
			conn.close()


def add_package(category: str, package_cp: int, price) -> bool:
	ensure_prices_schema()
	conn = None
	try:
		conn = _get_connection()
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO prices (category, package_cp, price, active, updated_at)
				VALUES (%s, %s, %s, TRUE, CURRENT_TIMESTAMP)
				ON CONFLICT (category, package_cp)
				DO UPDATE SET
					price = EXCLUDED.price,
					active = TRUE,
					updated_at = CURRENT_TIMESTAMP
				""",
				(category, package_cp, price),
			)
		conn.commit()
		return True
	except Exception as exc:
		print(f"Failed to add package for '{category}' - '{package_cp}': {exc}")
		return False
	finally:
		if conn:
			conn.close()


def remove_package(category: str, package_cp: int) -> bool:
	ensure_prices_schema()
	conn = None
	try:
		conn = _get_connection()
		with conn.cursor() as cur:
			cur.execute(
				"""
				UPDATE prices
				SET active = FALSE,
					updated_at = CURRENT_TIMESTAMP
				WHERE category = %s AND package_cp = %s
				""",
				(category, package_cp),
			)
			updated = cur.rowcount
		conn.commit()
		return updated > 0
	except Exception as exc:
		print(f"Failed to remove package for '{category}' - '{package_cp}': {exc}")
		return False
	finally:
		if conn:
			conn.close()

