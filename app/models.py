from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal
from decimal import Decimal, InvalidOperation

class Operation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    operation_id: str = Field(alias="operationId")
    amount:  str
    currency: Literal["RUB"]
    description: str

    @field_validator("amount", mode="before")
    @classmethod
    def amount_validation(cls, v):
        try:
            amount = Decimal(v)
        except InvalidOperation:
            raise ValueError("Amount must be a valid decimal number")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if amount.as_tuple().exponent < -2:
            raise ValueError("Amount must have at most two decimal places")
        if amount.is_infinite() or amount.is_nan():
            raise ValueError("Amount must be a finite number")
        return str(amount)

class OperationResponse(Operation):
    status: Literal["CREATED", "PROCESSING", "COMPLETED", "REJECTED"]
    provider_payment_id: str | None = Field(alias="providerPaymentId", default=None)
