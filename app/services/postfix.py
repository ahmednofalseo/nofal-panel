"""
Mail Service - Postfix + Dovecot Management
Creates email accounts, forwarders, aliases
"""
import os
import subprocess
import crypt
from typing import Dict, Any, List
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MailService:

    VIRTUAL_MAILBOX_BASE = "/var/mail/vhosts"
    POSTFIX_VIRTUAL_DOMAINS = "/etc/postfix/virtual_domains"
    POSTFIX_VIRTUAL_MAILBOX = "/etc/postfix/virtual_mailbox"
    POSTFIX_VIRTUAL_ALIAS = "/etc/postfix/virtual_alias"
    DOVECOT_PASSWD = "/etc/dovecot/users"

    @staticmethod
    def _run(cmd: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return {"success": result.returncode == 0, "output": result.stdout.strip(), "error": result.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def setup_domain(domain: str) -> Dict[str, Any]:
        """Set up email infrastructure for a new domain"""
        try:
            # Create mail directory
            mail_dir = f"{MailService.VIRTUAL_MAILBOX_BASE}/{domain}"
            os.makedirs(mail_dir, exist_ok=True)
            MailService._run(f"chown -R vmail:vmail {mail_dir}")

            # Add to virtual domains
            if os.path.exists(MailService.POSTFIX_VIRTUAL_DOMAINS):
                with open(MailService.POSTFIX_VIRTUAL_DOMAINS, "r") as f:
                    content = f.read()
                if domain not in content:
                    with open(MailService.POSTFIX_VIRTUAL_DOMAINS, "a") as f:
                        f.write(f"{domain}\tOK\n")
                    MailService._run(f"postmap {MailService.POSTFIX_VIRTUAL_DOMAINS}")

            return {"success": True, "message": f"Mail domain configured: {domain}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_email_account(email: str, password: str, quota_mb: int = 1024) -> Dict[str, Any]:
        """Create a new email account"""
        try:
            username, domain = email.split("@", 1)
            mail_dir = f"{MailService.VIRTUAL_MAILBOX_BASE}/{domain}/{username}/"

            # Create mailbox directory
            os.makedirs(mail_dir, exist_ok=True)
            MailService._run(f"chown -R vmail:vmail {mail_dir}")

            # Add to virtual_mailbox map
            if os.path.exists(MailService.POSTFIX_VIRTUAL_MAILBOX):
                with open(MailService.POSTFIX_VIRTUAL_MAILBOX, "a") as f:
                    f.write(f"{email}\t{domain}/{username}/\n")
                MailService._run(f"postmap {MailService.POSTFIX_VIRTUAL_MAILBOX}")

            # Add Dovecot user with password
            hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
            if os.path.exists(MailService.DOVECOT_PASSWD):
                with open(MailService.DOVECOT_PASSWD, "a") as f:
                    quota_bytes = quota_mb * 1024 * 1024
                    f.write(f"{email}:{{{hashed}}}:vmail:vmail::{MailService.VIRTUAL_MAILBOX_BASE}::userdb_quota_rule=*:bytes={quota_bytes}\n")

            # Reload services
            MailService._run("postfix reload")
            MailService._run("systemctl reload dovecot")

            return {"success": True, "message": f"Email account created: {email}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_email_account(email: str) -> Dict[str, Any]:
        """Delete an email account"""
        try:
            username, domain = email.split("@", 1)
            mail_dir = f"{MailService.VIRTUAL_MAILBOX_BASE}/{domain}/{username}"

            # Remove from virtual_mailbox
            for filepath in [MailService.POSTFIX_VIRTUAL_MAILBOX, MailService.DOVECOT_PASSWD]:
                if os.path.exists(filepath):
                    with open(filepath, "r") as f:
                        lines = f.readlines()
                    with open(filepath, "w") as f:
                        f.writelines([l for l in lines if not l.startswith(email)])

            # Rebuild postmap
            MailService._run(f"postmap {MailService.POSTFIX_VIRTUAL_MAILBOX}")
            MailService._run("postfix reload")
            MailService._run("systemctl reload dovecot")

            return {"success": True, "message": f"Email account deleted: {email}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def change_email_password(email: str, new_password: str) -> Dict[str, Any]:
        """Change email account password"""
        try:
            hashed = crypt.crypt(new_password, crypt.mksalt(crypt.METHOD_SHA512))
            if os.path.exists(MailService.DOVECOT_PASSWD):
                with open(MailService.DOVECOT_PASSWD, "r") as f:
                    lines = f.readlines()

                new_lines = []
                for line in lines:
                    if line.startswith(email + ":"):
                        parts = line.split(":")
                        parts[1] = f"{{{hashed}}}"
                        new_lines.append(":".join(parts))
                    else:
                        new_lines.append(line)

                with open(MailService.DOVECOT_PASSWD, "w") as f:
                    f.writelines(new_lines)

            MailService._run("systemctl reload dovecot")
            return {"success": True, "message": "Password changed successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_forwarder(source_email: str, destination_email: str) -> Dict[str, Any]:
        """Create email forwarder"""
        try:
            if os.path.exists(MailService.POSTFIX_VIRTUAL_ALIAS):
                with open(MailService.POSTFIX_VIRTUAL_ALIAS, "a") as f:
                    f.write(f"{source_email}\t{destination_email}\n")
                MailService._run(f"postmap {MailService.POSTFIX_VIRTUAL_ALIAS}")
                MailService._run("postfix reload")

            return {"success": True, "message": f"Forwarder created: {source_email} -> {destination_email}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_forwarder(source_email: str) -> Dict[str, Any]:
        """Delete email forwarder"""
        try:
            if os.path.exists(MailService.POSTFIX_VIRTUAL_ALIAS):
                with open(MailService.POSTFIX_VIRTUAL_ALIAS, "r") as f:
                    lines = f.readlines()
                with open(MailService.POSTFIX_VIRTUAL_ALIAS, "w") as f:
                    f.writelines([l for l in lines if not l.startswith(source_email)])
                MailService._run(f"postmap {MailService.POSTFIX_VIRTUAL_ALIAS}")
                MailService._run("postfix reload")

            return {"success": True, "message": f"Forwarder deleted: {source_email}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_mail_queue() -> Dict[str, Any]:
        """Get current mail queue"""
        result = MailService._run("mailq")
        return {"queue": result.get("output", "Mail queue is empty")}

    @staticmethod
    def flush_mail_queue() -> Dict[str, Any]:
        """Flush the mail queue"""
        return MailService._run("postqueue -f")

    @staticmethod
    def get_service_status() -> Dict[str, str]:
        """Check Postfix and Dovecot status"""
        postfix = MailService._run("systemctl is-active postfix")
        dovecot = MailService._run("systemctl is-active dovecot")
        return {
            "postfix": postfix.get("output", "unknown"),
            "dovecot": dovecot.get("output", "unknown"),
        }
