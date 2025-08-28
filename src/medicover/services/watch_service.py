"""
Watch service for managing appointment watches.
"""

import datetime

from src.database import MedicoverDbClient
from src.id_value_util import IdValue
from src.logger import log
from src.medicover.api_client import MediAPI
from src.medicover.watch import Watch, WatchTimeRange, WatchType, flatten_exclusions


class WatchService:
    """Service layer for watch-related operations."""

    def __init__(self, api_client: MediAPI, db_client: MedicoverDbClient):
        self.api_client = api_client
        self.db_client = db_client

    async def get_all_watches(self) -> list[Watch]:
        """Get all watches from database with metadata"""
        watches = self.db_client.get_watches()
        for watch in watches:
            await self.api_client.update_watch_metadata(watch)
        return watches

    def get_watch(self, watch_id: int) -> Watch | None:
        """Get a single watch by ID"""
        return self.db_client.get_watch(watch_id)

    def add_watch(self, **kwargs) -> int:
        """Add a new watch with provided parameters and persist it.

        Expected kwargs: region, city, specialty, clinic, doctor, exclusions, type, start_date,
        end_date, auto_book, time_range, account
        """
        region = kwargs.get("region")
        city = kwargs.get("city", "")
        specialty = kwargs.get("specialty", [])
        clinic = kwargs.get("clinic")
        doctor = kwargs.get("doctor")
        exclusions = kwargs.get("exclusions")
        watch_type = kwargs.get("type", WatchType.STANDARD)
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date", datetime.date.max)
        auto_book = kwargs.get("auto_book", False)
        time_range = kwargs.get("time_range", "")
        account = kwargs.get("account")
        
        try:
            if region is None:
                raise ValueError("Region is required")
            if not isinstance(region, IdValue):
                if isinstance(region, dict) and "id" in region and "value" in region:
                    region = IdValue(id=region["id"], value=region["value"])
                elif isinstance(region, (int, str)):
                    region = IdValue(id=int(region), value="")
                else:
                    raise ValueError(f"Invalid region type: {type(region)}")

            if clinic is not None and not isinstance(clinic, IdValue):
                if isinstance(clinic, dict) and "id" in clinic and "value" in clinic:
                    clinic = IdValue(id=clinic["id"], value=clinic["value"])
                elif isinstance(clinic, (int, str)):
                    clinic = IdValue(id=int(clinic), value="")
                else:
                    clinic = None

            if doctor is not None and not isinstance(doctor, IdValue):
                if isinstance(doctor, dict) and "id" in doctor and "value" in doctor:
                    doctor = IdValue(id=doctor["id"], value=doctor["value"])
                elif isinstance(doctor, (int, str)):
                    doctor = IdValue(id=int(doctor), value="")
                else:
                    doctor = None

            specialty_list: list[IdValue] = []
            if specialty:
                if not isinstance(specialty, list):
                    specialty = [specialty]
                for spec in specialty:
                    if isinstance(spec, IdValue):
                        specialty_list.append(spec)
                    elif isinstance(spec, dict) and "id" in spec and "value" in spec:
                        specialty_list.append(IdValue(id=spec["id"], value=spec["value"]))
                    elif isinstance(spec, (int, str)):
                        specialty_list.append(IdValue(id=int(spec), value=""))

            if isinstance(time_range, str) and time_range:
                try:
                    time_range_obj = WatchTimeRange(time_range)
                except ValueError:
                    time_range_obj = WatchTimeRange("00:00-23:59")
            else:
                time_range_obj = WatchTimeRange("00:00-23:59")

            if isinstance(watch_type, str):
                try:
                    watch_type_enum = WatchType(watch_type)
                except ValueError:
                    watch_type_enum = WatchType.STANDARD
            else:
                watch_type_enum = watch_type if isinstance(watch_type, WatchType) else WatchType.STANDARD

            watch = Watch(
                id=0,
                region=region,
                city=str(city) if city else "",
                specialty=specialty_list,
                clinic=clinic,
                doctor=doctor,
                start_date=start_date if start_date else datetime.date.today(),
                end_date=end_date if end_date else datetime.date.max,
                time_range=time_range_obj,
                auto_book=bool(auto_book),
                exclusions=exclusions,
                type=watch_type_enum,
                account=account,
            )

            watch_id = self.db_client.save_watch(watch)
            return watch_id or 0
        except Exception as e:
            log.error(f"Error creating watch: {e}")
            return 0

    def update_watch(self, watch: Watch, **kwargs) -> bool:
        watch_id = watch.id
        """Update an existing watch"""
        # First get the existing watch
        existing_watch = self.db_client.get_watch(watch_id)
        if not existing_watch:
            raise ValueError(f"Watch with ID {watch_id} not found")

        # Process time_range if it's provided
        time_range = kwargs.get("time_range")
        if isinstance(time_range, str):
            time_range = WatchTimeRange(time_range)
            kwargs["time_range"] = str(time_range)

        # Process exclusions if they're provided
        exclusions = kwargs.get("exclusions")
        if isinstance(exclusions, dict):
            kwargs["exclusions"] = flatten_exclusions(exclusions)

        # Set default account if not provided
        if "account" not in kwargs:
            kwargs["account"] = "default"

        # Update in database
        return self.db_client.update_watch(watch_id, **kwargs)

    def remove_watch(self, watch_id: int):
        """Remove a watch by ID"""
        return self.db_client.remove_watch(watch_id)

    async def list_available_filters(self, filter_type: str, **kwargs):
        """
        Get available filters for creating/updating watches.
        Filter types: regions, cities, specialties, clinics, doctors
        """
        region = kwargs.get("region")
        specialty = kwargs.get("specialty")
        search_type = kwargs.get("search_type", WatchType.STANDARD)

        # Fetch filters from API
        filters_data = await self.api_client.find_filters(region=region, specialty=specialty, search_type=search_type)

        # Return the requested filter type
        filter_type = filter_type.lower()
        if filter_type == "regions":
            return filters_data.get("regions", [])
        elif filter_type == "cities":
            # This might need special handling as cities are typically within regions
            # For now, extract unique cities from clinics
            clinics = filters_data.get("clinics", [])
            cities = set()
            for clinic in clinics:
                if "name" in clinic:
                    # Extract city from clinic name (might need adaptation)
                    city = clinic["name"].split(",")[0].strip()
                    cities.add(city)
            return sorted(list(cities))
        elif filter_type == "specialties":
            return filters_data.get("specialties", [])
        elif filter_type == "clinics":
            return filters_data.get("clinics", [])
        elif filter_type == "doctors":
            return filters_data.get("doctors", [])
        else:
            return []
