import matplotlib

matplotlib.use("TkAgg")  # ensure Tkinter backend
import matplotlib.pyplot as plt

from .expense_book import ExpenseBook


def show_charts(book: ExpenseBook) -> None:
    """Display basic charts for the given expense book."""
    totals = book.totals_paid_by_person()
    names = list(totals.keys())
    vals = [float(totals[n]) for n in names]
    plt.figure()
    plt.bar(names, vals)
    plt.title("Kişi Bazlı Toplam Ödemeler (TL)")
    plt.xlabel("Kişi")
    plt.ylabel("Toplam Ödeme (TL)")
    plt.tight_layout()

    net = book.net_balances()
    names2 = list(net.keys())
    vals2 = [float(net[n]) for n in names2]
    plt.figure()
    plt.bar(names2, vals2)
    plt.title("Net Bakiyeler (Alacak - Borç, TL)")
    plt.xlabel("Kişi")
    plt.ylabel("Net Bakiye (TL)")
    plt.axhline(0, linewidth=2)
    plt.tight_layout()

    if sum(vals) > 0:
        plt.figure()
        plt.pie(vals, labels=names, autopct="%1.1f%%", startangle=90)
        plt.title("Toplam Harcama Payı")
        plt.tight_layout()

    plt.show()
