from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, HTTPException
from fastapi import status
from pydantic import BaseModel, ValidationError, field_validator
import re

from aiosqlite import connect
from asyncio import wait_for, TimeoutError

from app.database import init_db

class Operation(BaseModel):
    operation_id: str
    amount:  str
    currency: str
    description: str

    @field_validator("amount", mode="before")
    @classmethod
    def amount_validation(cls, v):
        if re.fullmatch(r'\d+.\d{2}', v):
            return v
        raise ValueError("amount — положительная десятичная строка с не более чем двумя знаками после точки")

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

@app.post("/operations")
async def create_operation(operation: Operation):
    async with connect("data/database.db") as db:
        try:
            await db.execute(
                "INSERT INTO operations (operation_id, amount, currency, description, status) VALUES (?, ?, ?, ?, ?)",
                (operation.operation_id, operation.amount, operation.currency, operation.description, "CREATED")
            )
            await db.commit()
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return status.HTTP_201_CREATED

@app.post("/operations/{id}/submit")
async def submit_operation():
    return status.HTTP_202_ACCEPTED

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

@app.get("/operations/{id}/events")
async def get_operation_events():
    return status.HTTP_200_OK