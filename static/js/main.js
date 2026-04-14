// =============================================
//   NOFAL PANEL - Main JavaScript
// =============================================

/** Merge into fetch() headers for POST/PUT/PATCH/DELETE (CSRF middleware). */
function csrfFetchHeaders() {
  const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  const t = m ? decodeURIComponent(m[1]) : '';
  return t ? { 'X-CSRF-Token': t } : {};
}

document.addEventListener('DOMContentLoaded', function() {
  // Sidebar Toggle
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  }

  // cPanel Jupiter: filter sidebar menu
  const cpanelSearch = document.getElementById('cpanelSearch');
  const cpanelMenu = document.getElementById('cpanelSidebarMenu');
  if (cpanelSearch && cpanelMenu) {
    cpanelSearch.addEventListener('input', function() {
      const q = this.value.trim().toLowerCase();
      cpanelMenu.querySelectorAll(':scope > li').forEach(function(li) {
        if (li.classList.contains('menu-header')) {
          li.style.display = q ? 'none' : '';
          return;
        }
        const text = (li.textContent || '').toLowerCase();
        li.style.display = !q || text.includes(q) ? '' : 'none';
      });
      if (q) {
        cpanelMenu.querySelectorAll(':scope > li.menu-header').forEach(function(h) {
          let el = h.nextElementSibling;
          let showHeader = false;
          while (el && !el.classList.contains('menu-header')) {
            if (el.style.display !== 'none') showHeader = true;
            el = el.nextElementSibling;
          }
          h.style.display = showHeader ? '' : 'none';
        });
      }
    });
  }

  // Server Time
  const timeEl = document.getElementById('serverTime');
  if (timeEl) {
    setInterval(() => {
      timeEl.textContent = new Date().toLocaleTimeString();
    }, 1000);
    timeEl.textContent = new Date().toLocaleTimeString();
  }

  // Auto-dismiss alerts after 5 seconds
  document.querySelectorAll('.alert.alert-success').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // Password strength indicator
  const passInputs = document.querySelectorAll('input[type="password"][name*="password"]');
  passInputs.forEach(input => {
    input.addEventListener('input', function() {
      const strength = getPasswordStrength(this.value);
      let indicator = this.parentElement.querySelector('.pass-strength');
      if (!indicator) {
        indicator = document.createElement('small');
        indicator.className = 'pass-strength d-block mt-1';
        this.parentElement.after(indicator);
      }
      indicator.className = 'pass-strength d-block mt-1 text-' + strength.color;
      indicator.textContent = '🔒 ' + strength.label;
    });
  });

  // Confirm delete buttons
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', function(e) {
      if (!confirm(this.dataset.confirm)) e.preventDefault();
    });
  });

  // File manager - detect file type for icon
  document.querySelectorAll('.file-name').forEach(el => {
    const name = el.textContent.trim();
    const icon = el.previousElementSibling;
    if (!icon) return;
    const ext = name.split('.').pop().toLowerCase();
    const types = {
      'php': 'php', 'html': 'html', 'htm': 'html',
      'js': 'js', 'css': 'css',
      'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image', 'svg': 'image',
      'zip': 'archive', 'tar': 'archive', 'gz': 'archive',
    };
    if (types[ext]) icon.classList.add(types[ext]);
  });
});

function getPasswordStrength(pass) {
  let score = 0;
  if (pass.length >= 8) score++;
  if (pass.length >= 12) score++;
  if (/[A-Z]/.test(pass)) score++;
  if (/[0-9]/.test(pass)) score++;
  if (/[^A-Za-z0-9]/.test(pass)) score++;
  if (score <= 1) return {label: 'Weak', color: 'danger'};
  if (score <= 3) return {label: 'Medium', color: 'warning'};
  return {label: 'Strong', color: 'success'};
}

// Service Management (Admin)
function manageService(name, action) {
  const btn = event.target;
  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

  fetch(`/admin/server/services/${name}/${action}`, {
    method: 'POST',
    headers: { ...csrfFetchHeaders(), 'Content-Type': 'application/json' },
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      showToast(`Service ${name} ${action}ed successfully`, 'success');
      setTimeout(() => location.reload(), 1500);
    } else {
      showToast(`Error: ${data.error || 'Operation failed'}`, 'danger');
      btn.disabled = false;
    }
  })
  .catch(() => {
    showToast('Network error', 'danger');
    btn.disabled = false;
  });
}

// Toast notification
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `alert alert-${type} position-fixed bottom-0 end-0 m-3`;
  toast.style.cssText = 'z-index:9999;max-width:350px;box-shadow:0 4px 15px rgba(0,0,0,0.2)';
  toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>${message}`;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// Copy to clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard!', 'success'));
}

// Generate random password
function generatePassword(inputId) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%';
  let pass = '';
  for (let i = 0; i < 16; i++) pass += chars[Math.floor(Math.random() * chars.length)];
  const input = document.getElementById(inputId);
  if (input) { input.value = pass; input.type = 'text'; }
  return pass;
}
