"""
MySQL Service - Database & User Management
Creates, drops databases and users for hosting accounts
"""
import subprocess
import pymysql
from typing import Dict, Any, List, Optional
from app.config import settings


class MySQLService:

    @staticmethod
    def get_connection(database: str = None):
        """Get MySQL root connection"""
        conn_args = {
            "host": settings.MYSQL_HOST,
            "port": settings.MYSQL_PORT,
            "user": settings.MYSQL_ROOT_USER,
            "password": settings.MYSQL_ROOT_PASSWORD,
            "charset": "utf8mb4",
            "autocommit": True,
        }
        if database:
            conn_args["database"] = database
        return pymysql.connect(**conn_args)

    @staticmethod
    def create_database(db_name: str) -> Dict[str, Any]:
        """Create a new MySQL database"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.close()
            return {"success": True, "message": f"Database '{db_name}' created successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def drop_database(db_name: str) -> Dict[str, Any]:
        """Drop a MySQL database"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            conn.close()
            return {"success": True, "message": f"Database '{db_name}' dropped successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_user(db_user: str, db_password: str, host: str = "localhost") -> Dict[str, Any]:
        """Create a MySQL user"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE USER IF NOT EXISTS '{db_user}'@'{host}' IDENTIFIED BY %s", (db_password,))
            conn.close()
            return {"success": True, "message": f"User '{db_user}' created successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def drop_user(db_user: str, host: str = "localhost") -> Dict[str, Any]:
        """Drop a MySQL user"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"DROP USER IF EXISTS '{db_user}'@'{host}'")
            conn.close()
            return {"success": True, "message": f"User '{db_user}' dropped successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def grant_privileges(db_name: str, db_user: str, privileges: str = "ALL PRIVILEGES", host: str = "localhost") -> Dict[str, Any]:
        """Grant privileges on a database to a user"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"GRANT {privileges} ON `{db_name}`.* TO '{db_user}'@'{host}'")
                cursor.execute("FLUSH PRIVILEGES")
            conn.close()
            return {"success": True, "message": f"Privileges granted on '{db_name}' to '{db_user}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def revoke_privileges(db_name: str, db_user: str, host: str = "localhost") -> Dict[str, Any]:
        """Revoke all privileges from a user on a database"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"REVOKE ALL PRIVILEGES ON `{db_name}`.* FROM '{db_user}'@'{host}'")
                cursor.execute("FLUSH PRIVILEGES")
            conn.close()
            return {"success": True, "message": "Privileges revoked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def change_user_password(db_user: str, new_password: str, host: str = "localhost") -> Dict[str, Any]:
        """Change MySQL user password"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"ALTER USER '{db_user}'@'{host}' IDENTIFIED BY %s", (new_password,))
                cursor.execute("FLUSH PRIVILEGES")
            conn.close()
            return {"success": True, "message": "Password changed successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def list_databases(prefix: str = None) -> List[str]:
        """List all databases (optionally filtered by prefix)"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                dbs = [row[0] for row in cursor.fetchall()]
            conn.close()
            exclude = {"information_schema", "performance_schema", "mysql", "sys"}
            dbs = [d for d in dbs if d not in exclude]
            if prefix:
                dbs = [d for d in dbs if d.startswith(prefix)]
            return dbs
        except Exception as e:
            return []

    @staticmethod
    def get_database_size(db_name: str) -> Dict[str, Any]:
        """Get database size in MB"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    GROUP BY table_schema
                """, (db_name,))
                result = cursor.fetchone()
            conn.close()
            return {"size_mb": result[0] if result else 0}
        except Exception as e:
            return {"size_mb": 0, "error": str(e)}

    @staticmethod
    def get_server_status() -> Dict[str, Any]:
        """Get MySQL server status"""
        try:
            conn = MySQLService.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime'")
                uptime = cursor.fetchone()
                cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected'")
                threads = cursor.fetchone()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
            conn.close()
            return {
                "version": version[0] if version else "Unknown",
                "uptime_seconds": uptime[1] if uptime else 0,
                "threads_connected": threads[1] if threads else 0,
                "status": "running",
            }
        except Exception as e:
            return {"status": "stopped", "error": str(e)}

    @staticmethod
    def create_db_with_user(db_name: str, db_user: str, db_password: str) -> Dict[str, Any]:
        """Create database + user + grant privileges in one call"""
        results = {}
        r1 = MySQLService.create_database(db_name)
        r2 = MySQLService.create_user(db_user, db_password)
        r3 = MySQLService.grant_privileges(db_name, db_user)
        if r1["success"] and r2["success"] and r3["success"]:
            return {"success": True, "message": f"Database '{db_name}' with user '{db_user}' created successfully"}
        else:
            errors = []
            for r in [r1, r2, r3]:
                if not r["success"]:
                    errors.append(r.get("error", "Unknown error"))
            return {"success": False, "error": "; ".join(errors)}
