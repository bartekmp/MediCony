"""
Pharma database client.
"""

import datetime
from typing import List, Optional

from pharmaradar import Medicine as PharmaRadarMedicine
from pharmaradar import MedicineDatabaseInterface
from sqlalchemy.exc import SQLAlchemyError

from src.database.base_db import BaseDbLogic
from src.logger import log
from src.models import MedicineModel


class PharmaDbClient(BaseDbLogic, MedicineDatabaseInterface):
    def __init__(self):
        super().__init__("Medicine")

    def _row_to_medicine(self, row: MedicineModel) -> PharmaRadarMedicine:
        return PharmaRadarMedicine(
            id=row.id,
            name=row.name,
            dosage=row.dosage,
            amount=row.amount,
            location=row.location,
            radius_km=row.radius_km,
            max_price=row.max_price,
            min_availability=row.min_availability,
            title=row.title,
            created_at=row.created_at,
            last_search_at=row.last_search_at,
            active=row.active,
        )

    def save_medicine(self, medicine: PharmaRadarMedicine) -> int:
        with self._lock:
            try:
                with self.get_session() as session:
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

    def get_medicine(self, medicine_id: int) -> Optional[PharmaRadarMedicine]:
        with self._lock:
            try:
                with self.get_session() as session:
                    row = session.query(MedicineModel).filter(MedicineModel.id == medicine_id).first()
                    return self._row_to_medicine(row) if row else None
            except SQLAlchemyError as e:
                log.error(f"Error getting medicine: {e}")
                return None

    def get_medicines(self) -> List[PharmaRadarMedicine]:
        with self._lock:
            try:
                with self.get_session() as session:
                    return [self._row_to_medicine(row) for row in session.query(MedicineModel).all()]
            except SQLAlchemyError as e:
                log.error(f"Error getting medicines: {e}")
                return []

    def remove_medicine(self, medicine_id: int) -> bool:
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
        *,
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
        with self._lock:
            try:
                with self.get_session() as session:
                    if not session.query(MedicineModel).filter(MedicineModel.id == medicine_id).first():
                        return False

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

                    if update_data:
                        session.query(MedicineModel).filter_by(id=medicine_id).update(update_data)
                    session.commit()
                    return True
            except SQLAlchemyError as e:
                log.error(f"Error updating medicine: {e}")
                return False
