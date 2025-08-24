"""Entry point for the holiday budget planner application."""

from holiday_budget_planner.ui.app import App


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
