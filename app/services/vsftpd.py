"""
FTP Service - vsftpd Management
Creates and manages FTP accounts
"""
import os
import subprocess
import crypt
from typing import Dict, Any, List
from app.config import settings


class FTPService:

    VSFTPD_CONF = "/etc/vsftpd.conf"
    VSFTPD_USERS_DIR = settings.VSFTPD_USER_DIR
    VSFTPD_PASSWD = "/etc/vsftpd/passwd"
    PAM_CONFIG = "/etc/pam.d/vsftpd"

    @staticmethod
    def _run(cmd: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return {"success": result.returncode == 0, "output": result.stdout.strip(), "error": result.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_ftp_account(username: str, password: str, home_dir: str, quota_mb: int = 0) -> Dict[str, Any]:
        """Create a virtual FTP account"""
        try:
            # Create home directory
            os.makedirs(home_dir, exist_ok=True)

            # Create user config file
            os.makedirs(FTPService.VSFTPD_USERS_DIR, exist_ok=True)
            user_conf = f"{FTPService.VSFTPD_USERS_DIR}/{username}"
            with open(user_conf, "w") as f:
                f.write(f"local_root={home_dir}\n")
                f.write("write_enable=YES\n")
                if quota_mb > 0:
                    f.write(f"# Quota: {quota_mb}MB\n")

            # Add to virtual password file using htpasswd-style
            hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
            passwd_file = FTPService.VSFTPD_PASSWD
            os.makedirs(os.path.dirname(passwd_file), exist_ok=True)
            with open(passwd_file, "a") as f:
                f.write(f"{username}:{hashed}\n")

            # Update the db file
            FTPService._run(f"db_load -T -t hash -f {passwd_file} {passwd_file}.db")

            # Restart vsftpd
            FTPService._run("systemctl restart vsftpd")

            return {"success": True, "message": f"FTP account created: {username}", "home_dir": home_dir}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_ftp_account(username: str) -> Dict[str, Any]:
        """Delete a virtual FTP account"""
        try:
            # Remove user config
            user_conf = f"{FTPService.VSFTPD_USERS_DIR}/{username}"
            if os.path.exists(user_conf):
                os.remove(user_conf)

            # Remove from password file
            if os.path.exists(FTPService.VSFTPD_PASSWD):
                with open(FTPService.VSFTPD_PASSWD, "r") as f:
                    lines = f.readlines()
                with open(FTPService.VSFTPD_PASSWD, "w") as f:
                    f.writelines([l for l in lines if not l.startswith(f"{username}:")])
                FTPService._run(f"db_load -T -t hash -f {FTPService.VSFTPD_PASSWD} {FTPService.VSFTPD_PASSWD}.db")

            FTPService._run("systemctl restart vsftpd")
            return {"success": True, "message": f"FTP account deleted: {username}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def change_ftp_password(username: str, new_password: str) -> Dict[str, Any]:
        """Change FTP account password"""
        try:
            hashed = crypt.crypt(new_password, crypt.mksalt(crypt.METHOD_SHA512))
            if os.path.exists(FTPService.VSFTPD_PASSWD):
                with open(FTPService.VSFTPD_PASSWD, "r") as f:
                    lines = f.readlines()
                new_lines = []
                for line in lines:
                    if line.startswith(f"{username}:"):
                        new_lines.append(f"{username}:{hashed}\n")
                    else:
                        new_lines.append(line)
                with open(FTPService.VSFTPD_PASSWD, "w") as f:
                    f.writelines(new_lines)
                FTPService._run(f"db_load -T -t hash -f {FTPService.VSFTPD_PASSWD} {FTPService.VSFTPD_PASSWD}.db")

            FTPService._run("systemctl restart vsftpd")
            return {"success": True, "message": "FTP password changed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def list_ftp_accounts(prefix: str = None) -> List[str]:
        """List FTP accounts"""
        try:
            accounts = []
            if os.path.exists(FTPService.VSFTPD_USERS_DIR):
                for f in os.listdir(FTPService.VSFTPD_USERS_DIR):
                    if prefix and not f.startswith(prefix):
                        continue
                    accounts.append(f)
            return accounts
        except:
            return []

    @staticmethod
    def get_service_status() -> Dict[str, str]:
        result = FTPService._run("systemctl is-active vsftpd")
        return {"status": result.get("output", "unknown")}
