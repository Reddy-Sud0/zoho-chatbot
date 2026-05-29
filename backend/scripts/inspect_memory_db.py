import sqlite3
import json

def main():
    conn = sqlite3.connect('zoho_chatbot.db')
    cursor = conn.cursor()

    print("--- MEMORY TABLE ---")
    cursor.execute("SELECT user_id, key, value, updated_at FROM memory ORDER BY updated_at DESC")
    for row in cursor.fetchall():
        print(f"User: {row[0]}, Key: {row[1]}, Value: {row[2]}, Updated: {row[3]}")

if __name__ == "__main__":
    main()