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
def add_expense(date:str,amount:float,category: str,subcategory:str ="",note:str = "") -> dict:
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
def summarize(start_date: str, end_date: str,category: Optional[str] = None) -> list:
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

"""
I developed a custom MCP Server using the FastMCP framework for an Expense Management use case. The
objective was to allow AI agents to manage and analyze employee expenses such as travel, food, 
accommodation, and other business-related expenses.For persistence, I used a SQLite database to store  expense details such as date, amount, category, subcategory, and notes. I exposed three MCP Tools using the @mcp.tool() decorator:

add_expense(): Used to add a new expense record into the database.
list_expenses(): Used to retrieve expenses within a specific date range.
summarize(): Used to generate category-wise expense summaries for a given date range.

I also implemented an MCP Resource using @mcp.resource("expense://categories"). This resource exposes
all available expense categories from a JSON file (categories.json) in a read-only format. Agents
can access this resource to understand valid expense categories without modifying them.

Additionally, I created an MCP Prompt using @mcp.prompt(). This defines the behavior of the assistant,
such as when to use tools, how to process expense-related requests, and how to handle general
questions. For example, if the user asks a general knowledge question unrelated to expenses,
the assistant answers directly using the LLM instead of invoking any tools.

Finally, I start the MCP server using mcp.run(). While developing locally, I connected the server
to clients such as Claude Desktop using the MCP configuration file. Communication happens using
the standard MCP protocol based on JSON-RPC. For local execution, MCP typically uses stdio transport, 
allowing Claude or other MCP-compatible clients to securely discover and invoke tools, resources,
and prompts exposed by the server."""