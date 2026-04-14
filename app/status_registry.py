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
    {"path": "/cpanel/email", "name": "البريد", "area": "cPanel", "status": "live", "note": "واجهة كاملة + WEBMAIL_URL + وضع لوحة بدون Postfix"},
    {"path": "/cpanel/email/open-webmail", "name": "توجيه ويب ميل", "area": "cPanel", "status": "live", "note": "?account="},
    {"path": "/cpanel/databases", "name": "قواعد MySQL", "area": "cPanel", "status": "live", "note": "يتطلب اتصال MySQL"},
    {"path": "/cpanel/ftp", "name": "FTP", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/ssl", "name": "SSL/TLS", "area": "cPanel", "status": "live", "note": "Certbot على الخادم"},
    {"path": "/cpanel/cron", "name": "Cron", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/terminal", "name": "Terminal", "area": "cPanel", "status": "partial", "note": "PTY على Unix"},
    {"path": "/cpanel/feature-unavailable", "name": "ميزة غير معروفة", "area": "cPanel", "status": "live", "note": "?key= للتوافق"},
    {"path": "/cpanel/disk-usage", "name": "استخدام القرص", "area": "cPanel", "status": "live", "note": "du + حصة الحساب"},
    {"path": "/cpanel/backup", "name": "النسخ الاحتياطي", "area": "cPanel", "status": "partial", "note": "جدولة في اللوحة؛ التنفيذ على الخادم يدوي"},
    {"path": "/cpanel/git", "name": "Git", "area": "cPanel", "status": "live", "note": "مسح .git تحت الحساب"},
    {"path": "/cpanel/phpmyadmin", "name": "phpMyAdmin", "area": "cPanel", "status": "partial", "note": "PHPMYADMIN_URL"},
    {"path": "/cpanel/remote-mysql", "name": "Remote MySQL", "area": "cPanel", "status": "live", "note": "قائمة عناوين في قاعدة اللوحة"},
    {"path": "/cpanel/addon-domains", "name": "نطاقات إضافية", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/redirects", "name": "إعادة التوجيه", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/zone-editor", "name": "محرر المنطقة DNS", "area": "cPanel", "status": "live", "note": "سجلات dns_records"},
    {"path": "/cpanel/forwarders", "name": "الموجهات", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/autoresponder", "name": "الرد الآلي", "area": "cPanel", "status": "live", "note": ""},
    {"path": "/cpanel/spam", "name": "عامل السبام", "area": "cPanel", "status": "partial", "note": "تفضيلات؛ ربط خادم لاحقاً"},
    {"path": "/cpanel/metrics/visitors", "name": "الزوار (سجل)", "area": "cPanel", "status": "partial", "note": "ذيل access.log"},
    {"path": "/cpanel/metrics/errors", "name": "أخطاء nginx", "area": "cPanel", "status": "partial", "note": "ذيل error.log"},
    {"path": "/cpanel/metrics/bandwidth", "name": "النطاق الترددي", "area": "cPanel", "status": "live", "note": "من بيانات المستخدم"},
    {"path": "/cpanel/metrics/raw-log", "name": "سجل خام", "area": "cPanel", "status": "partial", "note": ""},
    {"path": "/cpanel/ssh", "name": "SSH مفتاح", "area": "cPanel", "status": "partial", "note": "تخزين في اللوحة"},
    {"path": "/cpanel/ip-blocker", "name": "حظر IP", "area": "cPanel", "status": "partial", "note": "قائمة؛ تطبيق على الخادم يدوي"},
    {"path": "/cpanel/hotlink", "name": "Hotlink", "area": "cPanel", "status": "partial", "note": ""},
    {"path": "/cpanel/multiphp", "name": "MultiPHP", "area": "cPanel", "status": "partial", "note": "إصدار لكل نطاق في اللوحة"},
    {"path": "/cpanel/optimize", "name": "تحسين الموقع", "area": "cPanel", "status": "partial", "note": "تفضيلات"},
    {"path": "/cpanel/ini-editor", "name": "محرر INI", "area": "cPanel", "status": "live", "note": "مقتطف محفوظ"},
    {"path": "/cpanel/track-dns", "name": "تتبع DNS", "area": "cPanel", "status": "live", "note": "dnspython"},
    {"path": "—", "name": "Softaculous", "area": "cPanel", "status": "planned", "note": "تكامل منفصل"},
]


def counts_by_status() -> Dict[str, int]:
    c = {"live": 0, "partial": 0, "planned": 0}
    for row in REGISTRY:
        s = row.get("status", "planned")
        if s in c:
            c[s] += 1
    return c
