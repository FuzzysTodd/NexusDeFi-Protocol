# safe_core.py
import time, json, os

STATE = "simulator/state.json"

def load_state():
    if not os.path.exists(STATE):
        return {"vault": {"ETH": 0, "USDC": 0}, "spokes": {}, "pending": [], "keys": ["K1", "K2", "K3"]}
    return json.load(open(STATE))

def save_state(s): json.dump(s, open(STATE, "w"), indent=2)

def propose_tx(s, tx, timelock_hours):
    tx["requiredSigs"] = 2
    tx["signatures"] = []
    tx["not_before"] = time.time() + timelock_hours * 3600
    s["pending"].append(tx)

def sign_tx(s, tx_id, key_id):
    tx = s["pending"][tx_id]
    if key_id not in s["keys"]: raise ValueError("bad key")
    if key_id in tx["signatures"]: return
    tx["signatures"].append(key_id)

def execute_tx(s, tx_id):
    tx = s["pending"][tx_id]
    if len(tx["signatures"]) < tx["requiredSigs"]: raise ValueError("insufficient signatures")
    if time.time() < tx["not_before"]: raise ValueError("timelock active")
    # route by type
    if tx["type"] == "fund_spoke":
        s["spokes"].setdefault(tx["spoke"], {"ETH":0, "USDC":0})
        s["vault"][tx["asset"]] -= tx["amount"]
        s["spokes"][tx["spoke"]][tx["asset"]] += tx["amount"]
    elif tx["type"] == "pay_tax":
        s["vault"][tx["asset"]] -= tx["amount"]
    s["pending"].pop(tx_id)
