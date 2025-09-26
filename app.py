import streamlit as st
import hashlib
import json
import time
import pandas as pd
from typing import List, Dict, Any


# -------------------------------
# Blockchain + EduCoin Classes
# -------------------------------

class Blockchain:
    def __init__(self):
        self.chain: List[Dict[str, Any]] = []
        self.pending_transactions: List[Dict[str, Any]] = []
        self.balances: Dict[str, int] = {}  # Track EduCoin balances
        self.reward_history: List[Dict[str, Any]] = []  # Teacher -> Student
        self.transfer_history: List[Dict[str, Any]] = []  # Student -> Student
        self.new_block(proof=100, previous_hash="1")  # Genesis block

    def new_block(self, proof: int, previous_hash: str = None) -> Dict[str, Any]:
        block_transactions = [tx.copy() for tx in self.pending_transactions]
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time.time(),
            "transactions": block_transactions,
            "proof": proof,
            "previous_hash": previous_hash or self.hash(self.chain[-1]),
        }
        self.pending_transactions = []
        block["hash"] = self.hash(block)
        self.chain.append(block)
        return block

    def new_transaction(self, sender: str, recipient: str, amount: int, teacher: str = None):
        # Prevent insufficient balance
        if sender != "Teacher":
            if self.balances.get(sender, 0) < amount:
                return False

        tx = {"sender": sender, "recipient": recipient, "amount": amount}
        if teacher:
            tx["teacher"] = teacher

        self.pending_transactions.append(tx)

        # Update balances
        if sender != "Teacher":
            self.balances[sender] -= amount
        self.balances[recipient] = self.balances.get(recipient, 0) + amount

        # Store history
        if sender == "Teacher":
            self.reward_history.append({"teacher": teacher, "student": recipient, "amount": amount})
        else:
            self.transfer_history.append({"from": sender, "to": recipient, "amount": amount})

        return self.last_block["index"] + 1

    @staticmethod
    def hash(block: Dict[str, Any]) -> str:
        block_copy = block.copy()
        block_copy.pop("hash", None)
        block_string = json.dumps(block_copy, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self) -> Dict[str, Any]:
        return self.chain[-1]

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            curr = self.chain[i]
            if curr["previous_hash"] != prev["hash"]:
                return False
            if curr["hash"] != self.hash(curr):
                return False
        return True


# -------------------------------
# Streamlit UI
# -------------------------------

st.set_page_config(page_title="EduCoin - Classroom Cryptocurrency", layout="wide")
st.title("💰 EduCoin: Classroom Cryptocurrency System")

# Initialize blockchain
if "blockchain" not in st.session_state:
    st.session_state.blockchain = Blockchain()

bc: Blockchain = st.session_state.blockchain

# Status
col1, col2 = st.columns(2)
col1.metric("Chain Length", len(bc.chain))
col2.metric("Is Chain Valid?", "✅ Yes" if bc.is_chain_valid() else "❌ No")

# -------------------------------
# Teacher Rewards
# -------------------------------
st.header("👩‍🏫 Teacher: Reward Students")
with st.form("reward_form", clear_on_submit=True):
    teacher_name = st.text_input("Teacher Name")
    student = st.text_input("Student Name")
    coins = st.number_input("Coins to Award", min_value=1, step=1)
    reward_submit = st.form_submit_button("Give EduCoin")
    if reward_submit and teacher_name and student:
        bc.new_transaction("Teacher", student, coins, teacher=teacher_name)
        block = bc.new_block(proof=123)
        st.success(f"✅ {coins} EduCoin awarded to {student} by {teacher_name} in Block {block['index']}!")

# -------------------------------
# Student Transfers
# -------------------------------
st.header("🔁 Students: Transfer EduCoin")
with st.form("transfer_form", clear_on_submit=True):
    teacher_name = st.text_input("Teacher Supervising Transfer")
    sender = st.text_input("Sender (Student)")
    recipient = st.text_input("Recipient (Student)")
    amount = st.number_input("Amount to Transfer", min_value=1, step=1)
    transfer_submit = st.form_submit_button("Send Coins")
    if transfer_submit and sender and recipient and teacher_name:
        if bc.new_transaction(sender, recipient, amount, teacher=teacher_name):
            block = bc.new_block(proof=123)
            st.success(f"✅ {sender} sent {amount} EduCoin to {recipient} (approved by {teacher_name}) in Block {block['index']}")
        else:
            st.error("❌ Transaction failed. Not enough balance.")

# -------------------------------
# Leaderboards
# -------------------------------
st.header("📊 EduCoin Leaderboards")

col1, col2 = st.columns(2)

# Teacher → Student Rewards
with col1:
    st.subheader("👩‍🏫 Teacher → Student Rewards")
    if bc.reward_history:
        df_rewards = pd.DataFrame(bc.reward_history)
        total_rewards = df_rewards["amount"].sum()
        st.dataframe(df_rewards)
        st.success(f"Total Coins Rewarded by Teachers: {total_rewards}")
    else:
        st.info("No teacher rewards yet.")

# Student → Student Transfers
with col2:
    st.subheader("🔁 Student → Student Transfers")
    if bc.transfer_history:
        df_transfers = pd.DataFrame(bc.transfer_history)
        total_transfers = df_transfers["amount"].sum()
        st.dataframe(df_transfers)
        st.success(f"Total Coins Transferred Between Students: {total_transfers}")
    else:
        st.info("No student transfers yet.")

# -------------------------------
# Balances
# -------------------------------
st.header("💳 Current EduCoin Balances")
if bc.balances:
    df_bal = pd.DataFrame(list(bc.balances.items()), columns=["Student", "Balance"])
    df_bal = df_bal.sort_values(by="Balance", ascending=False).reset_index(drop=True)
    st.dataframe(df_bal)
else:
    st.info("No balances yet. Teacher must reward students first.")

# -------------------------------
# Blockchain Explorer
# -------------------------------
st.header("⛓ Blockchain Explorer")
for block in reversed(bc.chain):
    with st.expander(f"Block {block['index']}"):
        st.write("Timestamp:", block["timestamp"])
        st.write("Previous Hash:", block["previous_hash"])
        st.write("Hash:", block["hash"])
        st.json(block["transactions"])
