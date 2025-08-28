"""
Tests for the Watch domain model and related functionality.

This module contains tests for the Watch class, WatchTimeRange, and related
helper functions to ensure correct initialization, validation and operations.
"""

from datetime import date, time, timedelta

from pytest import raises

from src.medicover.watch import Watch, WatchActiveStatus, WatchTimeRange, is_within


def test_watch_invalid_initialization():
    """Test that Watch initialization fails with invalid arguments."""
    # Act & Assert
    with raises(ValueError):
        Watch.from_tuple((1, 2))  # Too few arguments


def test_watch_initialization_with_defaults():
    """Test initializing a Watch with minimal arguments and default values."""
    # Arrange
    init = (1, 2, "aaa", [3], 4, 5, date.min)

    # Act
    watch = Watch.from_tuple(init)

    # Assert
    assert watch.id == 1
    assert watch.region is not None and watch.region.id == 2
    assert watch.city == "aaa"
    assert watch.specialty[0].id == 3
    assert watch.clinic is not None and watch.clinic.id == 4
    assert watch.doctor is not None and watch.doctor.id == 5
    assert watch.start_date == date.min


def test_watch_initialization_with_defaults_multiple_specialties():
    """Test initializing a Watch with multiple specialties."""
    # Arrange
    init = (1, 2, "aaa", [3, 6, 9], 4, 5, date.min)

    # Act
    watch = Watch.from_tuple(init)

    # Assert
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
    init = (
        11,
        22,
        "bbb",
        [33],
        44,
        55,
        date.fromisoformat("2137-09-01"),
        date.fromisoformat("2137-09-17"),
        WatchTimeRange("12:12:12-13:13:13"),
        False,
    )
    watch = Watch.from_tuple(init)

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
    init = (
        11,
        22,
        "bbb",
        [33, 66, 99],
        44,
        55,
        date.fromisoformat("2137-09-01"),
        date.fromisoformat("2137-09-17"),
        WatchTimeRange("12:12:12-13:13:13"),
        False,
    )
    watch = Watch.from_tuple(init)

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
    init = (11, 22, "xxxx", [33], 44, 55, "2137-09-01", "2137-09-17", "12:12:12-13:13:13", True)
    watch = Watch.from_tuple(init)

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
    init = (
        91,
        92,
        "zzz",
        [93],
        94,
        95,
        date.fromisoformat("2027-02-21"),
        date.fromisoformat("2027-09-17"),
        WatchTimeRange("10:30"),
        False,
        "doctor:111,222;clinic:333,444",
        "Standard",
    )
    watch = Watch.from_tuple(init)

    expected = "ID 91\nRegion: 92\nCity: zzz\nType: Standard\nSpecialty: 93\nClinic: 94\nDoctor: 95\nDate range: 2027-02-21–2027-09-17\nTime range: 10:30:00-*\nAutobook: False\nExclusions: doctor:111,222;clinic:333,444\nAccount: default"

    assert str(watch) == expected


def test_watch_to_string_multiple_specialties():
    """Test the string representation of a Watch object with multiple specialties."""
    init = (
        91,
        92,
        "zzz",
        [93, 96, 99],
        94,
        95,
        date.fromisoformat("2027-02-21"),
        date.fromisoformat("2027-09-17"),
        WatchTimeRange("10:30"),
        False,
        None,
        "Standard",
    )
    watch = Watch.from_tuple(init)

    expected = "ID 91\nRegion: 92\nCity: zzz\nType: Standard\nSpecialty: 93, 96, 99\nClinic: 94\nDoctor: 95\nDate range: 2027-02-21–2027-09-17\nTime range: 10:30:00-*\nAutobook: False\nExclusions: None\nAccount: default"

    assert str(watch) == expected


def test_watch_to_string_with_descriptive_values():
    """Test the string representation of a Watch object with descriptive values."""
    init = (
        51,
        52,
        "yyy",
        [53],
        54,
        55,
        "2137-09-01",
        "2137-09-17",
        "12:12:12-13:13:13",
        True,
        None,
        "DiagnosticProcedure",
    )
    watch = Watch.from_tuple(init)
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
    init = (
        51,
        52,
        "yyy",
        [53, 56, 59],
        54,
        55,
        "2137-09-01",
        "2137-09-17",
        "12:12:12-13:13:13",
        True,
        "doctor:111,222,333",
        "DiagnosticProcedure",
    )
    watch = Watch.from_tuple(init)
    # Set descriptive values for the watch
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
    init = (51, 52, "yyy", [53], 54, 55, "2137-09-01", "2137-09-17", "12:15:36", True, None, "DiagnosticProcedure")
    watch = Watch.from_tuple(init)
    expected = "ID 51; r: 52; ci: yyy; t: DiagnosticProcedure; s: 53; cl: 54; d: 55; dr: 2137-09-01–2137-09-17; tr: 12:15:36-*; ab: True; excl: None; acc: default"

    assert watch.short_str() == expected


def test_watch_to_short_str_multiple_specialties():
    """Test the short string representation of a Watch object with multiple specialties."""
    init = (
        51,
        52,
        "yyy",
        [53, 56, 59],
        54,
        55,
        "2137-09-01",
        "2137-09-17",
        "12:15:36",
        True,
        "doctor:777,888,999",
        "DiagnosticProcedure",
    )
    watch = Watch.from_tuple(init)
    expected = "ID 51; r: 52; ci: yyy; t: DiagnosticProcedure; s: 53, 56, 59; cl: 54; d: 55; dr: 2137-09-01–2137-09-17; tr: 12:15:36-*; ab: True; excl: doctor:777,888,999; acc: default"

    assert watch.short_str() == expected


def test_watch_active_status():
    """Test the active status determination of a Watch object."""
    starting_point = date.today()
    threshold = 1  # days
    w1 = Watch.from_tuple(
        (
            51,
            52,
            "yyy",
            [53, 56, 59],
            54,
            55,
            starting_point + timedelta(days=2),
            "2137-09-17",
            "12:15:36",
            True,
            None,
            "DiagnosticProcedure",
        )
    )
    assert w1.is_active(threshold, starting_point) == WatchActiveStatus.INACTIVE

    w2 = Watch.from_tuple(
        (
            51,
            52,
            "yyy",
            [53, 56, 59],
            54,
            55,
            starting_point - timedelta(days=10),
            starting_point - timedelta(days=2),
            "12:15:36",
            True,
            "clinic:123,456",
            "DiagnosticProcedure",
        )
    )
    assert w2.is_active(threshold, starting_point) == WatchActiveStatus.EXPIRED

    w3 = Watch.from_tuple(
        (
            51,
            52,
            "yyy",
            [53, 56, 59],
            54,
            55,
            starting_point,
            starting_point + timedelta(days=10),
            "12:15:36",
            True,
            "doctor:123,456",
            "DiagnosticProcedure",
        )
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
    init = (
        91,
        92,
        "zzz",
        [93],
        94,
        95,
        date.fromisoformat("2027-02-21"),
        date.fromisoformat("2027-09-17"),
        "10:30:00-12:00:00",
        False,
        None,
        "Standard",
    )
    watch = Watch.from_tuple(init)
    # Simulate edit
    new_city = "edited"
    watch.city = new_city
    assert watch.city == "edited"
    # Other fields unchanged
    assert watch.region is not None and watch.region.id == 92
    assert watch.specialty is not None and watch.specialty[0].id == 93
    assert watch.clinic is not None and watch.clinic.id == 94
    assert watch.doctor is not None and watch.doctor.id == 95
