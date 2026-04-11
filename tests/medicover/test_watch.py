"""
Tests for the Watch domain model and related functionality.

This module contains tests for the Watch class, WatchTimeRange, and related
helper functions to ensure correct initialization, validation and operations.
"""

from datetime import date, time, timedelta

from pytest import raises

from src.id_value_util import IdValue
from src.medicover.watch import Watch, WatchActiveStatus, WatchTimeRange, WatchType, is_within, parse_exclusions


def test_watch_invalid_initialization():
    """Test that Watch initialization fails with invalid arguments."""
    # Act & Assert
    with raises(TypeError):
        Watch(id=1)  # Missing required fields: region, city, specialty


def test_watch_initialization_with_defaults():
    """Test initializing a Watch with minimal arguments and default values."""
    watch = Watch(
        id=1,
        region=IdValue(2),
        city="aaa",
        specialty=[IdValue(3)],
        clinic=IdValue(4),
        doctor=IdValue(5),
        start_date=date.min,
    )

    assert watch.id == 1
    assert watch.region is not None and watch.region.id == 2
    assert watch.city == "aaa"
    assert watch.specialty[0].id == 3
    assert watch.clinic is not None and watch.clinic.id == 4
    assert watch.doctor is not None and watch.doctor.id == 5
    assert watch.start_date == date.min


def test_watch_initialization_with_defaults_multiple_specialties():
    """Test initializing a Watch with multiple specialties."""
    watch = Watch(
        id=1,
        region=IdValue(2),
        city="aaa",
        specialty=[IdValue(3), IdValue(6), IdValue(9)],
        clinic=IdValue(4),
        doctor=IdValue(5),
        start_date=date.min,
    )

    assert watch.id == 1
    assert watch.region is not None and watch.region.id == 2
    assert watch.city == "aaa"
    assert watch.specialty[0].id == 3
    assert watch.specialty[1].id == 6
    assert watch.specialty[2].id == 9
    assert watch.clinic is not None and watch.clinic.id == 4
    assert watch.doctor is not None and watch.doctor.id == 5
    assert watch.start_date == date.min


def test_watch_initialization_full_with_dedicated_types():
    """Test initializing a Watch with full set of parameters using dedicated types."""
    watch = Watch(
        id=11,
        region=IdValue(22),
        city="bbb",
        specialty=[IdValue(33)],
        clinic=IdValue(44),
        doctor=IdValue(55),
        start_date=date.fromisoformat("2137-09-01"),
        end_date=date.fromisoformat("2137-09-17"),
        time_range=WatchTimeRange("12:12:12-13:13:13"),
        auto_book=False,
    )

    assert watch.id == 11
    assert watch.region is not None and watch.region.id == 22
    assert watch.city == "bbb"
    assert watch.specialty[0].id == 33
    assert watch.clinic is not None and watch.clinic.id == 44
    assert watch.doctor is not None and watch.doctor.id == 55
    assert watch.start_date == date.fromisoformat("2137-09-01")
    assert watch.end_date == date.fromisoformat("2137-09-17")
    assert watch.time_range == WatchTimeRange("12:12:12-13:13:13")
    assert not watch.auto_book


def test_watch_initialization_full_with_dedicated_types_multiple_specialties():
    """Test initializing a Watch with full set of parameters and multiple specialties."""
    watch = Watch(
        id=11,
        region=IdValue(22),
        city="bbb",
        specialty=[IdValue(33), IdValue(66), IdValue(99)],
        clinic=IdValue(44),
        doctor=IdValue(55),
        start_date=date.fromisoformat("2137-09-01"),
        end_date=date.fromisoformat("2137-09-17"),
        time_range=WatchTimeRange("12:12:12-13:13:13"),
        auto_book=False,
    )

    assert watch.id == 11
    assert watch.region is not None and watch.region.id == 22
    assert watch.city == "bbb"
    assert watch.specialty[0].id == 33
    assert watch.specialty[1].id == 66
    assert watch.specialty[2].id == 99
    assert watch.clinic is not None and watch.clinic.id == 44
    assert watch.doctor is not None and watch.doctor.id == 55
    assert watch.start_date == date.fromisoformat("2137-09-01")
    assert watch.end_date == date.fromisoformat("2137-09-17")
    assert watch.time_range == WatchTimeRange("12:12:12-13:13:13")
    assert not watch.auto_book


