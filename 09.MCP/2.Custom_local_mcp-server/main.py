from fastmcp import FastMCP
import os
import sqlite3
from typing import Optional

# Paths
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.json")

# MCP Server
mcp = FastMCP("ExpenseTracker")


def init_db() -> None:
    """Initialize the SQLite database."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
            """
        )


# -----------------------
# TOOLS
# -----------------------

@mcp.tool()
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
) -> dict:
    """
    Add a new expense entry to the database.
    Date format must be YYYY-MM-DD.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO expenses(date, amount, category, subcategory, note)
            VALUES (?,?,?,?,?)
            """,
            (date, amount, category, subcategory, note)
        )

        return {
            "status": "success",
            "expense_id": cur.lastrowid
        }


@mcp.tool()
def list_expenses(start_date: str, end_date: str) -> list:
    """
    List expense entries within an inclusive date range.
    Dates must be YYYY-MM-DD.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
            """,
            (start_date, end_date)
        )

        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@mcp.tool()
def summarize(
    start_date: str,
    end_date: str,
    category: Optional[str] = None
) -> list:
    """
    Summarize expenses by category within a date range.
    Optionally filter by a specific category.
    """
    with sqlite3.connect(DB_PATH) as conn:
        query = """
        SELECT category, SUM(amount) as total_amount
        FROM expenses
        WHERE date BETWEEN ? AND ?
        """

        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"

        cur = conn.execute(query, params)

        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# -----------------------
# RESOURCE
# -----------------------

@mcp.resource("expense://categories", mime_type="application/json")
def categories() -> str:
    """
    Returns available expense categories.
    Reads categories.json dynamically.
    """
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


# -----------------------
# PROMPT
# -----------------------

@mcp.prompt("expense-assistant")
def expense_assistant() -> dict:
    """
    Base system prompt for the expense assistant.
    """
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful and intelligent assistant.\n\n"

                    "You can manage expenses using available tools such as adding, listing, "
                    "and summarizing expenses.\n\n"

                    "Guidelines:\n"
                    "- Use tools ONLY when the query is related to expense management.\n"
                    "- For general or unrelated questions, answer directly using your knowledge.\n"
                    "- Do NOT refuse general questions.\n"
                    "- If a tool is not required, respond normally.\n"
                    "- When using tools, ensure correct arguments and formats.\n"
                    "- Dates must follow the YYYY-MM-DD format.\n\n"

                    "Your goal is to be helpful, flexible, and accurate."
                )
            }
        ]
    }


# -----------------------
# MAIN
# -----------------------

if __name__ == "__main__":
    init_db()
    mcp.run()