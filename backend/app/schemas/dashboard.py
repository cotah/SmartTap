from pydantic import BaseModel, Field


class DashboardOverview(BaseModel):
    customers_total: int = Field(ge=0)
    taps_week: int = Field(ge=0)
    reviews_month: int = Field(ge=0)
    customers_at_risk: int = Field(ge=0)
    active_stamps_total: int = Field(ge=0)
