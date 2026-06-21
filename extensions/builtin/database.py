"""
Database Extension
Connect to SQLite, MySQL, or PostgreSQL databases.
Run queries, explore schemas, and analyze data.
"""

import os
import json
import sqlite3
from extensions.base import BaseExtension


class DatabaseExtension(BaseExtension):
    """Connect and query databases."""

    name = "database"
    display_name = "Database"
    description = "Connect to SQLite, MySQL, or PostgreSQL. Run queries and explore schemas."
    version = "1.0.0"
    author = "GALACTOS"
    icon = "database"

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self._refresh_config()

    def _refresh_config(self):
        self.db_type = self.get_config("db_type", "sqlite")
        self.db_path = self.get_config("db_path", "")
        self.host = self.get_config("host", "localhost")
        self.port = int(self.get_config("port", 3306))
        self.database = self.get_config("database", "")
        self.username = self.get_config("username", "")
        self.password = self.get_config("password", "")

    def get_routes(self):
        from flask import request, jsonify

        def connect():
            self._refresh_config()
            if self.db_type == "sqlite":
                if not self.db_path:
                    return jsonify({"error": "No SQLite database path configured"}), 400
                if not os.path.exists(self.db_path):
                    return jsonify({"error": f"Database file not found: {self.db_path}"}), 400
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    conn.close()
                    return jsonify({"success": True, "tables": tables, "type": "sqlite"})
                except Exception as e:
                    return jsonify({"error": str(e)}), 500
            else:
                try:
                    import pymysql
                    conn = pymysql.connect(
                        host=self.host, port=self.port,
                        user=self.username, password=self.password,
                        database=self.database
                    )
                    cursor = conn.cursor()
                    cursor.execute("SHOW TABLES")
                    tables = [row[0] for row in cursor.fetchall()]
                    conn.close()
                    return jsonify({"success": True, "tables": tables, "type": self.db_type})
                except ImportError:
                    return jsonify({"error": "pymysql not installed. Run: pip install pymysql"}), 500
                except Exception as e:
                    return jsonify({"error": str(e)}), 500

        def query():
            data = request.get_json()
            sql = data.get("query", "").strip()
            if not sql:
                return jsonify({"error": "No query provided"}), 400

            self._refresh_config()
            try:
                if self.db_type == "sqlite":
                    conn = sqlite3.connect(self.db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                else:
                    import pymysql
                    conn = pymysql.connect(
                        host=self.host, port=self.port,
                        user=self.username, password=self.password,
                        database=self.database, cursorclass=pymysql.cursors.DictCursor
                    )
                    cursor = conn.cursor()

                cursor.execute(sql)
                if sql.upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
                    rows = cursor.fetchall()
                    result = [dict(row) for row in rows]
                    conn.close()
                    return jsonify({"success": True, "rows": result, "count": len(result)})
                else:
                    conn.commit()
                    affected = cursor.rowcount
                    conn.close()
                    return jsonify({"success": True, "affected_rows": affected})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        def schema():
            data = request.get_json()
            table = data.get("table", "")
            if not table:
                return jsonify({"error": "No table specified"}), 400

            self._refresh_config()
            try:
                if self.db_type == "sqlite":
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute(f"PRAGMA table_info('{table}')")
                    columns = [{"name": row[1], "type": row[2], "notnull": bool(row[3]), "pk": bool(row[5])} for row in cursor.fetchall()]
                    cursor.execute(f"SELECT COUNT(*) FROM '{table}'")
                    count = cursor.fetchone()[0]
                    conn.close()
                else:
                    import pymysql
                    conn = pymysql.connect(
                        host=self.host, port=self.port,
                        user=self.username, password=self.password,
                        database=self.database
                    )
                    cursor = conn.cursor()
                    cursor.execute(f"DESCRIBE `{table}`")
                    columns = [{"name": row[0], "type": row[1], "notnull": row[2] == "NO", "pk": row[3] == "PRI"} for row in cursor.fetchall()]
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                    count = cursor.fetchone()[0]
                    conn.close()

                return jsonify({"success": True, "columns": columns, "row_count": count})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        return {
            "/api/extensions/database/connect": {
                "method": "POST",
                "handler": connect,
                "login_required": True,
            },
            "/api/extensions/database/query": {
                "method": "POST",
                "handler": query,
                "login_required": True,
            },
            "/api/extensions/database/schema": {
                "method": "POST",
                "handler": schema,
                "login_required": True,
            }
        }

    def get_chat_tools(self):
        return [
            {
                "name": "db_query",
                "description": "Run a SQL query on the connected database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query to execute"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "db_schema",
                "description": "Get the schema/structure of a database table",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"}
                    },
                    "required": ["table"]
                }
            }
        ]

    def execute_tool(self, tool_name, parameters):
        if tool_name == "db_query":
            return self._run_query(parameters.get("query", ""))
        elif tool_name == "db_schema":
            return self._get_schema(parameters.get("table", ""))
        return {"error": f"Unknown tool: {tool_name}"}

    def _run_query(self, sql):
        self._refresh_config()
        try:
            if self.db_type == "sqlite":
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
            else:
                import pymysql
                conn = pymysql.connect(
                    host=self.host, port=self.port,
                    user=self.username, password=self.password,
                    database=self.database, cursorclass=pymysql.cursors.DictCursor
                )
                cursor = conn.cursor()

            cursor.execute(sql)
            if sql.upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
                conn.close()
                return {"rows": result, "count": len(result)}
            else:
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return {"affected_rows": affected}
        except Exception as e:
            return {"error": str(e)}

    def _get_schema(self, table):
        self._refresh_config()
        try:
            if self.db_type == "sqlite":
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info('{table}')")
                columns = [{"name": row[1], "type": row[2], "pk": bool(row[5])} for row in cursor.fetchall()]
                cursor.execute(f"SELECT COUNT(*) FROM '{table}'")
                count = cursor.fetchone()[0]
                conn.close()
            else:
                import pymysql
                conn = pymysql.connect(
                    host=self.host, port=self.port,
                    user=self.username, password=self.password,
                    database=self.database
                )
                cursor = conn.cursor()
                cursor.execute(f"DESCRIBE `{table}`")
                columns = [{"name": row[0], "type": row[1], "pk": row[3] == "PRI"} for row in cursor.fetchall()]
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                conn.close()
            return {"columns": columns, "row_count": count}
        except Exception as e:
            return {"error": str(e)}

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "db_type",
                    "type": "select",
                    "label": "Database Type",
                    "options": [
                        {"value": "sqlite", "label": "SQLite"},
                        {"value": "mysql", "label": "MySQL"},
                        {"value": "postgresql", "label": "PostgreSQL"}
                    ],
                    "value": self.get_config("db_type", "sqlite")
                },
                {
                    "name": "db_path",
                    "type": "text",
                    "label": "SQLite Database Path",
                    "placeholder": "C:/path/to/database.db",
                    "value": self.get_config("db_path", "")
                },
                {
                    "name": "host",
                    "type": "text",
                    "label": "Host (MySQL/PostgreSQL)",
                    "placeholder": "localhost",
                    "value": self.get_config("host", "localhost")
                },
                {
                    "name": "port",
                    "type": "number",
                    "label": "Port",
                    "placeholder": "3306",
                    "value": self.get_config("port", 3306)
                },
                {
                    "name": "database",
                    "type": "text",
                    "label": "Database Name",
                    "placeholder": "my_database",
                    "value": self.get_config("database", "")
                },
                {
                    "name": "username",
                    "type": "text",
                    "label": "Username",
                    "placeholder": "root",
                    "value": self.get_config("username", "")
                },
                {
                    "name": "password",
                    "type": "password",
                    "label": "Password",
                    "placeholder": "password",
                    "value": self.get_config("password", "")
                }
            ]
        }
