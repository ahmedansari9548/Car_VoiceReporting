from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from app.db.database import get_db
from app.repositories import inventory_repo

router = APIRouter()

@router.get("")
def get_cars(
    make: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    transmission: Optional[str] = Query(None),
    price_max: Optional[int] = Query(None),
    limit: int = Query(50),
    db=Depends(get_db),
):
    try:
        filters = {}
        if make:
            filters["make"] = make
        if city:
            filters["city"] = city
        if transmission:
            filters["transmission"] = transmission
        if price_max:
            filters["price_max"] = price_max

        cars = inventory_repo.search(db, filters, limit=limit)
        total = inventory_repo.count(db, filters)
        return {"cars": cars, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
