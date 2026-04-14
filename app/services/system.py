"""
System Service - Server Monitoring & Control
Controls: CPU, RAM, Disk, Bandwidth, Services, Processes
"""
import subprocess
import psutil
import os
import platform
from datetime import datetime
from typing import Dict, List, Any

_IS_LINUX = platform.system() == "Linux"


class SystemService:

    @staticmethod
    def run_command(cmd: str, shell: bool = True) -> Dict[str, Any]:
        """Execute a system command safely"""
        try:
            result = subprocess.run(
                cmd, shell=shell, capture_output=True, text=True, timeout=30
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out", "returncode": -1}
        except Exception as e:
            return {"success": False, "error": str(e), "returncode": -1}

    @staticmethod
    def get_server_info() -> Dict[str, Any]:
        """Get comprehensive server information"""
        try:
            if _IS_LINUX:
                cpu_info = SystemService.run_command(
                    "grep 'model name' /proc/cpuinfo 2>/dev/null | head -1 | cut -d: -f2"
                )
                cpu_model = (cpu_info.get("stdout") or "").strip() or "Unknown"
            else:
                cpu_info = SystemService.run_command(
                    "sysctl -n machdep.cpu.brand_string 2>/dev/null || sysctl -n hw.model 2>/dev/null"
                )
                cpu_model = (cpu_info.get("stdout") or "").strip() or platform.processor() or "Unknown"
            return {
                "hostname": platform.node(),
                "os": f"{platform.system()} {platform.release()}",
                "kernel": platform.version(),
                "architecture": platform.machine(),
                "cpu_model": cpu_model,
                "cpu_count": psutil.cpu_count(logical=True) or 0,
                "cpu_count_physical": psutil.cpu_count(logical=False) or 0,
                "uptime": SystemService.get_uptime(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"),
                "python_version": platform.python_version(),
            }
        except Exception as e:
            return {
                "error": str(e),
                "hostname": platform.node(),
                "os": f"{platform.system()} {platform.release()}",
                "kernel": platform.version(),
                "architecture": platform.machine(),
                "cpu_model": "Unknown",
                "cpu_count": psutil.cpu_count(logical=True) or 0,
                "cpu_count_physical": psutil.cpu_count(logical=False) or 0,
                "uptime": SystemService.get_uptime(),
                "boot_time": "-",
                "python_version": platform.python_version(),
            }

    @staticmethod
    def get_uptime() -> str:
        """Get system uptime as human-readable string"""
        try:
            uptime_seconds = (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{days}d {hours}h {minutes}m"
        except:
            return "Unknown"

    @staticmethod
    def get_cpu_usage(interval: float = 0) -> Dict[str, Any]:
        """Get CPU usage statistics (interval=0 is non-blocking; use 1 on monitor for smoother sample)."""
        return {
            "percent": psutil.cpu_percent(interval=interval),
            "per_core": psutil.cpu_percent(interval=interval, percpu=True),
            "load_avg": list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0, 0, 0],
            "count": psutil.cpu_count(),
        }

    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """Get memory usage statistics"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total_mb": round(mem.total / 1024 / 1024),
            "used_mb": round(mem.used / 1024 / 1024),
            "free_mb": round(mem.available / 1024 / 1024),
            "percent": mem.percent,
            "swap_total_mb": round(swap.total / 1024 / 1024),
            "swap_used_mb": round(swap.used / 1024 / 1024),
            "swap_percent": swap.percent,
        }

    @staticmethod
    def get_disk_usage() -> List[Dict[str, Any]]:
        """Get disk usage for all partitions"""
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / 1024 / 1024 / 1024, 2),
                    "used_gb": round(usage.used / 1024 / 1024 / 1024, 2),
                    "free_gb": round(usage.free / 1024 / 1024 / 1024, 2),
                    "percent": round((usage.used / usage.total) * 100, 1),
                })
            except:
                pass
        return disks

    @staticmethod
    def get_network_usage() -> Dict[str, Any]:
        """Get network I/O statistics"""
        net = psutil.net_io_counters()
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family.name == 'AF_INET':
                    interfaces.append({"name": name, "ip": addr.address})
        return {
            "bytes_sent_mb": round(net.bytes_sent / 1024 / 1024, 2),
            "bytes_recv_mb": round(net.bytes_recv / 1024 / 1024, 2),
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "interfaces": interfaces,
        }

    @staticmethod
    def get_services_status() -> List[Dict[str, Any]]:
        """Check status of key hosting services"""
        services = [
            {"name": "nginx", "display": "Nginx Web Server"},
            {"name": "apache2", "display": "Apache Web Server"},
            {"name": "mysql", "display": "MySQL Database"},
            {"name": "postfix", "display": "Postfix Mail (SMTP)"},
            {"name": "dovecot", "display": "Dovecot Mail (IMAP/POP3)"},
            {"name": "bind9", "display": "BIND9 DNS Server"},
            {"name": "vsftpd", "display": "vsftpd FTP Server"},
            {"name": "fail2ban", "display": "Fail2ban Security"},
            {"name": "ufw", "display": "UFW Firewall"},
        ]

        result = []
        if not _IS_LINUX:
            for svc in services:
                result.append({
                    "name": svc["name"],
                    "display": svc["display"],
                    "status": "n/a",
                    "enabled": False,
                    "is_active": False,
                    "note": "systemctl غير متاح — استخدم Ubuntu/Debian للوضع الإنتاجي",
                })
            return result

        for svc in services:
            status = SystemService.run_command(f"systemctl is-active {svc['name']} 2>/dev/null")
            is_active = status.get("stdout") == "active"
            enabled = SystemService.run_command(f"systemctl is-enabled {svc['name']} 2>/dev/null")

            result.append({
                "name": svc["name"],
                "display": svc["display"],
                "status": "running" if is_active else "stopped",
                "enabled": enabled.get("stdout") == "enabled",
                "is_active": is_active,
            })
        return result

    @staticmethod
    def manage_service(service_name: str, action: str) -> Dict[str, Any]:
        """Start, stop, restart, or reload a service"""
        allowed_actions = ["start", "stop", "restart", "reload", "status"]
        allowed_services = ["nginx", "apache2", "mysql", "postfix", "dovecot", "bind9", "vsftpd", "fail2ban"]

        if action not in allowed_actions:
            return {"success": False, "error": f"Invalid action: {action}"}
        if service_name not in allowed_services:
            return {"success": False, "error": f"Service not managed: {service_name}"}
        if not _IS_LINUX:
            return {"success": False, "error": "systemctl متاح على Linux فقط (خادم استضافة)"}

        return SystemService.run_command(f"systemctl {action} {service_name}")

    @staticmethod
    def get_top_processes(limit: int = 15) -> List[Dict[str, Any]]:
        """Get top processes by CPU usage"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = dict(proc.info)
                if info.get("username") is None:
                    info["username"] = "-"
                processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(processes, key=lambda x: (x.get('cpu_percent') or 0), reverse=True)[:limit]

    @staticmethod
    def get_user_disk_usage(username: str, home_dir: str = "/home") -> int:
        """Get disk usage for a specific user in MB"""
        result = SystemService.run_command(f"du -sm {home_dir}/{username} 2>/dev/null | cut -f1")
        try:
            return int(result.get("stdout", 0))
        except:
            return 0

    @staticmethod
    def get_firewall_rules() -> List[Dict[str, Any]]:
        """Get UFW firewall rules"""
        if not _IS_LINUX:
            return [{"rule": "[preview] UFW غير مدعوم على هذا النظام — على Ubuntu: ufw status numbered"}]
        result = SystemService.run_command("ufw status numbered 2>/dev/null")
        lines = result.get("stdout", "").split("\n")
        rules = []
        for line in lines:
            if line.strip() and line[0] == "[":
                rules.append({"rule": line.strip()})
        return rules

    @staticmethod
    def add_firewall_rule(port: int, protocol: str = "tcp", action: str = "allow") -> Dict[str, Any]:
        """Add UFW rule"""
        if not _IS_LINUX:
            return {"success": False, "stderr": "UFW متاح على Linux فقط"}
        return SystemService.run_command(f"ufw {action} {port}/{protocol}")

    @staticmethod
    def get_system_logs(service: str = "nginx", lines: int = 100) -> List[str]:
        """Get last N lines from service logs"""
        log_paths = {
            "nginx": "/var/log/nginx/access.log",
            "nginx_error": "/var/log/nginx/error.log",
            "mysql": "/var/log/mysql/error.log",
            "postfix": "/var/log/mail.log",
            "auth": "/var/log/auth.log",
            "syslog": "/var/log/syslog",
        }
        darwin_paths = {
            "nginx": "/usr/local/var/log/nginx/access.log",
            "nginx_error": "/usr/local/var/log/nginx/error.log",
            "syslog": "/var/log/system.log",
            "auth": "/var/log/system.log",
            "mysql": "/tmp/nofal-mysql.log",
            "postfix": "/var/log/system.log",
        }
        log_path = log_paths.get(service, f"/var/log/{service}.log")
        if not _IS_LINUX and platform.system() == "Darwin":
            alt = darwin_paths.get(service)
            if alt and os.path.isfile(alt):
                log_path = alt
        result = SystemService.run_command(f"tail -n {lines} {log_path} 2>/dev/null")
        out = result.get("stdout", "").strip()
        if not out:
            return [
                f"(لا يوجد محتوى أو الملف غير موجود: {log_path})",
                "على خادم Ubuntu: السجلات في /var/log/nginx و /var/log/syslog",
            ]
        return out.split("\n")

    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """Get all stats for dashboard overview"""
        return {
            "cpu": SystemService.get_cpu_usage(),
            "memory": SystemService.get_memory_usage(),
            "disk": SystemService.get_disk_usage(),
            "network": SystemService.get_network_usage(),
            "services": SystemService.get_services_status(),
            "server_info": SystemService.get_server_info(),
        }
