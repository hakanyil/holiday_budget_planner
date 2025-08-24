from decimal import Decimal
from typing import Any

from ..services.expense_book import ExpenseBook


def parse_decimal_or_none(value: str) -> Decimal | None:
    value = value.strip().replace(",", ".")
    if not value:
        return None
    try:
        return Decimal(value)
    except Exception:
        return None


def refresh_filter_results(app: Any) -> None:
    """Refresh tree view according to current filter widgets on ``app``."""
    tree = app.result_tree
    for item in tree.get_children():
        tree.delete(item)

    pay_filter = app.filter_payer.get()
    ben_filter = app.filter_benef.get()
    min_val = parse_decimal_or_none(app.filter_min.get())
    max_val = parse_decimal_or_none(app.filter_max.get())

    idx = 1
    for e in app.book.expenses:
        if pay_filter != "(Hepsi)" and e.payer != pay_filter:
            continue
        if ben_filter != "(Hepsi)" and ben_filter not in e.beneficiaries:
            continue
        amt = Decimal(e.amount)
        if (min_val is not None and amt < min_val) or (max_val is not None and amt > max_val):
            continue
        tree.insert("", "end", values=[idx, e.payer, str(e.amount), ", ".join(e.beneficiaries)])
        idx += 1


def clear_filters(app: Any) -> None:
    app.filter_payer.set("(Hepsi)")
    app.filter_benef.set("(Hepsi)")
    app.filter_min.set("")
    app.filter_max.set("")
    refresh_filter_results(app)
