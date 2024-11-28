from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class Resource(Base):
    __tablename__ = "resource"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32))

    def __repr__(self):
        return f"[{self.id!r}] {self.name!r}"


engine = create_engine('sqlite:///:memory:', echo=True)

Base.metadata.create_all(engine)