def test_watch_initialization_full_with_strings():
    """Test initializing a Watch with full set of parameters using string values."""
    watch = Watch(
        id=11,
        region=IdValue(22),
        city="xxxx",
        specialty=[IdValue(33)],
        clinic=IdValue(44),
        doctor=IdValue(55),
        start_date=date.fromisoformat("2137-09-01"),
        end_date=date.fromisoformat("2137-09-17"),
        time_range=WatchTimeRange("12:12:12-13:13:13"),
        auto_book=True,
    )

    assert watch.id == 11
    assert watch.region is not None and watch.region.id == 22
    assert watch.city == "xxxx"
    assert watch.specialty[0].id == 33
    assert watch.clinic is not None and watch.clinic.id == 44
    assert watch.doctor is not None and watch.doctor.id == 55
    assert watch.start_date == date.fromisoformat("2137-09-01")
    assert watch.end_date == date.fromisoformat("2137-09-17")
    assert watch.time_range == WatchTimeRange("12:12:12-13:13:13")
    assert watch.auto_book


def test_watch_to_string():
    """Test the string representation of a Watch object."""
    watch = Watch(
        id=91,
        region=IdValue(92),
        city="zzz",
        specialty=[IdValue(93)],
        clinic=IdValue(94),
        doctor=IdValue(95),
        start_date=date.fromisoformat("2027-02-21"),
        end_date=date.fromisoformat("2027-09-17"),
        time_range=WatchTimeRange("10:30"),
        auto_book=False,
        exclusions=parse_exclusions("doctor:111,222;clinic:333,444"),
        type=WatchType.STANDARD,
    )

    expected = "ID 91\nRegion: 92\nCity: zzz\nType: Standard\nSpecialty: 93\nClinic: 94\nDoctor: 95\nDate range: 2027-02-21–2027-09-17\nTime range: 10:30:00-*\nAutobook: False\nExclusions: doctor:111,222;clinic:333,444\nAccount: default"

    assert str(watch) == expected


def test_watch_to_string_multiple_specialties():
    """Test the string representation of a Watch object with multiple specialties."""
    watch = Watch(
        id=91,
        region=IdValue(92),
        city="zzz",
        specialty=[IdValue(93), IdValue(96), IdValue(99)],
        clinic=IdValue(94),
        doctor=IdValue(95),
        start_date=date.fromisoformat("2027-02-21"),
        end_date=date.fromisoformat("2027-09-17"),
        time_range=WatchTimeRange("10:30"),
        auto_book=False,
        exclusions=None,
        type=WatchType.STANDARD,
    )

    expected = "ID 91\nRegion: 92\nCity: zzz\nType: Standard\nSpecialty: 93, 96, 99\nClinic: 94\nDoctor: 95\nDate range: 2027-02-21–2027-09-17\nTime range: 10:30:00-*\nAutobook: False\nExclusions: None\nAccount: default"

    assert str(watch) == expected


def test_watch_to_string_with_descriptive_values():
    """Test the string representation of a Watch object with descriptive values."""
    watch = Watch(
        id=51,
        region=IdValue(52),
        city="yyy",
        specialty=[IdValue(53)],
        clinic=IdValue(54),
        doctor=IdValue(55),
        start_date=date.fromisoformat("2137-09-01"),
        end_date=date.fromisoformat("2137-09-17"),
        time_range=WatchTimeRange("12:12:12-13:13:13"),
        auto_book=True,
        exclusions=None,
        type=WatchType.EXAMINATION,
    )
    watch.region.value = "region52"
    watch.specialty[0].value = "specialty53"
    if watch.clinic is not None:
        watch.clinic.value = "clinic54"
    if watch.doctor is not None:
        watch.doctor.value = "doctor55"

    expected = "ID 51\nRegion: region52 (52)\nCity: yyy\nType: DiagnosticProcedure\nSpecialty: specialty53 (53)\nClinic: clinic54 (54)\nDoctor: doctor55 (55)\nDate range: 2137-09-01–2137-09-17\nTime range: 12:12:12-13:13:13\nAutobook: True\nExclusions: None\nAccount: default"
    assert str(watch) == expected


