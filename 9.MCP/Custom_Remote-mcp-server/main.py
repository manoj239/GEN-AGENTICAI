from fastmcp import FastMCP
from typing import Optional, List
import aiosqlite
import sqlite3
import os
import tempfile
import json
from datetime import datetime

# --- Setup --- test
DB_PATH = os.path.join(tempfile.gettempdir(), "expenses.db")

mcp = FastMCP("ExpenseTracker")


# --- DB Init (sync, once) ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                note TEXT
            )
        """)
        conn.commit()

init_db()


# --- Helper function to validate date ---
def validate_date(date_str: str) -> tuple[bool, str]:
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, "Date must be in YYYY-MM-DD format (e.g., 2024-01-15)"


# --- Tools ---

@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: Optional[str] = None,
    note: Optional[str] = None
) -> dict:
    """
    Add a new expense to the tracker.
    
    Args:
        date: Date of expense in YYYY-MM-DD format (e.g., 2024-01-15)
        amount: Amount spent (positive number)
        category: Category of expense (Food, Travel, Transport, Shopping, Bills, Healthcare, Education, Business, Other)
        subcategory: Optional subcategory for more detail
        note: Optional note or description
    """
    # Validate date
    is_valid, error_msg = validate_date(date)
    if not is_valid:
        return {"status": "error", "message": error_msg}
    
    # Validate amount
    if amount <= 0:
        return {"status": "error", "message": "Amount must be a positive number"}
    
    # Validate category
    valid_categories = ["Food", "Travel", "Transport", "Shopping", "Bills", 
                       "Healthcare", "Education", "Business", "Other"]
    if category not in valid_categories:
        return {
            "status": "error", 
            "message": f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        }
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
                (date, amount, category, subcategory, note)
            )
            await db.commit()
        
        return {
            "status": "success", 
            "id": cur.lastrowid,
            "message": f"Added expense: {category} - ${amount:.2f} on {date}"
        }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}


@mcp.tool()
async def list_expenses(
    start_date: str,
    end_date: str
) -> dict:
    """
    List all expenses within a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (e.g., 2024-01-01)
        end_date: End date in YYYY-MM-DD format (e.g., 2024-12-31)
    """
    # Validate dates
    is_valid, error_msg = validate_date(start_date)
    if not is_valid:
        return {"status": "error", "message": f"Invalid start_date: {error_msg}"}
    
    is_valid, error_msg = validate_date(end_date)
    if not is_valid:
        return {"status": "error", "message": f"Invalid end_date: {error_msg}"}
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
                """,
                (start_date, end_date)
            )
            cols = [c[0] for c in cur.description]
            expenses = [dict(zip(cols, row)) for row in await cur.fetchall()]
        
        return {
            "status": "success",
            "count": len(expenses),
            "expenses": expenses
        }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}


@mcp.tool()
async def summarize(
    start_date: str,
    end_date: str,
    category: Optional[str] = None
) -> dict:
    """
    Summarize expenses by category within a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        category: Optional specific category to filter by
    """
    # Validate dates
    is_valid, error_msg = validate_date(start_date)
    if not is_valid:
        return {"status": "error", "message": f"Invalid start_date: {error_msg}"}
    
    is_valid, error_msg = validate_date(end_date)
    if not is_valid:
        return {"status": "error", "message": f"Invalid end_date: {error_msg}"}
    
    query = """
        SELECT category, SUM(amount) AS total_amount, COUNT(*) AS count
        FROM expenses
        WHERE date BETWEEN ? AND ?
    """
    params = [start_date, end_date]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " GROUP BY category ORDER BY total_amount DESC"

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(query, params)
            cols = [c[0] for c in cur.description]
            summary = [dict(zip(cols, row)) for row in await cur.fetchall()]
        
        total = sum(item['total_amount'] for item in summary)
        
        return {
            "status": "success",
            "period": f"{start_date} to {end_date}",
            "total_amount": total,
            "summary": summary
        }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}


# --- Resource ---

@mcp.resource("expense:///categories", mime_type="application/json")
def categories():
    return json.dumps({
        "categories": [
            "Food",
            "Travel",
            "Transport",
            "Shopping",
            "Bills",
            "Healthcare",
            "Education",
            "Business",
            "Other"
        ]
    }, indent=2)


# --- Run ---
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)