from sqlalchemy import create_engine, MetaData, Table, Integer, String, \
    Column, DateTime, ForeignKey, Numeric
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Post(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    class_id = Column(String(50), nullable=False)
    published = Column(String(200), nullable=False, unique=True)
    created_on = Column(DateTime(), default=datetime.now)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)
