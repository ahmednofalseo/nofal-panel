"""
Single source of truth for /status and docs — which routes exist and their maturity.
status: live | partial | planned
"""
from typing import List, Dict, Any

REGISTRY: List[Dict[str, Any]] = [
    {"path": "/status", "name": "حالة النظام (واجهة)", "area": "System", "status": "live", "note": "يتطلب تسجيل الدخول"},
    {"path": "/api/status", "name": "حالة النظام (JSON)", "area": "System", "status": "live", "note": "يتطلب تسجيل الدخول"},
    # Auth
    {"path": "/auth/login", "name": "تسجيل الدخول", "area": "Auth", "status": "live", "note": ""},
    {"path": "/auth/logout", "name": "تسجيل الخروج", "area": "Auth", "status": "live", "note": ""},
    {"path": "/auth/change-password", "name": "تغيير كلمة المرور", "area": "Auth", "status": "live", "note": ""},
    # WHM Admin
    {"path": "/admin/dashboard", "name": "WHM Home", "area": "WHM", "status": "live", "note": ""},
    {"path": "/admin/accounts", "name": "قائمة الحسابات", "area": "WHM", "status": "live", "note": ""},
    {"path": "/admin/accounts/create", "name": "إنشاء حساب", "area": "WHM", "status": "live", "note": "يتطلب Linux للموارد على الخادم"},
    {"path": "/admin/packages", "name": "الباقات", "area": "WHM", "status": "live", "note": ""},
    {"path": "/admin/packages/create", "name": "إنشاء باقة", "area": "WHM", "status": "live", "note": ""},
    {"path": "/admin/dns", "name": "مدير DNS", "area": "WHM", "status": "live", "note": "BIND على Linux"},
    {"path": "/admin/server/monitor", "name": "المراقبة", "area": "WHM", "status": "live", "note": "psutil يعمل على كل الأنظمة"},
    {"path": "/admin/server/services", "name": "الخدمات", "area": "WHM", "status": "partial", "note": "systemctl على Linux فقط"},
    {"path": "/admin/server/logs", "name": "سجلات الخادم", "area": "WHM", "status": "partial", "note": "مسارات السجلات تختلف حسب OS"},
    {"path": "/admin/server/firewall", "name": "الجدار الناري", "area": "WHM", "status": "partial", "note": "UFW على Linux"},
    {"path": "/admin/server/processes", "name": "العمليات", "area": "WHM", "status": "live", "note": ""},
    {"path": "/admin/server/info", "name": "معلومات الخادم", "area": "WHM", "status": "live", "note": ""},
    {"path": "/admin/logs/activity", "name": "سجل النشاط", "area": "WHM", "status": "live", "note": ""},
    # cPanel user
    {"path": "/cpanel/dashboard", "name": "cPanel الرئيسية", "area": "cPanel", "status": "live", "note": "واجهة Jupiter-style"},
    {"path": "/cpanel/files", "name": "مدير الملفات", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/domains", "name": "النطاقات", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/email", "name": "البريد", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/databases", "name": "قواعد MySQL", "area": "cPanel", "status": "live", "note": "يتطلب اتصال MySQL"},
    {"path": "/cpanel/ftp", "name": "FTP", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/ssl", "name": "SSL/TLS", "area": "cPanel", "status": "live", "note": "Certbot على الخادم"},
    {"path": "/cpanel/cron", "name": "Cron", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/terminal", "name": "Terminal", "area": "cPanel", "status": "partial", "note": "PTY على Unix"},
    {"path": "/cpanel/feature-unavailable", "name": "ميزة قيد التطوير", "area": "cPanel", "status": "live", "note": "صفحة توضيحية للأدوات المخططة (?key=)"},
    # Planned (parity with cPanel Jupiter — roadmap)
    {"path": "—", "name": "phpMyAdmin (واجهة)", "area": "cPanel", "status": "planned", "note": "رابط خارجي أو تضمين لاحقاً"},
    {"path": "—", "name": "Metrics / Visitors / AWStats", "area": "cPanel", "status": "planned", "note": "لوحة المقاييس"},
    {"path": "—", "name": "Backup Wizard", "area": "cPanel", "status": "planned", "note": ""},
    {"path": "—", "name": "Softaculous", "area": "cPanel", "status": "planned", "note": "تكامل منفصل"},
    {"path": "—", "name": "MultiPHP Manager", "area": "cPanel", "status": "planned", "note": ""},
    {"path": "—", "name": "IP Blocker / Hotlink", "area": "cPanel", "status": "planned", "note": ""},
]


def counts_by_status() -> Dict[str, int]:
    c = {"live": 0, "partial": 0, "planned": 0}
    for row in REGISTRY:
        s = row.get("status", "planned")
        if s in c:
            c[s] += 1
    return c
