"""
Nginx Service - Virtual Host Management
Creates, updates, deletes Nginx virtual hosts for hosting accounts
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from app.config import settings


VHOST_TEMPLATE = """server {{
    listen 80;
    listen [::]:80;
    server_name {domain} www.{domain};
    root {document_root};
    index index.php index.html index.htm;

    access_log /var/log/nginx/{username}.access.log;
    error_log /var/log/nginx/{username}.error.log;

    client_max_body_size {upload_size}M;

    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}

    location ~ \\.php$ {{
        fastcgi_pass unix:/var/run/php/php{php_version}-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PHP_VALUE "upload_max_filesize = {upload_size}M\\npost_max_size = {upload_size}M\\nmemory_limit = {memory_limit}M\\nmax_execution_time = {max_exec}";
    }}

    location ~ /\\.ht {{
        deny all;
    }}

    # Deny access to hidden files
    location ~ /\\. {{
        deny all;
    }}
}}
"""

VHOST_SSL_TEMPLATE = """server {{
    listen 80;
    listen [::]:80;
    server_name {domain} www.{domain};
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain} www.{domain};
    root {document_root};
    index index.php index.html index.htm;

    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    access_log /var/log/nginx/{username}.access.log;
    error_log /var/log/nginx/{username}.error.log;

    client_max_body_size {upload_size}M;

    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}

    location ~ \\.php$ {{
        fastcgi_pass unix:/var/run/php/php{php_version}-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }}

    location ~ /\\.ht {{
        deny all;
    }}
}}
"""


class NginxService:

    @staticmethod
    def _run(cmd: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return {"success": result.returncode == 0, "output": result.stdout.strip(), "error": result.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_vhost(
        username: str,
        domain: str,
        document_root: str,
        php_version: str = "8.1",
        upload_size: int = 128,
        memory_limit: int = 256,
        max_exec: int = 300,
        has_ssl: bool = False,
        cert_path: str = "",
        key_path: str = ""
    ) -> Dict[str, Any]:
        """Create Nginx virtual host configuration"""
        try:
            # Ensure document root exists
            os.makedirs(document_root, exist_ok=True)
            NginxService._run(f"chown -R {username}:{username} {document_root}")
            NginxService._run(f"chmod 755 {document_root}")

            # Generate config
            if has_ssl and cert_path and key_path:
                config = VHOST_SSL_TEMPLATE.format(
                    domain=domain, document_root=document_root, username=username,
                    php_version=php_version, upload_size=upload_size,
                    memory_limit=memory_limit, max_exec=max_exec,
                    cert_path=cert_path, key_path=key_path
                )
            else:
                config = VHOST_TEMPLATE.format(
                    domain=domain, document_root=document_root, username=username,
                    php_version=php_version, upload_size=upload_size,
                    memory_limit=memory_limit, max_exec=max_exec
                )

            # Write config file
            config_file = f"{settings.NGINX_SITES_AVAILABLE}/{domain}.conf"
            with open(config_file, "w") as f:
                f.write(config)

            # Enable site
            symlink = f"{settings.NGINX_SITES_ENABLED}/{domain}.conf"
            if not os.path.exists(symlink):
                os.symlink(config_file, symlink)

            # Test and reload Nginx
            test = NginxService._run("nginx -t")
            if test["success"]:
                NginxService._run("systemctl reload nginx")
                return {"success": True, "message": f"Virtual host created for {domain}", "config_file": config_file}
            else:
                # Remove invalid config
                os.remove(config_file)
                if os.path.exists(symlink):
                    os.remove(symlink)
                return {"success": False, "error": f"Nginx config test failed: {test['error']}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_vhost(domain: str) -> Dict[str, Any]:
        """Remove Nginx virtual host"""
        try:
            config_file = f"{settings.NGINX_SITES_AVAILABLE}/{domain}.conf"
            symlink = f"{settings.NGINX_SITES_ENABLED}/{domain}.conf"

            if os.path.exists(symlink):
                os.remove(symlink)
            if os.path.exists(config_file):
                os.remove(config_file)

            NginxService._run("systemctl reload nginx")
            return {"success": True, "message": f"Virtual host removed for {domain}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def enable_ssl(domain: str, cert_path: str, key_path: str, username: str) -> Dict[str, Any]:
        """Enable SSL for an existing virtual host"""
        doc_root_cmd = NginxService._run(f"grep 'root ' {settings.NGINX_SITES_AVAILABLE}/{domain}.conf | awk '{{print $2}}' | tr -d ';'")
        document_root = doc_root_cmd.get("output", f"/home/{username}/public_html")
        return NginxService.create_vhost(
            username=username, domain=domain, document_root=document_root,
            has_ssl=True, cert_path=cert_path, key_path=key_path
        )

    @staticmethod
    def add_subdomain(username: str, subdomain: str, parent_domain: str, document_root: str) -> Dict[str, Any]:
        """Add subdomain virtual host"""
        full_domain = f"{subdomain}.{parent_domain}"
        return NginxService.create_vhost(username=username, domain=full_domain, document_root=document_root)

    @staticmethod
    def reload() -> Dict[str, Any]:
        return NginxService._run("systemctl reload nginx")

    @staticmethod
    def restart() -> Dict[str, Any]:
        return NginxService._run("systemctl restart nginx")

    @staticmethod
    def test_config() -> Dict[str, Any]:
        return NginxService._run("nginx -t")

    @staticmethod
    def get_status() -> Dict[str, Any]:
        result = NginxService._run("systemctl status nginx --no-pager")
        return {"status": "running" if result["success"] else "stopped", "output": result.get("output", "")}

    @staticmethod
    def list_vhosts() -> list:
        """List all virtual host config files"""
        try:
            configs = []
            available = Path(settings.NGINX_SITES_AVAILABLE)
            enabled_path = Path(settings.NGINX_SITES_ENABLED)
            for conf_file in available.glob("*.conf"):
                enabled = (enabled_path / conf_file.name).exists()
                configs.append({"file": conf_file.name, "domain": conf_file.stem, "enabled": enabled})
            return configs
        except:
            return []
