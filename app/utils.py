import httpx
from fastapi import HTTPException, status

async def acess_provider(data: dict):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url = "http://provider:8000/payments",
                headers = {
                    "Content-Type": "application/json",
                    "Idempotency-Key": data.get("operation_id"),
                    "X-Correlation-ID": data.get("operation_id")
                    },
                json = data
                )
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error while accessing provider: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Provider returned an error: {exc.response.status_code}")