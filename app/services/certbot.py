"""
SSL Service - Let's Encrypt + Self-Signed Certificate Management
"""
import os
import subprocess
from datetime import datetime
from typing import Dict, Any, List
from app.config import settings


class SSLService:

    CERTS_DIR = "/etc/letsencrypt/live"

    @staticmethod
    def _run(cmd: str, timeout: int = 120) -> Dict[str, Any]:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return {"success": result.returncode == 0, "output": result.stdout.strip(), "error": result.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "SSL operation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def issue_letsencrypt(domain: str, email: str = None, webroot: str = None) -> Dict[str, Any]:
        """Issue Let's Encrypt certificate for a domain"""
        cert_email = email or settings.CERTBOT_EMAIL
        www_domain = f"www.{domain}"

        if webroot:
            cmd = (f"certbot certonly --webroot -w {webroot} "
                   f"-d {domain} -d {www_domain} "
                   f"--email {cert_email} --agree-tos --non-interactive")
        else:
            cmd = (f"certbot certonly --nginx "
                   f"-d {domain} -d {www_domain} "
                   f"--email {cert_email} --agree-tos --non-interactive")

        result = SSLService._run(cmd, timeout=180)
        if result["success"]:
            return {
                "success": True,
                "message": f"SSL certificate issued for {domain}",
                "cert_path": f"{SSLService.CERTS_DIR}/{domain}/fullchain.pem",
                "key_path": f"{SSLService.CERTS_DIR}/{domain}/privkey.pem",
                "chain_path": f"{SSLService.CERTS_DIR}/{domain}/chain.pem",
            }
        return {"success": False, "error": result.get("error", result.get("output", "Certificate issuance failed"))}

    @staticmethod
    def renew_certificate(domain: str) -> Dict[str, Any]:
        """Renew an existing Let's Encrypt certificate"""
        result = SSLService._run(f"certbot renew --cert-name {domain} --non-interactive", timeout=180)
        return {"success": result["success"], "output": result.get("output", ""), "error": result.get("error", "")}

    @staticmethod
    def renew_all() -> Dict[str, Any]:
        """Renew all certificates"""
        result = SSLService._run("certbot renew --non-interactive", timeout=300)
        return {"success": result["success"], "output": result.get("output", "")}

    @staticmethod
    def revoke_certificate(domain: str) -> Dict[str, Any]:
        """Revoke and delete a certificate"""
        cert_path = f"{SSLService.CERTS_DIR}/{domain}/cert.pem"
        result = SSLService._run(f"certbot revoke --cert-path {cert_path} --delete-after-revoke --non-interactive")
        return {"success": result["success"], "message": f"Certificate revoked for {domain}"}

    @staticmethod
    def create_self_signed(domain: str, output_dir: str = "/etc/ssl/certs") -> Dict[str, Any]:
        """Create a self-signed certificate for development/testing"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            cert_path = f"{output_dir}/{domain}.crt"
            key_path = f"{output_dir}/{domain}.key"

            cmd = (f"openssl req -x509 -nodes -days 365 -newkey rsa:2048 "
                   f"-keyout {key_path} -out {cert_path} "
                   f"-subj '/CN={domain}/O=Nofal Panel/C=EG'")

            result = SSLService._run(cmd)
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Self-signed certificate created for {domain}",
                    "cert_path": cert_path,
                    "key_path": key_path,
                }
            return {"success": False, "error": result.get("error", "Failed to create certificate")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_cert_info(domain: str) -> Dict[str, Any]:
        """Get certificate expiry and details"""
        cert_path = f"{SSLService.CERTS_DIR}/{domain}/cert.pem"
        if not os.path.exists(cert_path):
            return {"exists": False}

        result = SSLService._run(f"openssl x509 -noout -dates -in {cert_path}")
        if result["success"]:
            lines = result["output"].split("\n")
            info = {}
            for line in lines:
                if "notBefore" in line:
                    info["issued"] = line.split("=", 1)[1].strip()
                elif "notAfter" in line:
                    info["expires"] = line.split("=", 1)[1].strip()
            info["exists"] = True
            info["cert_path"] = cert_path
            info["key_path"] = f"{SSLService.CERTS_DIR}/{domain}/privkey.pem"
            return info
        return {"exists": False, "error": result.get("error", "")}

    @staticmethod
    def list_certificates() -> List[Dict[str, Any]]:
        """List all managed certificates"""
        certs = []
        if os.path.exists(SSLService.CERTS_DIR):
            for domain in os.listdir(SSLService.CERTS_DIR):
                cert_info = SSLService.get_cert_info(domain)
                if cert_info.get("exists"):
                    cert_info["domain"] = domain
                    certs.append(cert_info)
        return certs
