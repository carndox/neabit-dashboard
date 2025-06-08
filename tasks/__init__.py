# tasks/__init__.py

# Tell Python that this is a package, and export ALL_TASKS for discovery.

from nea_reports import (
    process_pdc,
    process_interruption,
    process_supply,
    process_ngcp,
    process_distribution
)

ALL_TASKS = [
    # (display_name, module_path, function_name)
    ("PDC/PGC/PSR Report",   "tasks.pdc_stub",        "process_pdc"),
    ("Interruption Report",  "tasks.interruption_stub","process_interruption"),
    ("Supply OCR",           "tasks.supply_stub",     "process_supply"),
    ("NGCP OCR",             "tasks.ngcp_stub",       "process_ngcp"),
    ("Distribution Report",  "tasks.distribution_stub","process_distribution"),
]
