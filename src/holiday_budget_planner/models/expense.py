from dataclasses import dataclass, asdict
from typing import List


@dataclass(frozen=True)
class Expense:
    """Represents a single expense item."""

    payer: str
    amount: str  # stored as Decimal string to keep JSON serialisable
    beneficiaries: List[str]

    def to_dict(self) -> dict:
        """Serialize the expense to a dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Expense":
        """Create an :class:`Expense` from a dictionary."""
        return Expense(
            payer=data["payer"],
            amount=data["amount"],
            beneficiaries=list(data["beneficiaries"]),
        )
