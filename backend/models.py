from sqlalchemy import Column, Integer, String
from database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    location = Column(String, nullable=False)
    union = Column(String, nullable=True)
    salary_step = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class PreValidation(Base):
    __tablename__ = "pre_validations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    action_type = Column(String, nullable=False)  # hire, transfer, title_change, termination
    status = Column(String, nullable=False, default="pending")  # pending, approved, rejected
    comments = Column(String, nullable=True)

    # Relationship
    employee = relationship("Employee")

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class DP2001Request(Base):
    __tablename__ = "dp2001_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    prevalidation_id = Column(Integer, ForeignKey("pre_validations.id"), nullable=False)
    action_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="submitted")  # submitted, processing, completed, rejected
    comments = Column(String, nullable=True)

    employee = relationship("Employee")
    prevalidation = relationship("PreValidation")

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)  # e.g., "dp2001_status_change"
    entity_type = Column(String, nullable=False)  # "DP2001", "PreValidation"
    entity_id = Column(Integer, nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