def test_watch_to_string_with_descriptive_values_multiple_specialties():
    """Test the string representation of a Watch object with descriptive values and multiple specialties."""
    watch = Watch(
        id=51,
        region=IdValue(52),
        city="yyy",
        specialty=[IdValue(53), IdValue(56), IdValue(59)],
        clinic=IdValue(54),
        doctor=IdValue(55),
        start_date=date.fromisoformat("2137-09-01"),
        end_date=date.fromisoformat("2137-09-17"),
        time_range=WatchTimeRange("12:12:12-13:13:13"),
        auto_book=True,
        exclusions=parse_exclusions("doctor:111,222,333"),
        type=WatchType.EXAMINATION,
    )
    watch.region.value = "region52"
    watch.specialty[0].value = "specialty53"
    watch.specialty[1].value = "specialty56"
    watch.specialty[2].value = "specialty59"
    if watch.clinic is not None:
        watch.clinic.value = "clinic54"
    if watch.doctor is not None:
        watch.doctor.value = "doctor55"

    expected = "ID 51\nRegion: region52 (52)\nCity: yyy\nType: DiagnosticProcedure\nSpecialty: specialty53 (53), specialty56 (56), specialty59 (59)\nClinic: clinic54 (54)\nDoctor: doctor55 (55)\nDate range: 2137-09-01–2137-09-17\nTime range: 12:12:12-13:13:13\nAutobook: True\nExclusions: doctor:111,222,333\nAccount: default"
    assert str(watch) == expected


def test_watch_to_short_str():
    """Test the short string representation of a Watch object."""
    watch = Watch(
        id=51,
        region=IdValue(52),
        city="yyy",
        specialty=[IdValue(53)],
        clinic=IdValue(54),
        doctor=IdValue(55),
        start_date=date.fromisoformat("2137-09-01"),
        end_date=date.fromisoformat("2137-09-17"),
        time_range=WatchTimeRange("12:15:36"),
        auto_book=True,
        exclusions=None,
        type=WatchType.EXAMINATION,
    )
    expected = "ID 51; r: 52; ci: yyy; t: DiagnosticProcedure; s: 53; cl: 54; d: 55; dr: 2137-09-01–2137-09-17; tr: 12:15:36-*; ab: True; excl: None; acc: default"

    assert watch.short_str() == expected


def test_watch_to_short_str_multiple_specialties():
    """Test the short string representation of a Watch object with multiple specialties."""
    watch = Watch(
        id=51,
        region=IdValue(52),
        city="yyy",
        specialty=[IdValue(53), IdValue(56), IdValue(59)],
        clinic=IdValue(54),
        doctor=IdValue(55),
        start_date=date.fromisoformat("2137-09-01"),
        end_date=date.fromisoformat("2137-09-17"),
        time_range=WatchTimeRange("12:15:36"),
        auto_book=True,
        exclusions=parse_exclusions("doctor:777,888,999"),
        type=WatchType.EXAMINATION,
    )
    expected = "ID 51; r: 52; ci: yyy; t: DiagnosticProcedure; s: 53, 56, 59; cl: 54; d: 55; dr: 2137-09-01–2137-09-17; tr: 12:15:36-*; ab: True; excl: doctor:777,888,999; acc: default"

    assert watch.short_str() == expected


