# 🚀 Nofal Panel

**Hosting Control Panel - مثل WHM/cPanel بالضبط**

Built with FastAPI (Python) | Full Server Control | Open Source

---

## 📋 المميزات

### WHM (Admin Panel)
- ✅ إنشاء/حذف/تعليق حسابات الاستضافة
- ✅ إدارة الباقات والخطط (Package Manager)
- ✅ مراقبة الموارد (CPU / RAM / Disk / Bandwidth)
- ✅ إدارة الخدمات (Nginx, MySQL, Postfix, BIND9, vsftpd)
- ✅ محرر DNS (Zone Editor)
- ✅ إدارة الجدار الناري (UFW Firewall)
- ✅ سجلات الخادم (Server Logs)
- ✅ سجل النشاط (Activity Log)
- ✅ تسجيل الدخول كمستخدم (Ghost Login)

### cPanel (User Panel)
- ✅ File Manager (رفع، حذف، تعديل، تغيير صلاحيات)
- ✅ Domain Manager (Addon, Subdomain, Parked, Redirects)
- ✅ Email Accounts (إنشاء، حذف، Forwarder، Autoresponder)
- ✅ MySQL Databases (إنشاء، حذف، تغيير كلمة مرور)
- ✅ FTP Accounts
- ✅ SSL/TLS (Let's Encrypt + Self-Signed)
- ✅ Cron Jobs
- ✅ Resource Usage (Disk & Bandwidth)

---

## 🖥️ متطلبات السيرفر

- **OS:** Ubuntu 20.04 / 22.04 أو Debian 11 / 12
- **RAM:** 1GB minimum (2GB recommended)
- **Disk:** 10GB minimum
- **User:** root access required

---

## ⚡ التنصيب السريع

```bash
# 1. حمّل المشروع
git clone https://github.com/YOUR_USERNAME/nofal-panel.git
cd nofal-panel

# 2. شغّل الـ installer
chmod +x install.sh
sudo bash install.sh
```

بعد التنصيب:
```
Panel URL:   http://YOUR_SERVER_IP:2083
Username:    admin
Password:    NofaLPanel@2024
```

> ⚠️ **غيّر كلمة المرور فوراً بعد أول تسجيل دخول!**

---

## 🛠️ التنصيب اليدوي (للتطوير)

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/nofal-panel.git
cd nofal-panel

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit settings

# Run the panel
uvicorn app.main:app --host 0.0.0.0 --port 2083 --reload
```

---

## 📁 Project Structure

```
nofal-panel/
├── install.sh              ← الـ installer الرئيسي
├── uninstall.sh            ← إزالة البانل
├── requirements.txt        ← Python dependencies
├── .env.example            ← مثال على الإعدادات
├── app/
│   ├── main.py             ← FastAPI entry point
│   ├── config.py           ← الإعدادات
│   ├── database.py         ← SQLAlchemy setup
│   ├── auth.py             ← JWT Authentication
│   ├── models/             ← Database Models
│   │   ├── user.py
│   │   ├── package.py
│   │   ├── domain.py
│   │   ├── email_account.py
│   │   ├── db_account.py
│   │   ├── ftp_account.py
│   │   ├── cron_job.py
│   │   ├── ssl_cert.py
│   │   └── activity_log.py
│   ├── routers/
│   │   ├── auth.py         ← Login/Logout
│   │   ├── admin/          ← WHM Routes
│   │   │   ├── accounts.py
│   │   │   ├── packages.py
│   │   │   ├── server.py
│   │   │   └── dns.py
│   │   └── cpanel/         ← User Panel Routes
│   │       ├── dashboard.py
│   │       ├── domains.py
│   │       ├── email.py
│   │       ├── databases.py
│   │       ├── ftp.py
│   │       ├── ssl.py
│   │       ├── cron.py
│   │       └── files.py
│   ├── services/           ← Server Control Layer
│   │   ├── system.py       ← CPU/RAM/Disk monitoring
│   │   ├── nginx.py        ← Nginx vhost management
│   │   ├── bind9.py        ← DNS zone management
│   │   ├── postfix.py      ← Email server
│   │   ├── mysql_service.py← MySQL management
│   │   ├── vsftpd.py       ← FTP management
│   │   ├── certbot.py      ← SSL certificates
│   │   └── account_manager.py ← Full account lifecycle
│   └── templates/          ← Jinja2 HTML Templates
├── static/
│   ├── css/style.css
│   └── js/main.js
└── README.md
```

---

## 🔧 إدارة الخدمة

```bash
# تشغيل
systemctl start nofal-panel

# إيقاف
systemctl stop nofal-panel

# إعادة تشغيل
systemctl restart nofal-panel

# عرض الـ logs
journalctl -u nofal-panel -f

# حالة الخدمة
systemctl status nofal-panel
```

---

## 🔒 الأمان

بعد التنصيب، يُنصح بـ:
1. تغيير كلمة مرور admin فوراً
2. تغيير `SECRET_KEY` في ملف `.env`
3. تفعيل SSL للبانل (Let's Encrypt)
4. تفعيل Fail2ban لحماية من brute force

---

## 🤝 Contributing

المشروع مفتوح المصدر. Contributions are welcome!

---

## 📄 License

MIT License - Free to use and modify

---

**Made with ❤️ by Nofal | Powered by FastAPI + Python**
