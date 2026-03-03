from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

class MatrixItem(Base):
    __tablename__ = "matrix_items"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer) # Simplified for local testing
    code = Column(String(50))
    description = Column(Text)
    unit = Column(String(20))
    quantity = Column(Numeric(18, 4)) # Neodata precision

DATABASE_URL = "postgresql://admin:password123@localhost:5432/neocloud_erp"
engine = create_engine(DATABASE_URL)

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Schema Synchronized: matrix_items table is ready.")