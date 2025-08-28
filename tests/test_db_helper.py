"""
Test database logic using SQLAlchemy with SQLite for testing.
"""
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.medicover_db import MedicoverDbLogic
from src.models import Base


class SqliteDbLogic(MedicoverDbLogic):
    """Test version of MedicoverDbLogic that uses SQLite instead of PostgreSQL."""
    
    def __init__(self, db_path: str = ":memory:"):
        # Override the parent __init__ to use SQLite instead of calling super().__init__()
        self._lock = __import__('threading').RLock()
        
        # Create SQLite database URL
        if db_path == ":memory:":
            database_url = "sqlite:///:memory:"
        else:
            database_url = f"sqlite:///{db_path}"
        
        try:
            # Create engine
            self.engine = create_engine(database_url, echo=False)
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            # Don't call clear_db for test databases to avoid timezone issues
            
        except Exception as e:
            raise Exception(f"Failed to connect to test SQLite database: {e}")


class SqliteDbClient:
    """Test version of DbClient that uses SqliteDbLogic."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db = SqliteDbLogic(db_path or ":memory:")

    def _parse_row_to_watch(self, row):
        from src.medicover.watch import Watch as MedicoverWatch
        # Convert a database row to a Watch object
        # Handle the case where multiple specialties are stored as a comma-separated string
        specialties = [int(w) for w in row[3].split(",")]
        # Insert specialties into the watch tuple where they belong, between region and clinic
        watch_tuple = row[:3] + (specialties,) + row[4:]
        return MedicoverWatch.from_tuple(watch_tuple)

    def get_watch(self, watch_id: int):
        row = self.db.get_watch(watch_id)
        if row is None:
            return None
        return self._parse_row_to_watch(row)

    def get_watches(self):
        res = self.db.get_watches()
        watches = []
        for watch in res:
            watches.append(self._parse_row_to_watch(watch))
        return watches

    def remove_watch(self, watch_id: int) -> bool:
        return self.db.remove_watch(watch_id)

    def save_watch(self, watch) -> int:
        return self.db.save_watch(watch)

    def update_appointment(self, appointment):
        if not self.db.appointment_exists(appointment):
            self.db.add_appointment_history(appointment)
        else:
            self.db.update_appointment(appointment)

    def save_appointments_and_filter_old(self, appointments):
        new_appointments = []
        for appointment in appointments:
            # Check if appointment in the local database
            if not self.db.appointment_exists(appointment):
                # If not, append it to the return list and add it to the local database
                new_appointments.append(appointment)
                self.db.add_appointment_history(appointment)

        return new_appointments

    def get_booked_appointments(self):
        from src.medicover.appointment import Appointment as MedicoverAppointment
        appointments = self.db.get_booked_appointments()
        # Return a list of pairs id-appointment, id is required for cancelling an appointment via the app
        return [(ap[0], MedicoverAppointment.initialize_from_tuple(ap)) for ap in appointments]

    def update_watch(
        self,
        watch_id: int,
        city: Optional[str] = None,
        clinic_id: Optional[int] = None,
        start_date = None,
        end_date = None,
        time_range: Optional[str] = None,
        exclusions: Optional[str] = None,
        auto_book: Optional[bool] = None,
    ) -> bool:
        return self.db.update_watch(
            watch_id,
            city,
            clinic_id,
            start_date,
            end_date,
            time_range,
            exclusions,
            auto_book,
        )
