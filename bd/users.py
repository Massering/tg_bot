from sqlalchemy import create_engine, MetaData, Table, Integer, String, \
    Column, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Post(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    class_id = Column(String(50), nullable=False)
    citizen = Column(Boolean, nullable=False)
    lunch = Column(Integer)
    breakfast = Column(Integer, nullable=False)
    afternoon_snack = Column(Integer, nullable=False)
    school_visit = Column(Integer)
    reason = Column(String(200))
