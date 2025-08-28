import datetime
import sqlite3
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

from src.id_value_util import IdsValues, IdValue

WatchExclusions = Optional[dict[str, list[str]]]

# Constants for general practitioner specialties
GENERAL_PRACTITIONER_SPECIALTIES = [9, 1586, 7338]  # IDs of general practitioner specialties
GENERAL_PRACTITIONER_SPECIALTIES_STR = ",".join(
    map(str, GENERAL_PRACTITIONER_SPECIALTIES)
)  # String representation of GP specialties
GENERAL_PRACTITIONER_SPECIALTIES_LABEL = "General Practitioner - Medycyna ogólna"  # Label for GP specialties


class WatchActiveStatus(StrEnum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    EXPIRED = "Expired"


class WatchType(StrEnum):
    STANDARD = "Standard"
    EXAMINATION = "DiagnosticProcedure"


def parse_exclusions(exclusions: Optional[str]) -> Optional[dict[str, list[str]]]:
    """
    Parse a string of exclusions into a dictionary.
    The string should be in the format "key1:value1,value2;key2:value3,value4;..."
    """
    if not exclusions:
        return None

    exclusion_dict = {}
    for exclusion in exclusions.split(";"):
        key, values = exclusion.split(":")
        if key and values:
            exclusion_dict[key] = values.split(",")
        elif key:
            exclusion_dict[key] = []
        else:
            continue

    return exclusion_dict if exclusion_dict else None


def flatten_exclusions(exclusions: dict) -> str:
    """Flatten a dictionary of exclusions into a string."""
    return ";".join(f"{k}:{','.join(v)}" for k, v in exclusions.items())


class WatchTimeRange:
    start_time: datetime.time
    end_time: datetime.time | None = None
    is_endless: bool = True

    def __init__(self, timestr: str):
        if not timestr:
            raise ValueError("Invalid time format, expected HH:MM:SS[-HH:MM:SS]")

        timestr.strip()
        if "-" in timestr:
            start, end = timestr.split("-")
            self.start_time = datetime.time.fromisoformat(start)
            if end == "*":
                self.is_endless = True
            else:
                self.end_time = datetime.time.fromisoformat(end)
                if self.end_time < self.start_time:
                    raise ValueError("End time cannot be earlier than the start time")

                self.is_endless = False
        else:
            self.start_time = datetime.time.fromisoformat(timestr)

    def __eq__(self, other) -> bool:
        if self.is_endless and other.is_endless:
            return self.start_time == other.start_time
        if not (self.is_endless and other.is_endless):
            return self.start_time == other.start_time and self.end_time == other.end_time
        else:
            return False

    def __str__(self) -> str:
        if self.is_endless:
            return f"{self.start_time}-*"
        return f"{self.start_time}-{self.end_time}"

    def __conform__(self, protocol) -> str:
        if protocol is sqlite3.PrepareProtocol:
            return str(self)
        return ""

    @staticmethod
    def midnight() -> "WatchTimeRange":
        return WatchTimeRange("00:00:00")

    @staticmethod
    def default() -> "WatchTimeRange":
        return WatchTimeRange.midnight()


def is_within(range: WatchTimeRange, time_point: datetime.time) -> bool:
    if range.is_endless:
        return range.start_time <= time_point
    return range.start_time <= time_point <= (range.end_time if range.end_time else datetime.time.max)


@dataclass
class Watch:
    """
    Domain model representing a medical appointment watch.

    A watch monitors for available appointments based on specified criteria
    such as region, specialty, clinic, doctor, and time constraints.
    """

    id: int
    region: IdValue
    city: str
    specialty: IdsValues
    clinic: Optional[IdValue] = None
    doctor: Optional[IdValue] = None
    start_date: datetime.date = field(default_factory=datetime.date.today)
    end_date: Optional[datetime.date] = None
    time_range: WatchTimeRange = field(default_factory=WatchTimeRange.default)
    auto_book: bool = False
    exclusions: Optional[WatchExclusions] = None
    type: WatchType = WatchType.STANDARD
    account: str | None = None  # Which Medicover account to use (alias from config)

    def __post_init__(self):
        """Validate and normalize data after initialization."""
        # Ensure end_date is set to max if None
        if self.end_date is None:
            self.end_date = datetime.date.max

        # Validate date range
        if self.start_date > self.end_date:
            raise ValueError("Start date cannot be after end date")

        # Ensure specialty is a list
        if not isinstance(self.specialty, list):
            raise ValueError("Specialty must be a list of IdValue objects")

    @classmethod
    def from_tuple(cls, data: tuple) -> "Watch":
        """
        Create a Watch instance from a tuple of data for backward compatibility.

        The tuple should contain:
        0: watch ID (int)
        1: region ID and name (tuple of int and str)
        2: city name (str)
        3: list of specialty IDs (list of int)
        4: clinic ID and name (tuple of int and str or None)
        5: doctor ID and name (tuple of int and str or None)
        6: start date (str in YYYY-MM-DD format or datetime.date)
        7: end date (str in YYYY-MM-DD format or datetime.date, optional)
        8: time range (str in HH:MM:SS[-HH:MM:SS] format or WatchTimeRange, optional)
        9: auto book flag (bool, optional)
        10: exclusions (str in "key:value1,value2;key2:value3,value4" format or None, optional)
        11: watch type (str, optional, defaults to "Standard")
        12: account alias (str, optional)
        """
        if len(data) < 6 or len(data) > 13:
            raise ValueError("Cannot initialize Watch object, the data tuple is in improper format")

        # Required fields
        watch_id = data[0]
        region = IdValue(data[1])
        city = data[2]
        specialty = [IdValue(id) for id in data[3]]
        clinic = IdValue(data[4]) if data[4] else None
        doctor = IdValue(data[5]) if data[5] else None

        # Parse start date
        start_date = data[6] if len(data) > 6 else datetime.date.today()
        if isinstance(start_date, str):
            start_date = datetime.date.fromisoformat(start_date)

        # Optional fields with defaults
        end_date = None
        time_range = WatchTimeRange.default()
        auto_book = False
        exclusions = None
        watch_type = WatchType.STANDARD

        # Parse optional fields based on tuple length
        if len(data) > 7 and data[7]:
            end_date = data[7]
            if isinstance(end_date, str):
                end_date = datetime.date.fromisoformat(end_date)

        if len(data) > 8 and data[8]:
            time_range = data[8]
            if isinstance(time_range, str):
                time_range = WatchTimeRange(time_range)

        if len(data) > 9:
            auto_book = data[9]

        if len(data) > 10:
            exclusions = parse_exclusions(data[10])

        if len(data) > 11 and data[11]:
            watch_type = WatchType(data[11])

        account = None
        if len(data) > 12:
            account = data[12]

        return cls(
            id=watch_id,
            region=region,
            city=city,
            specialty=specialty,
            clinic=clinic,
            doctor=doctor,
            start_date=start_date,
            end_date=end_date,
            time_range=time_range,
            auto_book=auto_book,
            exclusions=exclusions,
            type=watch_type,
            account=account,
        )

    @classmethod
    def create(
        cls,
        watch_id: int,
        region: IdValue,
        city: str,
        specialty: IdsValues,
        clinic: Optional[IdValue] = None,
        doctor: Optional[IdValue] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        time_range: Optional[WatchTimeRange] = None,
        auto_book: bool = False,
        exclusions: Optional[WatchExclusions] = None,
        watch_type: WatchType = WatchType.STANDARD,
        account: Optional[str] = None,
    ) -> "Watch":
        """
        Factory method for creating a Watch with proper defaults.

        This method provides a clean, type-safe way to create Watch instances
        without relying on tuple unpacking.
        """
        return cls(
            id=watch_id,
            region=region,
            city=city,
            specialty=specialty,
            clinic=clinic,
            doctor=doctor,
            start_date=start_date or datetime.date.today(),
            end_date=end_date,
            time_range=time_range or WatchTimeRange.default(),
            auto_book=auto_book,
            exclusions=exclusions,
            type=watch_type,
            account=account,
        )

    def is_active(
        self, activity_threshold_days: int = 14, starting_point: Optional[datetime.date] = None
    ) -> WatchActiveStatus:
        # Check if the watch is active based on the current date
        # If the watch's start date is in the future, it's not yet active or the end date is in the past, it is expired
        starting_point = starting_point or datetime.date.today()
        threshold = starting_point + datetime.timedelta(days=activity_threshold_days)

        if self.start_date > threshold:
            return WatchActiveStatus.INACTIVE
        if self.end_date and self.end_date < starting_point:
            return WatchActiveStatus.EXPIRED
        return WatchActiveStatus.ACTIVE

    def _get_descriptive_info(self) -> dict[str, Any]:
        # Prepare a dictionary with watch description, containing all the relevant information and IDs
        watch_description = {"id": self.id, "city": self.city, "type": self.type.value, "specialty": ""}

        if self.region.value:
            watch_description["region"] = f"{self.region.value} ({self.region.id})"
        else:
            watch_description["region"] = f"{self.region.id}"

        for specialty in self.specialty:
            if specialty.value:
                watch_description["specialty"] += f"{specialty.value} ({specialty.id}), "
            else:
                watch_description["specialty"] += f"{specialty.id}, "
        if watch_description["specialty"][-2:] == ", ":  # Remove trailing comma
            watch_description["specialty"] = watch_description["specialty"][:-2]
        if watch_description["specialty"] == GENERAL_PRACTITIONER_SPECIALTIES_STR:  # General practitioner specialties
            watch_description["specialty"] = "GP (" + watch_description["specialty"] + ")"

        if not self.clinic:
            watch_description["clinic"] = "any"
        elif self.clinic.value:
            watch_description["clinic"] = f"{self.clinic.value} ({self.clinic.id})"
        else:
            watch_description["clinic"] = f"{self.clinic.id}"

        if not self.doctor:
            watch_description["doctor"] = "any"
        elif self.doctor.value:
            watch_description["doctor"] = f"{self.doctor.value} ({self.doctor.id})"
        else:
            watch_description["doctor"] = f"{self.doctor.id if self.doctor.id else 'any'}"

        watch_description["start_date"] = self.start_date
        watch_description["end_date"] = self.end_date
        if self.end_date == datetime.date.max:
            watch_description["end_date"] = "*"

        watch_description["time_range"] = self.time_range
        watch_description["auto_book"] = self.auto_book
        watch_description["exclusions"] = flatten_exclusions(self.exclusions) if self.exclusions else None
        watch_description["account"] = self.account if self.account else "default"
        return watch_description

    def __str__(self) -> str:
        d = self._get_descriptive_info()
        return f"ID {d['id']}\nRegion: {d['region']}\nCity: {d['city']}\nType: {d['type']}\nSpecialty: {d['specialty']}\nClinic: {d['clinic']}\nDoctor: {d['doctor']}\nDate range: {d['start_date']}–{d['end_date']}\nTime range: {d['time_range']}\nAutobook: {bool(d["auto_book"])}\nExclusions: {d['exclusions']}\nAccount: {d['account']}"

    def short_str(self) -> str:
        d = self._get_descriptive_info()
        return (
            f"ID {d['id']}; r: {d['region']}; ci: {d['city']}; t: {d['type']}; s: {d['specialty']}; cl: {d['clinic']}; "
            f"d: {d['doctor']}; dr: {d['start_date']}–{d['end_date']}; tr: {d['time_range']}; ab: {bool(d['auto_book'])}; "
            f"excl: {d['exclusions']}; acc: {d['account']}"
        )