def test_watch_active_status():
    """Test the active status determination of a Watch object."""
    starting_point = date.today()
    threshold = 1  # days
    w1 = Watch(
        id=51,
        region=IdValue(52),
        city="yyy",
        specialty=[IdValue(53), IdValue(56), IdValue(59)],
        clinic=IdValue(54),
        doctor=IdValue(55),
        start_date=starting_point + timedelta(days=2),
        end_date=date.fromisoformat("2137-09-17"),
        time_range=WatchTimeRange("12:15:36"),
        auto_book=True,
        type=WatchType.EXAMINATION,
    )
    assert w1.is_active(threshold, starting_point) == WatchActiveStatus.INACTIVE

    w2 = Watch(
        id=51,
        region=IdValue(52),
        city="yyy",
        specialty=[IdValue(53), IdValue(56), IdValue(59)],
        clinic=IdValue(54),
        doctor=IdValue(55),
        start_date=starting_point - timedelta(days=10),
        end_date=starting_point - timedelta(days=2),
        time_range=WatchTimeRange("12:15:36"),
        auto_book=True,
        exclusions=parse_exclusions("clinic:123,456"),
        type=WatchType.EXAMINATION,
    )
    assert w2.is_active(threshold, starting_point) == WatchActiveStatus.EXPIRED

    w3 = Watch(
        id=51,
        region=IdValue(52),
        city="yyy",
        specialty=[IdValue(53), IdValue(56), IdValue(59)],
        clinic=IdValue(54),
        doctor=IdValue(55),
        start_date=starting_point,
        end_date=starting_point + timedelta(days=10),
        time_range=WatchTimeRange("12:15:36"),
        auto_book=True,
        exclusions=parse_exclusions("doctor:123,456"),
        type=WatchType.EXAMINATION,
    )
    assert w3.is_active(threshold, starting_point) == WatchActiveStatus.ACTIVE


def test_watchtimerange_invalid_param():
    """Test that WatchTimeRange initialization fails with invalid parameters."""
    with raises(ValueError):
        WatchTimeRange(None)  # type: ignore


def test_watchtimerange_default():
    """Test the default WatchTimeRange creation."""
    d = WatchTimeRange.default()
    assert d == WatchTimeRange.midnight()
    assert d.is_endless
    assert d.start_time == time.min
    assert d.end_time is None


def test_watchtimerange_initialized_endless():
    """Test creating a WatchTimeRange with an endless time range."""
    d = WatchTimeRange("01:02:03")
    assert d.start_time == time.fromisoformat("01:02:03")
    assert d.is_endless
    assert d.end_time is None


def test_watchtimerange_initialized_constrained():
    """Test creating a WatchTimeRange with a constrained time range."""
    d = WatchTimeRange("01:02:03-11:11:11")
    assert d.start_time == time.fromisoformat("01:02:03")
    assert d.end_time == time.fromisoformat("11:11:11")
    assert not d.is_endless


def test_watchtimerange_initialized_wrong_order():
    """Test that WatchTimeRange initialization fails with end time before start time."""
    with raises(ValueError):
        WatchTimeRange("11:02:03-01:11:11")


def test_watchtimerange_check_within():
    """Test the is_within function for checking if a time is within a WatchTimeRange."""
    d = WatchTimeRange("05:02:03-11:11:11")
    t_inside = time.fromisoformat("07:00:00")
    assert is_within(d, t_inside)

    t_outside = time.fromisoformat("00:15:00")
    assert not is_within(d, t_outside)

    endless = WatchTimeRange("01:02:03")
    assert is_within(endless, t_inside)
    assert not is_within(endless, t_outside)


def test_watchtimerange_to_string():
    """Test the string representation of a WatchTimeRange object."""
    d = WatchTimeRange("05:02:03-11:11:11")
    assert str(d) == "05:02:03-11:11:11"

    endless = WatchTimeRange("01:02:03")
    assert str(endless) == "01:02:03-*"


def test_watch_edit_preserves_other_fields():
    """Test that editing a Watch field preserves other field values."""
    watch = Watch(
        id=91,
        region=IdValue(92),
        city="zzz",
        specialty=[IdValue(93)],
        clinic=IdValue(94),
        doctor=IdValue(95),
        start_date=date.fromisoformat("2027-02-21"),
        end_date=date.fromisoformat("2027-09-17"),
        time_range=WatchTimeRange("10:30:00-12:00:00"),
        auto_book=False,
        exclusions=None,
        type=WatchType.STANDARD,
    )
    # Simulate edit
    new_city = "edited"
    watch.city = new_city
    assert watch.city == "edited"
    # Other fields unchanged
    assert watch.region is not None and watch.region.id == 92
    assert watch.specialty is not None and watch.specialty[0].id == 93
    assert watch.clinic is not None and watch.clinic.id == 94
    assert watch.doctor is not None and watch.doctor.id == 95
