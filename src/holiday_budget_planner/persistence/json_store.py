from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ..models import Expense

if TYPE_CHECKING:  # pragma: no cover
    from ..services.expense_book import ExpenseBook

DATA_PATH = Path("expenses.json")


def save(book: "ExpenseBook", path: Path | None = None) -> None:
    """Persist expenses of the given book to JSON."""
    path = path or DATA_PATH
    data = {"people": book.people, "expenses": [e.to_dict() for e in book.expenses]}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load(book: "ExpenseBook", path: Path | None = None) -> None:
    """Load expenses into the given book from JSON."""
    path = path or DATA_PATH
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    book.people = data.get("people", book.people)
    book.expenses = [Expense.from_dict(e) for e in data.get("expenses", [])]
    book.debts.clear()
    for e in book.expenses:
        book._apply_expense(e)
