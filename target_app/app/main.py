from __future__ import annotations

import asyncio
import os
from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Demo Commerce API", version="1.0.0", description="A deliberately small demo API for TestGuard AI." )

PRODUCTS = {
    1: {"id": 1, "name": "Notebook", "price": 4.99, "category": "stationery"},
    2: {"id": 2, "name": "Desk Lamp", "price": 18.50, "category": "home"},
    3: {"id": 3, "name": "Water Bottle", "price": 12.00, "category": "outdoors"},
}


class CheckoutRequest(BaseModel):
    product_id: Annotated[int, Field(gt=0)]
    quantity: Annotated[int, Field(gt=0, le=100)]


async def maybe_delay() -> None:
    delay_ms = max(0, int(os.getenv("DEMO_LATENCY_MS", "0")))
    if delay_ms:
        await asyncio.sleep(delay_ms / 1000)


def get_product(product_id: int) -> dict:
    product = PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    output = dict(product)
    # Demonstration-only fault injection: lets the tester prove it catches data regressions.
    if os.getenv("DEMO_BUG_MODE", "false").lower() in {"1", "true", "yes", "on"} and product_id == 1:
        output["price"] = 5.49
    return output


@app.get("/health")
async def health():
    return {"status": "ok", "service": "demo-commerce-api"}


@app.get("/products")
async def list_products():
    await maybe_delay()
    return [get_product(product_id) for product_id in sorted(PRODUCTS)]


@app.get("/products/{product_id}")
async def product_detail(product_id: int):
    await maybe_delay()
    return get_product(product_id)


@app.post("/checkout", status_code=201)
async def checkout(request: CheckoutRequest):
    await maybe_delay()
    product = get_product(request.product_id)
    total = round(product["price"] * request.quantity, 2)
    return {"order_id": "DEMO-1001", "product_id": request.product_id, "quantity": request.quantity, "unit_price": product["price"], "total": total}
