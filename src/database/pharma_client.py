"""
Pharma database client.
"""

import datetime
from typing import List, Optional, Tuple

from pharmaradar import Medicine as PharmaRadarMedicine
from pharmaradar import MedicineDatabaseInterface

from src.database.pharma_db import PharmaDbLogic


class PharmaDbClient(MedicineDatabaseInterface):
    def __init__(self):
        # db_path is ignored since we're using PostgreSQL
        self.db = PharmaDbLogic()

    def _parse_row_to_medicine(self, row: Tuple) -> PharmaRadarMedicine:
        """Convert a database row to a Medicine object."""
        medicine_data = {
            "id": row[0],
            "name": row[1],
            "dosage": row[2],
            "amount": row[3],
            "location": row[4],
            "radius_km": row[5],
            "max_price": row[6],
            "min_availability": row[7],
            "title": row[8],
            "created_at": datetime.datetime.fromisoformat(row[9]) if row[9] else None,
            "last_search_at": datetime.datetime.fromisoformat(row[10]) if row[10] else None,
            "active": row[11],
        }
        return PharmaRadarMedicine(**medicine_data)

    def get_medicine(self, medicine_id: int) -> Optional[PharmaRadarMedicine]:
        row = self.db.get_medicine(medicine_id)
        if row is None:
            return None
        return self._parse_row_to_medicine(row)

    def get_medicines(self) -> List[PharmaRadarMedicine]:
        res = self.db.get_medicines()
        medicines = []
        for medicine_row in res:
            medicines.append(self._parse_row_to_medicine(medicine_row))
        return medicines

    def remove_medicine(self, medicine_id: int) -> bool:
        return self.db.remove_medicine(medicine_id)

    def save_medicine(self, medicine: PharmaRadarMedicine) -> int:
        return self.db.save_medicine(medicine)

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
        return self.db.update_medicine(
            medicine_id,
            name,
            dosage,
            amount,
            location,
            radius_km,
            max_price,
            min_availability,
            title,
            last_search_at,
            active,
        )
