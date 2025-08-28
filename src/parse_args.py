import argparse
import datetime

from src.medicover.watch import GENERAL_PRACTITIONER_SPECIALTIES, WatchTimeRange


def specialty_list_type(value: str) -> list[int]:
    """
    Custom type for parsing a list of integers from a comma-separated string.
    """
    try:
        return [int(x) for x in value.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid list of integer IDs: {value}")


def command_line_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MediCony parameters")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")

    ########################################
    # find-appointment
    find_appointment = subparsers.add_parser("find-appointment", help="Find appointment")
    find_appointment.add_argument("-r", "--region", required=True, type=int, help="Region ID")
    find_appointment.add_argument("-m", "--city", required=False, default="any", type=str, help="City name")
    find_appointment.add_argument("-A", "--account", required=False, type=str, help="Medicover account alias")
    appt_specialty_group = find_appointment.add_mutually_exclusive_group(required=True)
    appt_specialty_group.add_argument(
        "-s",
        "--specialty",
        type=specialty_list_type,
        help="Specialty ID or multiple IDs separated by commas (e.g. 1,2,3)",
    )
    appt_specialty_group.add_argument(
        "-GP",
        "--general-practitioner",
        action="store_const",
        const=GENERAL_PRACTITIONER_SPECIALTIES,
        help="General practitioner specialties",
    )
    find_appointment.add_argument("-c", "--clinic", required=False, type=int, help="Clinic ID")
    find_appointment.add_argument("-d", "--doctor", required=False, type=int, help="Doctor ID")
    find_appointment.add_argument(
        "-f",
        "--date",
        type=datetime.date.fromisoformat,
        default=datetime.date.today(),
        help="Start date in YYYY-MM-DD format",
    )
    find_appointment.add_argument(
        "-E",
        "--examination",
        required=False,
        action="store_true",
        help="Sets the appointment type to examination",
    )
    find_appointment.add_argument(
        "-n", "--notification", action="store_true", required=False, help="Notification method"
    )
    find_appointment.add_argument("-t", "--title", required=False, help="Notification title")

    ########################################
    # book-appointment
    book_appointment = subparsers.add_parser("book-appointment", help="Book appointment")
    book_appointment.add_argument("-r", "--region", required=True, type=int, help="Region ID")
    book_appointment.add_argument("-m", "--city", required=False, default="any", type=str, help="City name")
    book_appointment.add_argument("-A", "--account", required=False, type=str, help="Medicover account alias")
    book_appointment.add_argument(
        "-s",
        "--specialty",
        required=True,
        type=int,
        help="Specialty ID",
    )
    book_appointment.add_argument("-c", "--clinic", required=True, type=int, help="Clinic ID")
    book_appointment.add_argument("-d", "--doctor", required=True, type=int, help="Doctor ID")
    book_appointment.add_argument(
        "-sd",
        "--date",
        type=datetime.datetime.fromisoformat,
        required=True,
        help="Appointment date in YYYY-MM-DD HH:MM:SS format, seconds (SS) are optional",
    )
    book_appointment.add_argument(
        "-E",
        "--examination",
        required=False,
        action="store_true",
        help="Sets the appointment type to examination",
    )
    book_appointment.add_argument(
        "-n", "--notification", action="store_true", required=False, help="Notification method"
    )
    book_appointment.add_argument("-t", "--title", required=False, help="Notification title")

    ########################################
    # list-appointments
    subparsers.add_parser("list-appointments", help="List appointments")

    ########################################
    # cancel-appointment
    cancel_appointment = subparsers.add_parser("cancel-appointment", help="Cancel appointment")
    cancel_appointment.add_argument("-i", "--id", required=True, type=int, help="Appointment ID")

    ########################################
    # list-accounts
    subparsers.add_parser("list-accounts", help="List configured Medicover account aliases")

    ########################################
    # add-watch
    add_watch = subparsers.add_parser("add-watch", help="Add watch")
    add_watch.add_argument("-r", "--region", required=True, type=int, help="Region ID")
    add_watch.add_argument("-m", "--city", required=False, default="any", type=str, help="City name")
    add_watch.add_argument("-A", "--account", required=False, type=str, help="Medicover account alias")
    specialty_group = add_watch.add_mutually_exclusive_group(required=True)
    specialty_group.add_argument(
        "-s",
        "--specialty",
        type=specialty_list_type,
        help="Specialty ID or multiple IDs separated by commas (e.g. 1,2,3)",
    )
    specialty_group.add_argument(
        "-GP",
        "--general-practitioner",
        action="store_const",
        const=GENERAL_PRACTITIONER_SPECIALTIES,
        help="General practitioner specialties",
    )
    add_watch.add_argument("-c", "--clinic", required=False, type=int, help="Clinic ID")
    add_watch.add_argument("-d", "--doctor", required=False, type=int, help="Doctor ID")
    add_watch.add_argument(
        "-sd",
        "--start-date",
        type=datetime.date.fromisoformat,
        default=datetime.date.today(),
        help="Start date in YYYY-MM-DD format",
    )
    add_watch.add_argument(
        "-ed",
        "--end-date",
        required=False,
        type=datetime.date.fromisoformat,
        default=datetime.date.max,
        help="End date in YYYY-MM-DD format",
    )
    add_watch.add_argument(
        "-tr",
        "--time-range",
        required=False,
        type=WatchTimeRange,
        default=WatchTimeRange.midnight(),
        help="Time range in HH:MM:SS[-HH:MM:SS] format, skip the second part for endless range, seconds (SS) are optional, default is 00:00:00",
    )
    add_watch.add_argument(
        "-B",
        "--auto-book",
        required=False,
        action="store_true",
        help="Autobooking when appointment is found",
    )
    add_watch.add_argument(
        "-E",
        "--examination",
        required=False,
        action="store_true",
        help="Sets the watch type to examination",
    )
    add_watch.add_argument(
        "-X",
        "--exclude",
        required=False,
        default=None,
        type=str,
        help='List of excluded IDs of clinics or doctors, e.g. "doctor:123,345;clinic:777,888"',
    )

    ########################################
    # remove-watch
    remove_watch = subparsers.add_parser("remove-watch", help="Remove watch")
    remove_watch.add_argument("-i", "--id", required=True, type=int, help="Watch Id")

    ########################################
    # start
    subparsers.add_parser("start", help="start watch")

    ########################################
    # list-watches
    list_watches = subparsers.add_parser("list-watches", help="List watches")
    list_watches.add_argument(
        "-n", "--notification", action="store_true", required=False, help="Send notifications via Telegram"
    )
    list_watches.add_argument("-A", "--account", required=False, type=str, help="Filter watches by account alias")

    list_filters = subparsers.add_parser("list-filters", help="List filters")

    list_filters_subparsers = list_filters.add_subparsers(
        dest="filter_type", required=True, help="Type of filter to list"
    )

    list_filters_subparsers.add_parser("regions", help="List available regions")
    list_filters_subparsers.add_parser("specialties", help="List available specialties")
    doctors = list_filters_subparsers.add_parser("doctors", help="List available doctors")
    doctors.add_argument("-r", "--region", required=True, type=int, help="Region ID")
    doctors.add_argument("-s", "--specialty", required=True, type=int, help="Specialty ID")

    clinics = list_filters_subparsers.add_parser("clinics", help="List available clinics")
    clinics.add_argument("-r", "--region", required=True, type=int, help="Region ID")
    clinics.add_argument("-s", "--specialty", required=True, type=int, help="Specialty ID")

    examinations = list_filters_subparsers.add_parser("examinations", help="List available examinations")
    examinations.add_argument("-r", "--region", required=True, type=int, help="Region ID")
    examinations.add_argument("-s", "--specialty", required=True, type=int, help="Specialty ID")

    ########################################
    # edit-watch
    edit_watch = subparsers.add_parser("edit-watch", help="Edit an existing watch")
    edit_watch.add_argument("-i", "--id", required=True, type=int, help="Watch ID to edit")
    edit_watch.add_argument("-m", "--city", required=False, default=None, type=str, help="City name")
    edit_watch.add_argument(
        "-A", "--account", required=False, type=str, help="Medicover account alias (ignored if watch already has one)"
    )
    edit_watch.add_argument("-c", "--clinic", required=False, default=None, type=int, help="Clinic ID")
    edit_watch.add_argument(
        "-B",
        "--auto-book",
        required=False,
        default=None,
        type=bool,
        help="Autobooking when appointment is found",
    )
    edit_watch.add_argument(
        "-sd",
        "--start-date",
        type=datetime.date.fromisoformat,
        required=False,
        default=None,
        help="Start date in YYYY-MM-DD format",
    )
    edit_watch.add_argument(
        "-ed",
        "--end-date",
        type=datetime.date.fromisoformat,
        required=False,
        default=None,
        help="End date in YYYY-MM-DD format, if not provided, maximum date (9999-12-31) is used",
    )
    edit_watch.add_argument(
        "-tr",
        "--time-range",
        required=False,
        default=None,
        type=WatchTimeRange,
        help="Time range in HH:MM:SS[-HH:MM:SS] format, skip the second part for endless range, seconds (SS) are optional, default is 00:00:00",
    )
    edit_watch.add_argument(
        "-X",
        "--exclude",
        required=False,
        default=None,
        type=str,
        help='List of excluded IDs of clinics or doctors, e.g. "doctor:123,345;clinic:777,888"',
    )

    ########################################
    # Medicine commands
    ########################################
    # add-medicine
    add_medicine = subparsers.add_parser("add-medicine", help="Add medicine search")
    add_medicine.add_argument("-n", "--name", required=True, type=str, help="Medicine name")
    add_medicine.add_argument("-d", "--dosage", required=False, type=str, help="Medicine dosage (e.g., 500mg, 10ml)")
    add_medicine.add_argument("--amount", required=False, type=str, help="Package amount/unit (e.g., 50 tabl., 200ml)")
    add_medicine.add_argument("-l", "--location", required=True, type=str, help="Location (address or city)")
    add_medicine.add_argument(
        "-r", "--radius", required=False, type=float, default=5.0, help="Search radius in km (default: 5.0)"
    )
    add_medicine.add_argument("-p", "--max-price", required=False, type=float, help="Maximum price in zł")
    add_medicine.add_argument(
        "-a",
        "--min-availability",
        required=False,
        choices=["low", "high", "none"],
        default="low",
        help="Minimum availability level (default: low)",
    )
    add_medicine.add_argument("-t", "--title", required=False, type=str, help="Custom title for notifications")

    ########################################
    # remove-medicine
    remove_medicine = subparsers.add_parser("remove-medicine", help="Remove medicine search")
    remove_medicine.add_argument("-i", "--id", required=True, type=int, help="Medicine ID")

    ########################################
    # list-medicines
    list_medicines = subparsers.add_parser("list-medicines", help="List medicine searches")
    list_medicines.add_argument(
        "-n", "--notification", action="store_true", required=False, help="Send notifications via Telegram"
    )

    ########################################
    # edit-medicine
    edit_medicine = subparsers.add_parser("edit-medicine", help="Edit an existing medicine search")
    edit_medicine.add_argument("-i", "--id", required=True, type=int, help="Medicine ID to edit")
    edit_medicine.add_argument("-n", "--name", required=False, type=str, help="Medicine name")
    edit_medicine.add_argument("-d", "--dosage", required=False, type=str, help="Medicine dosage")
    edit_medicine.add_argument("--amount", required=False, type=str, help="Package amount/unit (e.g., 50 tabl., 200ml)")
    edit_medicine.add_argument("-l", "--location", required=False, type=str, help="Location (address or city)")
    edit_medicine.add_argument("-r", "--radius", required=False, type=float, help="Search radius in km")
    edit_medicine.add_argument("-p", "--max-price", required=False, type=float, help="Maximum price in zł")
    edit_medicine.add_argument(
        "-a",
        "--min-availability",
        required=False,
        choices=["low", "high", "none"],
        help="Minimum availability level",
    )
    edit_medicine.add_argument("-t", "--title", required=False, type=str, help="Custom title for notifications")

    ########################################
    # search-medicine
    search_medicine = subparsers.add_parser("search-medicine", help="Search for a specific medicine")
    search_medicine.add_argument("-i", "--id", required=True, type=int, help="Medicine ID")
    search_medicine.add_argument(
        "-n", "--notification", action="store_true", required=False, help="Send results via Telegram"
    )

    return parser
