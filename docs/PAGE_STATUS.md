# حالة صفحات وميزات Nofal Panel

المصدر البرمجي للحقيقة: `app/status_registry.py` — يُحدَّث مع كل إصدار.

| الحالة | المعنى |
|--------|--------|
| **live** | مسار يعمل في الواجهة والخلفية ضمن النطاق المدعوم |
| **partial** | يعمل جزئياً أو يعتمد على Linux (systemctl، UFW، …) |
| **planned** | مذكور في خارطة الطريق لمطابقة cPanel؛ لا مسار بعد |

## الوصول

- **واجهة HTML:** `/status` (يتطلب تسجيل الدخول)
- **JSON:** `/api/status` (يتطلب تسجيل الدخول)

## ملخص العدد

يُحسب تلقائياً في الواجهة من `REGISTRY`.

## أقسام cPanel (الجذر)

- **Dashboard Jupiter:** `/cpanel/dashboard` — شبكة أيقونات + إحصائيات؛ أدوات مُخطّة تربط بـ `/cpanel/feature-unavailable?key=...`
- **الملفات:** File Manager، FTP، Cron، Terminal، SSL، إلخ — انظر الجدول في التطبيق

## ملاحظات الإنتاج

- للسلوك مثل WHM/cPanel الكامل: Ubuntu/Debian + root + `install.sh` على الخادم.
- تطوير macOS/Windows: الواجهة تعرض البيانات المحلية؛ التحكم في الخدمات عبر `systemctl` غير متاح.
