"""
Centralized queue status constants used across orders and products apps.
"""

ACTIVE_QUEUE_STATUSES = [
    "OEQ", "MGQ", "CHQ", "PTQ", "FQQ", "CRDQ", "SRQ", "PDQ", "BOQ", "PQ", "CSQ",
]

VALID_TRANSITIONS = {
    "OEQ": ["MGQ", "CHQ"],
    "CHQ": ["MGQ"],
    "MGQ": ["PTQ", "FQQ", "CRDQ", "SRQ", "PDQ"],
    "FQQ": ["PTQ", "MGQ"],
    "CRDQ": ["PTQ", "MGQ"],
    "SRQ": ["MGQ"],
    "PDQ": ["MGQ"],
    "PTQ": ["IVQ", "BOQ", "PQ"],
    "BOQ": ["PTQ"],
    "PQ": ["PTQ", "MGQ"],
    "CSQ": ["MGQ", "OEQ"],
    "IVQ": [],
}

HOLD_CREDIT_CODES = {"D", "C", "Z", "H"}
