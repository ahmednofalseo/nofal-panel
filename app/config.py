import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PANEL_NAME: str = os.getenv("PANEL_NAME", "Nofal Panel")
    PANEL_PORT: int = int(os.getenv("PANEL_PORT", 2083))
    PANEL_HOST: str = os.getenv("PANEL_HOST", "0.0.0.0")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "nofal-panel-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "NofaLPanel@2024")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@localhost")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./nofal_panel.db")

    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_ROOT_USER: str = os.getenv("MYSQL_ROOT_USER", "root")
    MYSQL_ROOT_PASSWORD: str = os.getenv("MYSQL_ROOT_PASSWORD", "")

    NGINX_SITES_AVAILABLE: str = os.getenv("NGINX_SITES_AVAILABLE", "/etc/nginx/sites-available")
    NGINX_SITES_ENABLED: str = os.getenv("NGINX_SITES_ENABLED", "/etc/nginx/sites-enabled")
    BIND_ZONES_DIR: str = os.getenv("BIND_ZONES_DIR", "/etc/bind/zones")
    VSFTPD_USER_DIR: str = os.getenv("VSFTPD_USER_DIR", "/etc/vsftpd/users")
    ACCOUNTS_HOME: str = os.getenv("ACCOUNTS_HOME", "/home")

    CERTBOT_EMAIL: str = os.getenv("CERTBOT_EMAIL", "admin@localhost")

    # cPanel tools: optional external phpMyAdmin URL (same host or /phpmyadmin)
    PHPMYADMIN_URL: str = os.getenv("PHPMYADMIN_URL", "")

    # Optional paths for metrics / raw log (panel host)
    NGINX_ACCESS_LOG: str = os.getenv("NGINX_ACCESS_LOG", "/var/log/nginx/access.log")
    NGINX_ERROR_LOG: str = os.getenv("NGINX_ERROR_LOG", "/var/log/nginx/error.log")

    PANEL_VERSION: str = "1.0.0"

settings = Settings()
