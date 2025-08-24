from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple

from ..models import Expense
from ..utils.rounding import d_round
from ..persistence import json_store

PEOPLE = ["Hakan", "Aydin", "Gunel", "Emre"]


class ExpenseBook:
    """Manage expenses and compute debts between people."""

    def __init__(self, people: List[str] | None = None):
        self.people = list(people) if people else list(PEOPLE)
        self.expenses: List[Expense] = []
        self.debts: Dict[Tuple[str, str], Decimal] = {}

    # ---------- Persistence ----------
    def save(self, path: Path | None = None) -> None:
        json_store.save(self, path)

    def load(self, path: Path | None = None) -> None:
        json_store.load(self, path)

    # ---------- Business Rules ----------
    def add_expense(self, payer: str, amount: Decimal, beneficiaries: List[str]) -> None:
        if amount <= 0:
            raise ValueError("Tutar 0’dan büyük olmalı.")
        if not beneficiaries:
            raise ValueError("En az bir faydalanan seçmelisin.")
        for nm in [payer, *beneficiaries]:
            if nm not in self.people:
                raise ValueError(f"Bilinmeyen kişi: {nm}")

        exp = Expense(payer=payer, amount=str(d_round(amount)), beneficiaries=list(beneficiaries))
        self.expenses.append(exp)
        self._apply_expense(exp)

    def _apply_expense(self, exp: Expense) -> None:
        payer = exp.payer
        amount = Decimal(exp.amount)
        beneficiaries = list(exp.beneficiaries)
        n = len(beneficiaries)
        base_pay = amount / Decimal(n)
        pay = d_round(base_pay)

        total_rounded = pay * n
        remainder = d_round(amount - total_rounded)
        per_person = [pay for _ in range(n)]
        if remainder != 0:
            per_person[-1] = d_round(per_person[-1] + remainder)

        for b, share in zip(beneficiaries, per_person):
            if b == payer or share == 0:
                continue
            self._add_debt_edge(b, payer, share)

        self._simplify_mutual_edges()

    def _add_debt_edge(self, from_p: str, to_p: str, amt: Decimal) -> None:
        if from_p == to_p:
            return
        key = (from_p, to_p)
        self.debts[key] = d_round(self.debts.get(key, Decimal("0.00")) + d_round(amt))

    def _simplify_mutual_edges(self) -> None:
        keys = list(self.debts.keys())
        for (a, b) in keys:
            if (a, b) not in self.debts:
                continue
            if (b, a) in self.debts:
                x = self.debts[(a, b)]
                y = self.debts[(b, a)]
                if x == y:
                    del self.debts[(a, b)]
                    del self.debts[(b, a)]
                elif x > y:
                    self.debts[(a, b)] = d_round(x - y)
                    del self.debts[(b, a)]
                else:
                    self.debts[(b, a)] = d_round(y - x)
                    del self.debts[(a, b)]

    # ---------- Reports ----------
    def debt_matrix(self) -> List[List[Decimal]]:
        idx = {p: i for i, p in enumerate(self.people)}
        n = len(self.people)
        mat = [[Decimal("0.00") for _ in range(n)] for __ in range(n)]
        for (frm, to), amt in self.debts.items():
            i, j = idx[frm], idx[to]
            mat[i][j] = d_round(amt)
        return mat

    def net_balances(self) -> Dict[str, Decimal]:
        idx = {p: i for i, p in enumerate(self.people)}
        n = len(self.people)
        alacak = [Decimal("0.00")] * n
        borc = [Decimal("0.00")] * n
        for (frm, to), amt in self.debts.items():
            borc[idx[frm]] = d_round(borc[idx[frm]] + amt)
            alacak[idx[to]] = d_round(alacak[idx[to]] + amt)
        net = {}
        for p in self.people:
            i = idx[p]
            net[p] = d_round(alacak[i] - borc[i])
        return net

    def totals_paid_by_person(self) -> Dict[str, Decimal]:
        totals = {p: Decimal("0.00") for p in self.people}
        for e in self.expenses:
            totals[e.payer] = d_round(totals[e.payer] + Decimal(e.amount))
        return totals

    def greedy_settlement(self) -> List[Tuple[str, str, Decimal]]:
        net = self.net_balances()
        creditors = [(p, net[p]) for p in self.people if net[p] > 0]
        debtors = [(p, -net[p]) for p in self.people if net[p] < 0]

        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)

        i = j = 0
        res: List[Tuple[str, str, Decimal]] = []
        while i < len(debtors) and j < len(creditors):
            d_name, d_amt = debtors[i]
            c_name, c_amt = creditors[j]
            pay = d_round(min(d_amt, c_amt))
            if pay > 0:
                res.append((d_name, c_name, pay))
            d_amt = d_round(d_amt - pay)
            c_amt = d_round(c_amt - pay)
            debtors[i] = (d_name, d_amt)
            creditors[j] = (c_name, c_amt)
            if d_amt == 0:
                i += 1
            if c_amt == 0:
                j += 1
        return res

    def advanced_summary(self) -> Dict[str, str]:
        totals = self.totals_paid_by_person()
        total_amount = d_round(sum(totals.values(), Decimal("0.00")))
        count_tx = len(self.expenses)
        avg_per_person = (
            d_round(total_amount / Decimal(len(self.people))) if self.people else Decimal("0.00")
        )
        biggest = max(totals.items(), key=lambda x: x[1])[0] if totals else "-"
        smallest = min(totals.items(), key=lambda x: x[1])[0] if totals else "-"
        net = self.net_balances()
        most_credit = max(net.items(), key=lambda x: x[1])[0] if net else "-"
        most_debt = min(net.items(), key=lambda x: x[1])[0] if net else "-"
        return {
            "total_amount": str(total_amount),
            "count_tx": str(count_tx),
            "avg_per_person": str(avg_per_person),
            "biggest_spender": biggest,
            "smallest_spender": smallest,
            "most_creditor": most_credit,
            "most_debtor": most_debt,
        }
