from aiosqlite import connect

async def init_db():
    async with connect("data/database.db") as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA busy_timeout=5000;")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                operation_id TEXT PRIMARY KEY,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL CHECK (currency = 'RUB'),
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('CREATED', 'PROCESSING', 'COMPLETED', 'REJECTED')),
                provider_payment_id TEXT DEFAULT NULL
            );
            """)
        await db.commit()
        
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT NOT NULL,
                fromStatus TEXT NOT NULL CHECK (fromStatus IN ('CREATED', 'PROCESSING', 'COMPLETED', 'REJECTED')),
                toStatus TEXT NOT NULL CHECK (toStatus IN ('CREATED', 'PROCESSING', 'COMPLETED', 'REJECTED')),
                message TEXT,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (operation_id) REFERENCES operations (operation_id)
            );
            """
        )
        
        await db.commit()