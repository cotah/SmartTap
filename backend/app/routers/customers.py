from fastapi import APIRouter

from app.schemas.customer import CustomerIdentifyIn, CustomerIdentifyOut
from app.services.customer_service import IdentifyContext, identify_customer

router = APIRouter(tags=["customers"])


@router.post("/customers/identify", response_model=CustomerIdentifyOut)
def identify_customer_endpoint(body: CustomerIdentifyIn) -> CustomerIdentifyOut:
    ctx = IdentifyContext(
        tenant_id=body.tenant_id,
        phone=body.phone,
        name=body.name,
        birthday=body.birthday,
        gdpr_consent=body.gdpr_consent,
        gdpr_consent_text=body.gdpr_consent_text,
    )
    result = identify_customer(ctx)
    return CustomerIdentifyOut(
        customer_id=result.customer_id,
        magic_link_token=result.magic_link_token,
        stamps_current=result.stamps_current,
    )
