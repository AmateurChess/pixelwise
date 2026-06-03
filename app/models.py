import os
from dotenv import load_dotenv

load_dotenv()
from sqlalchemy import (Column, Integer, String,
Float, DateTime)
from sqlalchemy.orm import declarative_base
from datetime import datetime
Base = declarative_base()
class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True)
    prediction = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime,
    default=datetime.utcnow)


import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
