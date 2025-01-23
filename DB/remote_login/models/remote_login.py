from sqlmodel import Field, SQLModel

class RemoteLogin(SQLModel,table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)
