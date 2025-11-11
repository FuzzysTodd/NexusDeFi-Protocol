# safe_core.py
import time
import json
import os

STATE = "simulator/state.json"

def load_state():
    """Load the state from disk or return a default state on error."""
    try:
        if not os.path.exists(STATE):
            return {"vault": {"ETH": 0, "USDC": 0}, "spokes": {}, "pending": [], "keys": ["K1", "K2", "K3"]}
        with open(STATE) as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading state: {e}")
        return {"vault": {"ETH": 0, "USDC": 0}, "spokes": {}, "pending": [], "keys": ["K1", "K2", "K3"]}

def save_state(s):
    """Save the state to disk safely."""
    try:
        with open(STATE, "w") as f:
            json.dump(s, f, indent=2)
    except IOError as e:
        print(f"Error saving state: {e}")
        raise

def propose_tx(s, tx, timelock_hours):
    """Propose a transaction with checks for required fields."""
    # Validate required transaction fields
    required_fields = ["type", "asset", "amount"]
    for field in required_fields:
        if field not in tx:
            raise ValueError(f"Missing required transaction field: {field}")
    tx["requiredSigs"] = 2
    tx["signatures"] = []
    tx["not_before"] = time.time() + timelock_hours * 3600
    s["pending"].append(tx)

def sign_tx(s, tx_id, key_id):
    """Sign a transaction after validating indices and keys."""
    try:
        tx = s["pending"][tx_id]
    except (IndexError, TypeError):
        raise ValueError("Transaction ID is invalid")
    if key_id not in s["keys"]:
        raise ValueError("Invalid key ID")
    if key_id in tx["signatures"]:
        return  # Already signed with this key
    tx["signatures"].append(key_id)

def execute_tx(s, tx_id):
    """Execute a transaction with all appropriate checks."""
    try:
        tx = s["pending"][tx_id]
    except (IndexError, TypeError):
        raise ValueError("Transaction ID is invalid")
    if len(tx["signatures"]) < tx["requiredSigs"]:
        raise ValueError("Insufficient signatures")
    if time.time() < tx["not_before"]:
        raise ValueError("Timelock is still active")
    tx_type = tx.get("type")
    asset = tx.get("asset")
    amount = tx.get("amount")

    # Check all relevant fields for presence
    if tx_type not in ["fund_spoke", "pay_tax"]:
        raise ValueError(f"Unsupported transaction type: {tx_type}")
    if asset is None or amount is None:
        raise ValueError("Missing asset or amount in transaction")
    if type(amount) not in (int, float) or amount <= 0:
        raise ValueError("Amount must be a positive number")

    if s["vault"].get(asset, 0) < amount:
        raise ValueError("Insufficient funds in vault")

    if tx_type == "fund_spoke":
        spoke = tx.get("spoke")
        if not spoke:
            raise ValueError("Missing 'spoke' for fund_spoke transaction type")
        s["spokes"].setdefault(spoke, {"ETH": 0, "USDC": 0})
        s["vault"][asset] -= amount
        s["spokes"][spoke][asset] += amount
    elif tx_type == "pay_tax":
        s["vault"][asset] -= amount
    # Remove the transaction from pending
    s["pending"].pop(tx_id)
