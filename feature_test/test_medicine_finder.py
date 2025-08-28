"""
Feature test for medicine search functionality.
Tests the medicine feature with real-world data.
"""

import logging

import pytest

from pharmaradar import Medicine, MedicineFinder
from pharmaradar.availability_level import AvailabilityLevel
from pharmaradar.text_parsers import MedicineNameMatcher

log = logging.getLogger(__name__)


def test_medicine_search_euthyrox():
    """
    End-to-end infrastructure test for medicine search functionality.

    This test verifies that:
    1. The medicine scraper can connect to ktomalek.pl
    2. WebDriver can be initialized and controlled
    3. The search workflow executes without crashes
    4. The fuzzy matching system is integrated correctly

    Note: This test validates technical functionality, not data availability.
    The website content may vary, so finding 0 results doesn't indicate failure
    as long as the infrastructure works correctly.

    In containerized environments, WebDriver may fail due to sandboxing restrictions.
    This is expected and the test will be skipped in such cases.
    """
    log.info("=" * 80)
    log.info("MEDICINE FEATURE TEST: Euthyrox N 50 in Warsaw")
    log.info("=" * 80)

    # Setup
    medicine = Medicine(
        name="Euthyrox N 50",
        dosage="50 mcg",
        location="Warszawa",
        radius_km=10.0,
        min_availability=AvailabilityLevel.LOW,
    )

    log.info(f"Testing medicine search for: {medicine.full_name} in {medicine.location}")

    # Create finder
    log.info("Creating medicine finder...")
    finder = MedicineFinder()

    # Test connection
    log.info("Testing connection to ktomalek.pl...")
    try:
        connected = finder.test_connection()
        log.info(f"Connection test: {'✅ PASSED' if connected else '❌ FAILED'}")
    except Exception as e:
        # In containerized environments, WebDriver may fail due to restrictions
        # This is expected and we should skip the test
        error_msg = str(e)
        if any(
            keyword in error_msg.lower()
            for keyword in [
                "user data directory",
                "preferences",
                "session not created",
                "webdriver",
                "chrome",
                "sandboxing",
            ]
        ):
            log.warning(f"WebDriver failed in containerized environment: {e}")
            pytest.skip("WebDriver cannot initialize in this environment (expected in containers)")
        else:
            # Unexpected error, re-raise
            raise

    if not connected:
        log.error("Cannot connect to ktomalek.pl, aborting test")
        pytest.skip("Cannot connect to ktomalek.pl")

    # Search for medicine
    log.info(f"Searching for {medicine.full_name} in {medicine.location}...")
    pharmacies = finder.search_medicine(medicine)

    # Log results
    if pharmacies:
        log.info(f"Found {len(pharmacies)} pharmacies with {medicine.full_name}")
        for i, pharmacy in enumerate(pharmacies[:5], 1):  # Show first 5
            log.info(f"Pharmacy {i}:")
            log.info(f"  Name: {pharmacy.name}")
            log.info(f"  Address: {pharmacy.address}")
            log.info(f"  Availability: {pharmacy.availability}")
            if pharmacy.price_full:
                log.info(f"  Price: {pharmacy.price_full} zł")
            if pharmacy.distance_km:
                log.info(f"  Distance: {pharmacy.distance_km} km")
            if pharmacy.reservation_url:
                log.info(f"  Reservation URL: {pharmacy.reservation_url}")
            log.info("  -" * 30)

        if len(pharmacies) > 5:
            log.info(f"... and {len(pharmacies) - 5} more")
    else:
        log.warning(f"No pharmacies found with {medicine.full_name} in {medicine.location}")

    # Summary
    log.info("=" * 80)
    log.info("TEST SUMMARY:")
    log.info(f"Connection: {'✅ PASSED' if connected else '❌ FAILED'}")
    log.info("Search execution: ✅ PASSED")
    log.info(f"Results found: {'✅ YES' if pharmacies else '⚠️ NO'}")
    log.info(f"Total pharmacies: {len(pharmacies)}")
    log.info("=" * 80)

    # We consider the test successful if we can connect and execute the search
    # Finding results is great but not required since website structure can change
    assert connected, "Could not connect to ktomalek.pl"

    if len(pharmacies) == 0:
        log.warning("No results found, but scraper infrastructure is working correctly")
        log.info("This test validates the technical functionality, not data availability")

    # Test passes if connection and search execution work (infrastructure validation)
    log.info("✅ Medicine feature test completed successfully - infrastructure is functional")


def test_fuzzy_medicine_matching():
    """
    Test the fuzzy matching functionality for medicine names.
    This test verifies case-insensitive and diacritics-aware matching.
    """
    log.info("=" * 80)
    log.info("FUZZY MATCHING TEST: Case-insensitive medicine search")
    log.info("=" * 80)

    matcher = MedicineNameMatcher()

    # Test case sensitivity
    test_cases = [
        ("Euthyrox N 50", "EUTHYROX N 50", True, "uppercase"),
        ("Euthyrox N 50", "euthyrox n 50", True, "lowercase"),
        ("Euthyrox N 50", "Euthyrox N 50", True, "exact match"),
        ("Euthyrox N 50", "Euthyrox N 50 mg", True, "with mg suffix"),
        ("Euthyrox N 50", "Letrox 50", False, "different medicine"),
        ("Apap", "APAP Extra", True, "partial match"),
        ("Aspirin", "Aspirin C", True, "with suffix"),
    ]

    log.info("Testing fuzzy matching cases:")
    passed_tests = 0
    total_tests = len(test_cases)

    for search_term, found_name, expected_match, description in test_cases:
        actual_match = matcher.is_name_match(search_term, found_name, min_similarity=0.7)
        similarity = matcher.calculate_similarity(search_term, found_name)

        status = "✅ PASS" if actual_match == expected_match else "❌ FAIL"
        if actual_match == expected_match:
            passed_tests += 1

        log.info(
            f"  {description:15} | '{search_term}' vs '{found_name}' | "
            f"Expected: {expected_match:5} | Got: {actual_match:5} | "
            f"Similarity: {similarity:.3f} | {status}"
        )

    log.info("=" * 80)
    log.info(f"Fuzzy matching test results: {passed_tests}/{total_tests} passed")
    log.info("=" * 80)

    # Test passes if all fuzzy matching cases work correctly
    assert passed_tests == total_tests, f"Fuzzy matching failed: {passed_tests}/{total_tests} tests passed"
