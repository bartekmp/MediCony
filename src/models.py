"""
SQLAlchemy models for MediCony application.
"""

from typing import Any, Dict

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MedicoverWatchModel(Base):
    __tablename__ = "watch"

    id = Column(Integer, primary_key=True)
    region = Column(Integer)
    city = Column(String(255))
    specialty = Column(String(255))  # stored as comma-separated string
    clinic = Column(Integer)
    doctor = Column(Integer)
    startDate = Column(Date, name="startdate")
    endDate = Column(Date, name="enddate")
    timeRange = Column(String(255), name="timerange")
    autobook = Column(Boolean)
    exclusions = Column(Text)
    type = Column(String(50))
    account = Column(String(64))  # Medicover account alias

    def to_dict(self) -> Dict[str, Any]:
        """Convert watch to dictionary."""
        return {
            "id": self.id,
            "region": self.region,
            "city": self.city,
            "specialty": self.specialty,
            "clinic": self.clinic,
            "doctor": self.doctor,
            "startDate": self.startDate,
            "endDate": self.endDate,
            "timeRange": self.timeRange,
            "autobook": self.autobook,
            "exclusions": self.exclusions,
            "type": self.type,
            "account": self.account,
        }


class MedicoverAppointmentModel(Base):
    __tablename__ = "appointment"

    id = Column(Integer, primary_key=True)
    clinic = Column(Integer)
    doctor = Column(Integer)
    date = Column(DateTime)
    specialty = Column(Integer)
    visitType = Column(String(255), name="visittype")
    bookingString = Column(Text, name="bookingstring")
    bookingIdentifier = Column(String(255), name="bookingidentifier")
    account = Column(String(64))

    def to_dict(self) -> Dict[str, Any]:
        """Convert appointment to dictionary."""
        return {
            "id": self.id,
            "clinic": self.clinic,
            "doctor": self.doctor,
            "date": self.date,
            "specialty": self.specialty,
            "visitType": self.visitType,
            "bookingString": self.bookingString,
            "bookingIdentifier": self.bookingIdentifier,
            "account": self.account,
        }


class MedicineModel(Base):
    __tablename__ = "medicine"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    dosage = Column(String(255))
    amount = Column(String(255))
    location = Column(String(255), nullable=False)
    radius_km = Column(Float, default=10)
    max_price = Column(Float)
    min_availability = Column(String(50), default="low")
    title = Column(String(255))
    created_at = Column(DateTime)
    last_search_at = Column(DateTime)
    active = Column(Boolean, default=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert medicine to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "dosage": self.dosage,
            "amount": self.amount,
            "location": self.location,
            "radius_km": self.radius_km,
            "max_price": self.max_price,
            "min_availability": self.min_availability,
            "title": self.title,
            "created_at": self.created_at,
            "last_search_at": self.last_search_at,
            "active": self.active,
        }
