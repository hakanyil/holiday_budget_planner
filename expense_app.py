# expense_app.py
# Özellikler:
# - 4 sabit kişi: Hakan, Aydın, Günel, Emre
# - Harcama ekleme (payer, amount, beneficiaries)
# - Borç matrisi, net bakiyeler
# - Greedy netleştirme önerisi
# - JSON kalıcılık (expenses.json)
# - YENİ: Hızlı Arama & Filtreleme (payer, beneficiary, min/max), sonuç listesi
# - YENİ: Harcama Grafikleri (matplotlib pencereleri)
# - YENİ: Gelişmiş Raporlama (TXT raporu + CSV dışa aktarma)

from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import List, Dict, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Grafikler
import matplotlib
matplotlib.use("TkAgg")  # Tkinter ile uyumlu backend
import matplotlib.pyplot as plt

# === Finansal yuvarlama ===
getcontext().prec = 28
TWOP = Decimal("0.01")

PEOPLE = ["Hakan", "Aydin", "Gunel", "Emre"]
DATA_PATH = Path("expenses.json")


def d_round(x: Decimal) -> Decimal:
    return x.quantize(TWOP, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Expense:
    payer: str
    amount: str  # Decimal string
    beneficiaries: List[str]

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Expense":
        return Expense(payer=d["payer"], amount=d["amount"], beneficiaries=list(d["beneficiaries"]))


class ExpenseBook:
    def __init__(self, people: List[str]):
        self.people = list(people)
        self.expenses: List[Expense] = []
        self.debts: Dict[Tuple[str, str], Decimal] = {}

    # ---------- Persistence ----------
    def save(self, path: Path = DATA_PATH):
        data = {
            "people": self.people,
            "expenses": [e.to_dict() for e in self.expenses],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: Path = DATA_PATH):
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.people = data.get("people", self.people)
        self.expenses = [Expense.from_dict(e) for e in data.get("expenses", [])]
        self.debts.clear()
        for e in self.expenses:
            self._apply_expense(e)

    # ---------- Rules ----------
    def add_expense(self, payer: str, amount: Decimal, beneficiaries: List[str]):
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

    def _apply_expense(self, exp: Expense):
        payer = exp.payer
        amount = Decimal(exp.amount)
        beneficiaries = list(exp.beneficiaries)
        n = len(beneficiaries)
        base_pay = (amount / Decimal(n))
        pay = d_round(base_pay)

        total_rounded = pay * n
        remainder = d_round(amount - total_rounded)
        per_person = [pay for _ in range(n)]
        if remainder != 0:
            per_person[-1] = d_round(per_person[-1] + remainder)

        for b, share in zip(beneficiaries, per_person):
            if b == payer:
                continue
            if share == 0:
                continue
            self._add_debt_edge(b, payer, share)

        self._simplify_mutual_edges()

    def _add_debt_edge(self, from_p: str, to_p: str, amt: Decimal):
        if from_p == to_p:
            return
        key = (from_p, to_p)
        self.debts[key] = d_round(self.debts.get(key, Decimal("0.00")) + d_round(amt))

    def _simplify_mutual_edges(self):
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
        """Kimin cebinden toplam ne kadar çıktığı (payer bazlı)"""
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

    # ---------- Advanced summary for report ----------
    def advanced_summary(self) -> Dict[str, str]:
        totals = self.totals_paid_by_person()
        total_amount = d_round(sum(totals.values(), Decimal("0.00")))
        count_tx = len(self.expenses)
        avg_per_person = d_round(total_amount / Decimal(len(self.people))) if self.people else Decimal("0.00")

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


# ===================== Tkinter UI =====================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tatil Harcama Paylaşımı")
        self.geometry("920x720")
        self.resizable(False, False)

        self.book = ExpenseBook(PEOPLE)
        try:
            self.book.load(DATA_PATH)
        except Exception as e:
            messagebox.showwarning("Uyarı", f"Veri yüklenemedi: {e}")

        self._build_ui()
        self._refresh_summary()
        self._refresh_filter_results()

    def _build_ui(self):
        # === Harcama Ekle ===
        frm = ttk.LabelFrame(self, text="Harcama Ekle")
        frm.pack(fill="x", padx=12, pady=8)

        ttk.Label(frm, text="Ödeyen:").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.payer_var = tk.StringVar(value=PEOPLE[0])
        self.payer_cb = ttk.Combobox(frm, textvariable=self.payer_var, values=PEOPLE, state="readonly", width=18)
        self.payer_cb.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(frm, text="Tutar (TL):").grid(row=0, column=2, padx=6, pady=6, sticky="e")
        self.amount_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.amount_var, width=18).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        bfrm = ttk.LabelFrame(frm, text="Faydalananlar")
        bfrm.grid(row=1, column=0, columnspan=4, padx=6, pady=6, sticky="w")
        self.benefit_vars: Dict[str, tk.BooleanVar] = {}
        for i, p in enumerate(PEOPLE):
            var = tk.BooleanVar(value=True)
            self.benefit_vars[p] = var
            ttk.Checkbutton(bfrm, text=p, variable=var).grid(row=0, column=i, padx=6, pady=6, sticky="w")

        btnfrm = ttk.Frame(frm)
        btnfrm.grid(row=2, column=0, columnspan=4, padx=6, pady=6, sticky="w")
        ttk.Button(btnfrm, text="Ekle", command=self._on_add).grid(row=0, column=0, padx=4)
        ttk.Button(btnfrm, text="Özet Tablo", command=self._show_table).grid(row=0, column=1, padx=4)
        ttk.Button(btnfrm, text="Netleştir (Öneri)", command=self._show_settlement).grid(row=0, column=2, padx=4)
        ttk.Button(btnfrm, text="Kaydet", command=self._on_save).grid(row=0, column=3, padx=4)
        ttk.Button(btnfrm, text="Yenile", command=self._refresh_summary).grid(row=0, column=4, padx=4)
        ttk.Button(btnfrm, text="Grafikler", command=self._show_charts).grid(row=0, column=5, padx=4)
        ttk.Button(btnfrm, text="Rapor Dışa Aktar", command=self._export_report).grid(row=0, column=6, padx=4)

        # === Arama & Filtreleme ===
        ffrm = ttk.LabelFrame(self, text="Hızlı Arama & Filtreleme")
        ffrm.pack(fill="x", padx=12, pady=8)

        ttk.Label(ffrm, text="Ödeyen:").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.filter_payer = tk.StringVar(value="(Hepsi)")
        payer_opts = ["(Hepsi)"] + PEOPLE
        ttk.Combobox(ffrm, textvariable=self.filter_payer, values=payer_opts, state="readonly", width=18)\
            .grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(ffrm, text="Faydalanan:").grid(row=0, column=2, padx=6, pady=6, sticky="e")
        self.filter_benef = tk.StringVar(value="(Hepsi)")
        benef_opts = ["(Hepsi)"] + PEOPLE
        ttk.Combobox(ffrm, textvariable=self.filter_benef, values=benef_opts, state="readonly", width=18)\
            .grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(ffrm, text="Min Tutar:").grid(row=0, column=4, padx=6, pady=6, sticky="e")
        self.filter_min = tk.StringVar()
        ttk.Entry(ffrm, textvariable=self.filter_min, width=12).grid(row=0, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(ffrm, text="Max Tutar:").grid(row=0, column=6, padx=6, pady=6, sticky="e")
        self.filter_max = tk.StringVar()
        ttk.Entry(ffrm, textvariable=self.filter_max, width=12).grid(row=0, column=7, padx=6, pady=6, sticky="w")

        ttk.Button(ffrm, text="Ara/Filtrele", command=self._refresh_filter_results).grid(row=0, column=8, padx=6, pady=6)
        ttk.Button(ffrm, text="Temizle", command=self._clear_filters).grid(row=0, column=9, padx=6, pady=6)

        # Sonuç listesi
        rfrm = ttk.LabelFrame(self, text="Sonuçlar")
        rfrm.pack(fill="both", expand=True, padx=12, pady=8)

        cols = ["#", "Ödeyen", "Tutar", "Faydalananlar"]
        self.result_tree = ttk.Treeview(rfrm, columns=cols, show="headings", height=10)
        for c in cols:
            self.result_tree.heading(c, text=c)
            anchor = "e" if c in ["#", "Tutar"] else "w"
            width = 60 if c == "#" else (100 if c in ["Ödeyen", "Tutar"] else 540)
            self.result_tree.column(c, anchor=anchor, width=width)
        self.result_tree.pack(fill="both", expand=True, padx=6, pady=6)

        # === Özet ===
        sfrm = ttk.LabelFrame(self, text="Özet")
        sfrm.pack(fill="both", expand=False, padx=12, pady=6)
        self.summary_txt = tk.Text(sfrm, height=10, wrap="word")
        self.summary_txt.pack(fill="both", expand=True, padx=6, pady=6)

    # ---------- Events ----------
    def _on_add(self):
        payer = self.payer_var.get().strip()
        amt_str = self.amount_var.get().strip().replace(",", ".")
        try:
            amount = d_round(Decimal(amt_str))
        except Exception:
            messagebox.showerror("Hata", "Geçerli bir tutar giriniz (örn. 200 veya 200.50).")
            return
        beneficiaries = [p for p, v in self.benefit_vars.items() if v.get()]
        try:
            self.book.add_expense(payer, amount, beneficiaries)
        except ValueError as ve:
            messagebox.showerror("Hata", str(ve))
            return
        except Exception as e:
            messagebox.showerror("Hata", f"Beklenmeyen hata: {e}")
            return
        self.amount_var.set("")
        self._refresh_summary()
        self._refresh_filter_results()

    def _on_save(self):
        try:
            self.book.save(DATA_PATH)
            messagebox.showinfo("Bilgi", f"Veriler kaydedildi: {DATA_PATH}")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydedilemedi: {e}")

    def _refresh_summary(self):
        mat = self.book.debt_matrix()
        net = self.book.net_balances()

        lines = []
        lines.append("Borç Matrisi (satır: borçlu → sütun: alacaklı):\n")
        header = ["     "] + [f"{p:>10}" for p in PEOPLE]
        lines.append("".join(header))
        for i, r_name in enumerate(PEOPLE):
            row = [f"{r_name:>5}"]
            for j, _ in enumerate(PEOPLE):
                val = mat[i][j]
                row.append(f"{str(val):>10}")
            lines.append("".join(row))
        lines.append("")
        lines.append("Net Bakiyeler (alacak - borç):")
        for p in PEOPLE:
            lines.append(f"  - {p}: {self.book.net_balances()[p]} TL")
        lines.append("")
        adv = self.book.advanced_summary()
        lines.append("Gelişmiş Raporlama Özeti:")
        lines.append(f"  - Toplam Harcama: {adv['total_amount']} TL")
        lines.append(f"  - İşlem Sayısı: {adv['count_tx']}")
        lines.append(f"  - Kişi Başı Ortalama: {adv['avg_per_person']} TL")
        lines.append(f"  - En Çok Harcayan: {adv['biggest_spender']}")
        lines.append(f"  - En Az Harcayan: {adv['smallest_spender']}")
        lines.append(f"  - En Yüksek Alacaklı (Net +): {adv['most_creditor']}")
        lines.append(f"  - En Yüksek Borçlu (Net -): {adv['most_debtor']}")

        self.summary_txt.delete("1.0", "end")
        self.summary_txt.insert("1.0", "\n".join(lines))

    def _show_table(self):
        mat = self.book.debt_matrix()
        win = tk.Toplevel(self)
        win.title("Borç Tablosu")
        cols = ["Borçlu \\ Alacaklı"] + PEOPLE
        tree = ttk.Treeview(win, columns=cols, show="headings", height=10)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="e", width=120)
        tree.column(cols[0], anchor="w", width=160)
        for i, r_name in enumerate(PEOPLE):
            row = [r_name] + [str(mat[i][j]) for j in range(len(PEOPLE))]
            tree.insert("", "end", values=row)
        tree.pack(fill="both", expand=True, padx=8, pady=8)

    def _show_settlement(self):
        proposals = self.book.greedy_settlement()
        if not proposals:
            messagebox.showinfo("Netleştirme", "Öneri yok (herkes dengede görünüyor).")
            return
        win = tk.Toplevel(self)
        win.title("Netleştirme Önerisi")
        txt = tk.Text(win, height=14, wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", "Kim kime ne kadar ödesin?\n\n")
        for frm, to, amt in proposals:
            txt.insert("end", f"  - {frm} → {to}: {amt} TL\n")

    # ---------- Filters ----------
    def _clear_filters(self):
        self.filter_payer.set("(Hepsi)")
        self.filter_benef.set("(Hepsi)")
        self.filter_min.set("")
        self.filter_max.set("")
        self._refresh_filter_results()

    def _parse_decimal_or_none(self, s: str):
        s = s.strip().replace(",", ".")
        if not s:
            return None
        try:
            return Decimal(s)
        except Exception:
            return None

    def _refresh_filter_results(self):
        for i in self.result_tree.get_children():
            self.result_tree.delete(i)

        pay_filter = self.filter_payer.get()
        ben_filter = self.filter_benef.get()
        min_val = self._parse_decimal_or_none(self.filter_min.get())
        max_val = self._parse_decimal_or_none(self.filter_max.get())

        idx = 1
        for e in self.book.expenses:
            # payer filter
            if pay_filter != "(Hepsi)" and e.payer != pay_filter:
                continue
            # beneficiary filter
            if ben_filter != "(Hepsi)" and ben_filter not in e.beneficiaries:
                continue
            amt = Decimal(e.amount)
            if (min_val is not None and amt < min_val) or (max_val is not None and amt > max_val):
                continue
            self.result_tree.insert("", "end", values=[idx, e.payer, str(e.amount), ", ".join(e.beneficiaries)])
            idx += 1

    # ---------- Charts ----------
    def _show_charts(self):
        if not self.book.expenses:
            messagebox.showinfo("Grafikler", "Önce en az bir harcama ekleyin.")
            return

        # 1) Kişi bazlı toplam ödemeler (bar)
        totals = self.book.totals_paid_by_person()
        names = list(totals.keys())
        vals = [float(totals[n]) for n in names]
        plt.figure()
        plt.bar(names, vals)
        plt.title("Kişi Bazlı Toplam Ödemeler (TL)")
        plt.xlabel("Kişi")
        plt.ylabel("Toplam Ödeme (TL)")
        plt.tight_layout()

        # 2) Net bakiyeler (bar)
        net = self.book.net_balances()
        names2 = list(net.keys())
        vals2 = [float(net[n]) for n in names2]
        plt.figure()
        plt.bar(names2, vals2)
        plt.title("Net Bakiyeler (Alacak - Borç, TL)")
        plt.xlabel("Kişi")
        plt.ylabel("Net Bakiye (TL)")
        plt.axhline(0, linewidth=2)
        plt.tight_layout()

        # 3) Toplam harcama payı (pie)
        if sum(vals) > 0:
            plt.figure()
            plt.pie(vals, labels=names, autopct="%1.1f%%", startangle=90)
            plt.title("Toplam Harcama Payı")
            plt.tight_layout()

        plt.show()

    # ---------- Report Export ----------
    def _export_report(self):
        if not self.book.expenses:
            messagebox.showinfo("Rapor", "Dışa aktarılacak veri yok.")
            return

        # TXT raporu
        adv = self.book.advanced_summary()
        net = self.book.net_balances()
        totals = self.book.totals_paid_by_person()

        txt_lines = []
        txt_lines.append("=== Tatil Harcama Raporu ===")
        txt_lines.append(f"Toplam Harcama: {adv['total_amount']} TL")
        txt_lines.append(f"İşlem Sayısı: {adv['count_tx']}")
        txt_lines.append(f"Kişi Başı Ortalama: {adv['avg_per_person']} TL\n")
        txt_lines.append("Kişi Bazlı Toplam Ödemeler:")
        for p in PEOPLE:
            txt_lines.append(f"  - {p}: {totals[p]} TL")
        txt_lines.append("\nNet Bakiyeler (alacak - borç):")
        for p in PEOPLE:
            txt_lines.append(f"  - {p}: {net[p]} TL")
        txt_lines.append("\nÖne Çıkanlar:")
        txt_lines.append(f"  - En Çok Harcayan: {adv['biggest_spender']}")
        txt_lines.append(f"  - En Az Harcayan: {adv['smallest_spender']}")
        txt_lines.append(f"  - En Yüksek Alacaklı (Net +): {adv['most_creditor']}")
        txt_lines.append(f"  - En Yüksek Borçlu (Net -): {adv['most_debtor']}")

        # Kaydetme konumu
        save_dir = filedialog.askdirectory(title="Raporu Kaydet (klasör seçin)")
        if not save_dir:
            return
        save_dir = Path(save_dir)

        # TXT
        report_path = save_dir / "harcama_raporu.txt"
        report_path.write_text("\n".join(txt_lines), encoding="utf-8")

        # CSV (ham işlemler)
        csv_path = save_dir / "harcamalar.csv"
        try:
            # basit CSV yazımı
            with csv_path.open("w", encoding="utf-8", newline="") as f:
                f.write("payer,amount,beneficiaries\n")
                for e in self.book.expenses:
                    b = ";".join(e.beneficiaries)
                    f.write(f"{e.payer},{e.amount},{b}\n")
        except Exception as e:
            messagebox.showwarning("CSV Uyarı", f"CSV yazarken sorun oluştu: {e}")

        messagebox.showinfo("Rapor", f"Kaydedildi:\n- {report_path}\n- {csv_path}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
