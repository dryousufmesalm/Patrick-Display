
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING ,Dict,List
if TYPE_CHECKING:
    from .ct_cycles_orders import CtCyclesOrders
from sqlmodel import Column, JSON


class CTCycle(SQLModel, table=True):
    __tablename__ = "ct_cycles"
    id: int | None = Field(default=None, primary_key=True)
    remote_id: int | None = Field(default=None, unique=True)
    orders: List["CtCyclesOrders"] = Relationship(back_populates="cycle")
    lower_bound: float
    upper_bound: float
    is_pending: bool
    is_closed: bool
    closing_method:  Dict = Field(default_factory=dict, sa_column=Column(JSON))
    opened_by: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    lot_idx: int
    status: str
    total_volume: float
    total_profit: float
    zone_index: int
    bot: str
    account: str
    symbol: str
    threshold_lower: float
    threshold_upper: float    
    initial: List[int] = Field(default_factory=list, sa_column=Column(JSON))
    hedge: List[int] = Field(default_factory=list, sa_column=Column(JSON))
    pending: List[int] = Field(default_factory=list, sa_column=Column(JSON))
    closed: List[int] = Field(default_factory=list, sa_column=Column(JSON))
    recovery: List[int] = Field(default_factory=list, sa_column=Column(JSON))
    threshold: List[int] = Field(default_factory=list, sa_column=Column(JSON))
    class Config:
        arbitrary_types_allowed = True 
        
