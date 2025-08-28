"""
Pharma-specific database logic using SQLAlchemy for PostgreSQL.
"""

import datetime
from typing import List, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError

from src.database.base_db import BaseDbLogic
from src.logger import log
from src.models import MedicineModel


class PharmaDbLogic(BaseDbLogic):
    def __init__(self):
        super().__init__()

    def save_medicine(self, medicine) -> int:
        """Save a medicine to the database and return its ID."""
        with self._lock:
            try:
                with self.get_session() as session:
                    # Convert enum to string value if needed
                    min_availability_value = medicine.min_availability
                    if hasattr(min_availability_value, "value"):
                        min_availability_value = min_availability_value.value

                    new_medicine = MedicineModel(
                        name=medicine.name,
                        dosage=medicine.dosage,
                        amount=medicine.amount,
                        location=medicine.location,
                        radius_km=medicine.radius_km,
                        max_price=medicine.max_price,
                        min_availability=min_availability_value,
                        title=medicine.title,
                        created_at=medicine.created_at,
                        last_search_at=medicine.last_search_at,
                        active=medicine.active,
                    )
                    session.add(new_medicine)
                    session.commit()
                    session.refresh(new_medicine)
                    return new_medicine.id  # type: ignore
            except SQLAlchemyError as e:
                log.error(f"Error saving medicine: {e}")
                raise

    def get_medicine(self, medicine_id: int) -> Optional[Tuple]:
        """Get a medicine by ID."""
        with self._lock:
            try:
                with self.get_session() as session:
                    medicine = session.query(MedicineModel).filter(MedicineModel.id == medicine_id).first()
                    if medicine:
                        return (
                            medicine.id,
                            medicine.name,
                            medicine.dosage,
                            medicine.amount,
                            medicine.location,
                            medicine.radius_km,
                            medicine.max_price,
                            medicine.min_availability,
                            medicine.title,
                            medicine.created_at.isoformat() if medicine.created_at is not None else None,
                            medicine.last_search_at.isoformat() if medicine.last_search_at is not None else None,
                            medicine.active,
                        )
                    return None
            except SQLAlchemyError as e:
                log.error(f"Error getting medicine: {e}")
                return None

    def get_medicines(self) -> List[Tuple]:
        """Get all medicines."""
        with self._lock:
            try:
                with self.get_session() as session:
                    medicines = session.query(MedicineModel).all()
                    return [
                        (
                            m.id,
                            m.name,
                            m.dosage,
                            m.amount,
                            m.location,
                            m.radius_km,
                            m.max_price,
                            m.min_availability,
                            m.title,
                            m.created_at.isoformat() if m.created_at is not None else None,
                            m.last_search_at.isoformat() if m.last_search_at is not None else None,
                            m.active,
                        )
                        for m in medicines
                    ]
            except SQLAlchemyError as e:
                log.error(f"Error getting medicines: {e}")
                return []

    def remove_medicine(self, medicine_id: int) -> bool:
        """Remove a medicine from the database."""
        with self._lock:
            try:
                with self.get_session() as session:
                    result = session.query(MedicineModel).filter(MedicineModel.id == medicine_id).delete()
                    session.commit()
                    return result > 0
            except SQLAlchemyError as e:
                log.error(f"Error removing medicine: {e}")
                return False

    def update_medicine(
        self,
        medicine_id: int,
        name: Optional[str] = None,
        dosage: Optional[str] = None,
        amount: Optional[str] = None,
        location: Optional[str] = None,
        radius_km: Optional[float] = None,
        max_price: Optional[float] = None,
        min_availability: Optional[str] = None,
        title: Optional[str] = None,
        last_search_at: Optional[datetime.datetime] = None,
        active: Optional[bool] = None,
    ) -> bool:
        """Update a medicine in the database."""
        with self._lock:
            try:
                with self.get_session() as session:
                    medicine = session.query(MedicineModel).filter(MedicineModel.id == medicine_id).first()
                    if not medicine:
                        return False

                    # Build update dictionary for non-None values
                    update_data = {}
                    if name is not None:
                        update_data["name"] = name
                    if dosage is not None:
                        update_data["dosage"] = dosage
                    if amount is not None:
                        update_data["amount"] = amount
                    if location is not None:
                        update_data["location"] = location
                    if radius_km is not None:
                        update_data["radius_km"] = radius_km
                    if max_price is not None:
                        update_data["max_price"] = max_price
                    if min_availability is not None:
                        # Convert enum to string value if needed
                        min_availability_value = min_availability
                        if hasattr(min_availability_value, "value"):
                            min_availability_value = min_availability_value.value  # type: ignore
                        update_data["min_availability"] = min_availability_value
                    if title is not None:
                        update_data["title"] = title
                    if last_search_at is not None:
                        update_data["last_search_at"] = last_search_at
                    if active is not None:
                        update_data["active"] = active

                    # Perform the update using the proper SQLAlchemy method
                    if update_data:
                        session.query(MedicineModel).filter_by(id=medicine_id).update(update_data)

                    session.commit()
                    return True
            except SQLAlchemyError as e:
                log.error(f"Error updating medicine: {e}")
                return False
