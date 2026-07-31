from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, BackgroundTasks
from fastapi import status


from aiosqlite import IntegrityError, connect
from asyncio import wait_for

from app.database import init_db
from app.models import Operation, OperationResponse
from app.utils import acess_provider

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    try:
        async with connect("data/database.db") as db:
            async with db.execute("SELECT 1") as cursor:
                result = await wait_for(cursor.fetchone(), timeout=1.0)
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    if result is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return {"status": "ok"}

@app.post("/operations", status_code=status.HTTP_201_CREATED)
async def create_operation(operation: Operation):
    async with connect("data/database.db") as db:
        try:
            await db.execute(
                "INSERT INTO operations (operation_id, amount, currency, description, status) VALUES (?, ?, ?, ?, ?)",
                (operation.operation_id, operation.amount, operation.currency, operation.description, "CREATED")
            )
        except IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        try:
            await db.execute(
                "INSERT INTO events (operation_id, toStatus, message) VALUES (?, ?, ?)",
                (operation.operation_id, "CREATED", "Operation created")
            )
        except IntegrityError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        finally:
            await db.commit()
    return OperationResponse(
        operationId=operation.operation_id,
        amount=operation.amount,
        currency=operation.currency,
        description=operation.description,
        status="CREATED"
    )

@app.post("/operations/{id}/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_operation(id: str, background_tasks: BackgroundTasks):
    async with connect("data/database.db") as db:
        async with db.execute("SELECT status FROM operations WHERE operation_id = ?", (id,)) as cursor:
            operation = await cursor.fetchone()
            if operation is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found")
            current_status = operation[0]
            if current_status != "CREATED":
                return Response(status_code=status.HTTP_200_OK, content="Operation submitted for processing")

        await db.execute(
            "UPDATE operations SET status = ? WHERE operation_id = ?",
            ("PROCESSING", id)
        )
        await db.execute(
            "INSERT INTO events (operation_id, fromStatus, toStatus, message) VALUES (?, ?, ?, ?)",
            (id, current_status, "PROCESSING", "Operation submitted for processing")
        )
        await db.commit()

    background_tasks.add_task(acess_provider, {"operation_id": id, "amount": operation[1], "currency": operation[2]})
    return {"message": "Operation submitted for processing"}

@app.post("/receipts")
async def take_receipt():
    return status.HTTP_204_NO_CONTENT

@app.get("/operations/{id}", status_code=status.HTTP_200_OK)
async def get_operation(id: str):
    async with connect("data/database.db") as db:
        async with db.execute("SELECT * FROM operations WHERE operation_id = ?", (id,)) as cursor:
            operation = await cursor.fetchone()
            if operation is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found")
    return operation

@app.get("/operations/{id}/events", status_code=status.HTTP_200_OK)
async def get_operation_events(id: str):
    async with connect("data/database.db") as db:
        async with db.execute("SELECT * FROM events WHERE operation_id = ?", (id,)) as cursor:
            events = await cursor.fetchall()
    return events