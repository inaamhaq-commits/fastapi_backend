from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


DashboardRange = Literal["week", "month", "3month"]


class DashboardOverviewResponse(BaseModel):
    label: str
    leads_generated: int
    calls_scheduled: int
    qualified: int
    pre_sale: int
    not_a_fit: int


class ManagerLeadTotalsResponse(BaseModel):
    total_leads: int
    calls_scheduled: int
    qualified: int
    pre_sale: int
    not_a_fit: int


class ManagerUserDashboardResponse(BaseModel):
    user_id: str
    name: str
    email: str
    leads: ManagerLeadTotalsResponse


class ManagerDashboardResponse(BaseModel):
    totals: ManagerLeadTotalsResponse
    users: list[ManagerUserDashboardResponse]
