import os

LEDGER_DEFAULT_LIMIT = int(os.getenv("LEDGER_DEFAULT_LIMIT", "20"))
LEDGER_MAX_LIMIT = int(os.getenv("LEDGER_MAX_LIMIT", "100"))
