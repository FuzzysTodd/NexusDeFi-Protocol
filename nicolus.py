# safe_core.py
import time, json, os

STATE = "simulator/state.json"

def load_state():
    try:
        if not os.path.exists(STATE):
            return {"vault": {"ETH": 0, "USDC": 0}, "spokes": {}, "pending": [], "keys": ["K1", "K2", "K3"]}
        with open(STATE) as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        # Log error and return default state
        print(f"Error loading state: {e}")
        return {"vault": {"ETH": 0, "USDC": 0}, "spokes": {}, "pending": [], "keys": ["K1", "K2", "K3"]}

def save_state(s):
    try:
        with open(STATE, "w") as f:
            json.dump(s, f, indent=2)
    except IOError as e:
        print(f"Error saving state: {e}")
        raise

def propose_tx(s, tx, timelock_hours):
    # Validate required fields
    for required in ["type", "asset", "amount"]:
        if required not in tx:
            raise ValueError(f"Missing required transaction field: {required}")
    tx["requiredSigs"] = 2
    tx["signatures"] = []
    tx["not_before"] = time.time() + timelock_hours * 3600
    s["pending"].append(tx)

def sign_tx(s, tx_id, key_id):
    try:
        tx = s["pending"][tx_id]
    except IndexError:
        raise ValueError("Transaction ID does not exist")
    if key_id not in s["keys"]:
        raise ValueError("bad key")
    if key_id in tx["signatures"]:
        return
    tx["signatures"].append(key_id)

def execute_tx(s, tx_id):
    try:
        tx = s["pending"][tx_id]
    except IndexError:
        raise ValueError("Transaction ID does not exist")
    if len(tx["signatures"]) < tx["requiredSigs"]:
        raise ValueError("insufficient signatures")
    if time.time() < tx["not_before"]:
        raise ValueError("timelock active")
    # Transaction type validation
    if tx["type"] == "fund_spoke":
        spoke = tx.get("spoke")
        asset = tx.get("asset")
        amount = tx.get("amount")
        if spoke is None or asset is None or amount is None:
            raise ValueError("Missing data for 'fund_spoke'")
        if s["vault"].get(asset, 0) < amount:
            raise ValueError("insufficient vault funds")
        s["spokes"].setdefault(spoke, {"ETH":0, "USDC":0})
        s["vault"][asset] -= amount
        s["spokes"][spoke][asset] += amount
    elif tx["type"] == "pay_tax":
        asset = tx.get("asset")
        amount = tx.get("amount")
        if asset is None or amount is None:
            raise ValueError("Missing data for 'pay_tax'")
        if s["vault"].get(asset, 0) < amount:
            raise ValueError("insufficient vault funds")
        s["vault"][asset] -= amount
    else:
        raise ValueError(f"Unsupported transaction type: {tx['type']}")
    s["pending"].pop(tx_id)
