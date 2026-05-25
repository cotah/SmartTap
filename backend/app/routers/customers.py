from fastapi import APIRouter, HTTPException

from app.schemas.customer import CustomerIdentifyIn, CustomerIdentifyOut

router = APIRouter(tags=["customers"])


@router.post("/customers/identify", response_model=CustomerIdentifyOut)
def identify_customer(body: CustomerIdentifyIn) -> CustomerIdentifyOut:
    _ = body
    raise HTTPException(status_code=501, detail="Not implemented yet")
