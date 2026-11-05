"""Transaction et Bloc."""
from dataclasses import dataclass, field

from core.crypto import sha256_hex, merkle_root

COINBASE = "COINBASE"
BLOCK_REWARD = 50.0


@dataclass(frozen=True)
class Transaction:
    sender: str
    receiver: str
    amount: float
    nonce: int = 0  # distingue deux transactions identiques
    tx_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "tx_id", sha256_hex(
            f"{self.sender}|{self.receiver}|{self.amount}|{self.nonce}"))


def coinbase(miner: str, height: int, reward: float = BLOCK_REWARD) -> Transaction:
    """Transaction de recompense du mineur (unique par hauteur)."""
    return Transaction(COINBASE, miner, reward, nonce=height)


@dataclass
class Block:
    index: int                      # hauteur du bloc
    prev_hash: str
    transactions: tuple             # tuple de Transaction
    miner: str
    difficulty: int = 0             # nb de zeros hexa au debut du hash
    timestamp: float = 0.0          # temps simule
    nonce: int = 0
    merkle: str = field(default="", init=False)
    hash: str = field(default="", init=False)

    def __post_init__(self):
        self.transactions = tuple(self.transactions)
        self.merkle = merkle_root([t.tx_id for t in self.transactions])
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        header = (f"{self.index}|{self.prev_hash}|{self.merkle}|{self.miner}|"
                  f"{self.timestamp}|{self.difficulty}|{self.nonce}")
        return sha256_hex(header)

    def refresh(self) -> None:
        """Recalcule merkle et hash (apres modification)."""
        self.merkle = merkle_root([t.tx_id for t in self.transactions])
        self.hash = self.compute_hash()

    def meets_target(self) -> bool:
        return self.hash.startswith("0" * self.difficulty)

    def __repr__(self) -> str:
        return f"Block(#{self.index} {self.hash[:8]} <- {self.prev_hash[:8]} by {self.miner})"
