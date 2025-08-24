from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Dict

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ..services.expense_book import ExpenseBook, PEOPLE
from ..utils.rounding import d_round
from ..persistence.json_store import DATA_PATH
from ..services import charts
from . import filters


class App(tk.Tk):
    """Tkinter based GUI application for the holiday budget planner."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Tatil Harcama Paylaşımı")
        self.geometry("920x720")
        self.resizable(False, False)

        self.book = ExpenseBook(PEOPLE)
        try:
            self.book.load(DATA_PATH)
        except Exception as e:  # pragma: no cover - UI warning
            messagebox.showwarning("Uyarı", f"Veri yüklenemedi: {e}")

        self._build_ui()
        self._refresh_summary()
        filters.refresh_filter_results(self)

    # ---------- UI building ----------
    def _build_ui(self) -> None:
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

        # --- Filter UI ---
        ffrm = ttk.LabelFrame(self, text="Hızlı Arama & Filtreleme")
        ffrm.pack(fill="x", padx=12, pady=8)

        ttk.Label(ffrm, text="Ödeyen:").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.filter_payer = tk.StringVar(value="(Hepsi)")
        payer_opts = ["(Hepsi)"] + PEOPLE
        ttk.Combobox(ffrm, textvariable=self.filter_payer, values=payer_opts, state="readonly", width=18).grid(
            row=0, column=1, padx=6, pady=6, sticky="w"
        )

        ttk.Label(ffrm, text="Faydalanan:").grid(row=0, column=2, padx=6, pady=6, sticky="e")
        self.filter_benef = tk.StringVar(value="(Hepsi)")
        benef_opts = ["(Hepsi)"] + PEOPLE
        ttk.Combobox(ffrm, textvariable=self.filter_benef, values=benef_opts, state="readonly", width=18).grid(
            row=0, column=3, padx=6, pady=6, sticky="w"
        )

        ttk.Label(ffrm, text="Min Tutar:").grid(row=0, column=4, padx=6, pady=6, sticky="e")
        self.filter_min = tk.StringVar()
        ttk.Entry(ffrm, textvariable=self.filter_min, width=12).grid(row=0, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(ffrm, text="Max Tutar:").grid(row=0, column=6, padx=6, pady=6, sticky="e")
        self.filter_max = tk.StringVar()
        ttk.Entry(ffrm, textvariable=self.filter_max, width=12).grid(row=0, column=7, padx=6, pady=6, sticky="w")

        ttk.Button(ffrm, text="Ara/Filtrele", command=lambda: filters.refresh_filter_results(self)).grid(
            row=0, column=8, padx=6, pady=6
        )
        ttk.Button(ffrm, text="Temizle", command=lambda: filters.clear_filters(self)).grid(
            row=0, column=9, padx=6, pady=6
        )

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

        sfrm = ttk.LabelFrame(self, text="Özet")
        sfrm.pack(fill="both", expand=False, padx=12, pady=6)
        self.summary_txt = tk.Text(sfrm, height=10, wrap="word")
        self.summary_txt.pack(fill="both", expand=True, padx=6, pady=6)

    # ---------- Event handlers ----------
    def _on_add(self) -> None:
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
        except Exception as e:  # pragma: no cover - user feedback
            messagebox.showerror("Hata", f"Beklenmeyen hata: {e}")
            return
        self.amount_var.set("")
        self._refresh_summary()
        filters.refresh_filter_results(self)

    def _on_save(self) -> None:
        try:
            self.book.save(DATA_PATH)
            messagebox.showinfo("Bilgi", f"Veriler kaydedildi: {DATA_PATH}")
        except Exception as e:  # pragma: no cover - user feedback
            messagebox.showerror("Hata", f"Kaydedilemedi: {e}")

    def _refresh_summary(self) -> None:
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
            lines.append(f"  - {p}: {net[p]} TL")
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

    def _show_table(self) -> None:
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

    def _show_settlement(self) -> None:
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

    def _show_charts(self) -> None:
        if not self.book.expenses:
            messagebox.showinfo("Grafikler", "Önce en az bir harcama ekleyin.")
            return
        charts.show_charts(self.book)

    def _export_report(self) -> None:
        if not self.book.expenses:
            messagebox.showinfo("Rapor", "Dışa aktarılacak veri yok.")
            return
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
        save_dir = filedialog.askdirectory(title="Raporu Kaydet (klasör seçin)")
        if not save_dir:
            return
        save_dir = Path(save_dir)
        report_path = save_dir / "harcama_raporu.txt"
        report_path.write_text("\n".join(txt_lines), encoding="utf-8")
        csv_path = save_dir / "harcamalar.csv"
        try:
            with csv_path.open("w", encoding="utf-8", newline="") as f:
                f.write("payer,amount,beneficiaries\n")
                for e in self.book.expenses:
                    b = ";".join(e.beneficiaries)
                    f.write(f"{e.payer},{e.amount},{b}\n")
        except Exception as e:  # pragma: no cover - user feedback
            messagebox.showwarning("CSV Uyarı", f"CSV yazarken sorun oluştu: {e}")
        messagebox.showinfo("Rapor", f"Kaydedildi:\n- {report_path}\n- {csv_path}")
