/**
 * Village Resources and Grievance Management System
 * Client-side Controller & UI Interaction Scripts
 * Pure Vanilla JavaScript (Zero External Libraries)
 */

// =========================================================================
// 1. MULTILINGUAL TRANSLATION DICTIONARY (English, Marathi, Hindi)
// =========================================================================

const TRANSLATIONS = {
  en: {
    // Navigation
    nav_home: "Home",
    nav_resources: "Resources",
    nav_grievance: "Report Grievance",
    nav_track: "Track Grievance",
    nav_dashboard: "Dashboard",
    nav_admin: "Admin Portal",
    nav_login: "Login",
    nav_register: "Register",
    nav_logout: "Logout",

    // Hero & Home
    hero_pill: "Digital Village Governance Platform",
    hero_title: "Village Resources & Grievance Management System",
    hero_subtitle: "Connecting Villagers with Essential Civic Resources and Faster Transparent Grievance Redressal.",
    btn_explore_resources: "Explore Resources",
    btn_report_grievance: "Report a Grievance",
    features_title: "Key Platform Services",
    features_subtitle: "Empowering rural communities with accessible digital services and responsive administration.",

    // General terms
    status: "Status",
    priority: "Priority",
    department: "Department",
    category: "Category",
    action: "Action",
    date: "Date",
    details: "Details",
    search_placeholder: "Search village resources or services...",
    all: "All",
    close: "Close",
    save: "Save Changes",
    submit: "Submit",
    cancel: "Cancel",

    // Grievance Statuses
    status_submitted: "Submitted",
    status_verified: "Verified",
    status_assigned: "Assigned",
    status_in_progress: "In Progress",
    status_resolved: "Resolved",
    status_rejected: "Rejected",

    // Grievance Priorities
    priority_emergency: "Emergency",
    priority_high: "High",
    priority_medium: "Medium",
    priority_low: "Low"
  },

  mr: {
    // Navigation
    nav_home: "मुख्यपृष्ठ",
    nav_resources: "ग्राम साधने",
    nav_grievance: "तक्रार नोंदवा",
    nav_track: "तक्रार स्थिती",
    nav_dashboard: "डॅशबोर्ड",
    nav_admin: "प्रशासक कक्ष",
    nav_login: "लॉगिन",
    nav_register: "नोंदणी",
    nav_logout: "बाहेर पडा",

    // Hero & Home
    hero_pill: "डिजिटल ग्राम प्रशासन व्यासपीठ",
    hero_title: "ग्राम साधने आणि तक्रार निवारण प्रणाली",
    hero_subtitle: "ग्रामस्थांना आवश्यक पायाभूत सुविधांशी जोडणे आणि तक्रारींचे जलद व पारदर्शक निवारण करणे.",
    btn_explore_resources: "ग्राम साधने पहा",
    btn_report_grievance: "तक्रार नोंदवा",
    features_title: "प्रमुख सेवा",
    features_subtitle: "सुलभ डिजिटल सेवा आणि तत्पर प्रशासनाद्वारे ग्रामीण भागाचे सक्षमीकरण.",

    // General terms
    status: "स्थिती",
    priority: "प्राधान्य",
    department: "विभाग",
    category: "प्रवर्ग",
    action: "कृती",
    date: "तारीख",
    details: "तपशील",
    search_placeholder: "ग्राम साधने किंवा सेवा शोधा...",
    all: "सर्व",
    close: "बंद करा",
    save: "बदल जतन करा",
    submit: "सादर करा",
    cancel: "रद्द करा",

    // Grievance Statuses
    status_submitted: "नोंदवली",
    status_verified: "पडताळणी झाली",
    status_assigned: "विभागाकडे वर्ग",
    status_in_progress: "प्रगतीपथावर",
    status_resolved: "निवारण झाले",
    status_rejected: "नाकारली",

    // Grievance Priorities
    priority_emergency: "तातडीची",
    priority_high: "उच्च",
    priority_medium: "मध्यम",
    priority_low: "साधारण"
  },

  hi: {
    // Navigation
    nav_home: "मुख्य पृष्ठ",
    nav_resources: "ग्राम संसाधन",
    nav_grievance: "शिकायत दर्ज करें",
    nav_track: "शिकायत स्थिति",
    nav_dashboard: "डैशबोर्ड",
    nav_admin: "प्रशासक पोर्टल",
    nav_login: "लॉगिन",
    nav_register: "पंजीकरण",
    nav_logout: "लॉगआउट",

    // Hero & Home
    hero_pill: "डिजिटल ग्राम शासन मंच",
    hero_title: "ग्राम संसाधन एवं जन शिकायत प्रबंधन प्रणाली",
    hero_subtitle: "ग्रामीणों को आवश्यक नागरिक सुविधाओं से जोड़ना और शिकायतों का त्वरित एवं पारदर्शी निवारण।",
    btn_explore_resources: "संसाधन देखें",
    btn_report_grievance: "शिकायत दर्ज करें",
    features_title: "प्रमुख जन सुविधाएं",
    features_subtitle: "सुलभ डिजिटल सेवाओं और त्वरित प्रशासन के माध्यम से ग्रामीण सशक्तिकरण।",

    // General terms
    status: "स्थिति",
    priority: "प्राथमिकता",
    department: "विभाग",
    category: "श्रेणी",
    action: "कार्रवाई",
    date: "दिनांक",
    details: "विवरण",
    search_placeholder: "ग्राम संसाधन या सेवाएं खोजें...",
    all: "सभी",
    close: "बंद करें",
    save: "सुरक्षित करें",
    submit: "जमा करें",
    cancel: "रद्द करें",

    // Grievance Statuses
    status_submitted: "दर्ज की गई",
    status_verified: "सत्यापित",
    status_assigned: "विभाग आवंटित",
    status_in_progress: "प्रगति पर",
    status_resolved: "समाधानित",
    status_rejected: "खारिज",

    // Grievance Priorities
    priority_emergency: "आपातकालीन",
    priority_high: "उच्च",
    priority_medium: "मध्यम",
    priority_low: "सामान्य"
  }
};

let currentLanguage = localStorage.getItem("village_lang") || "en";

function setLanguage(lang) {
  if (!TRANSLATIONS[lang]) lang = "en";
  currentLanguage = lang;
  localStorage.setItem("village_lang", lang);

  // Update dropdown value if present
  const select = document.getElementById("lang-select");
  if (select) select.value = lang;

  // Apply translations to all DOM elements with data-i18n attribute
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) {
      if (el.tagName === "INPUT" && el.getAttribute("placeholder")) {
        el.setAttribute("placeholder", TRANSLATIONS[lang][key]);
      } else {
        el.textContent = TRANSLATIONS[lang][key];
      }
    }
  });
}

// =========================================================================
// 2. TOAST NOTIFICATIONS
// =========================================================================

function showToast(message, type = "info", duration = 4000) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div style="flex:1;">${escapeHtml(message)}</div>
    <button style="background:none;border:none;cursor:pointer;font-size:1.1rem;color:#94a3b8;" onclick="this.parentElement.remove()">&times;</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }
  }, duration);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// =========================================================================
// 3. AUTHENTICATION & SESSION MANAGEMENT
// =========================================================================

window.currentUser = null;

async function checkSession() {
  try {
    const res = await fetch("/api/session", { credentials: "same-origin" });
    const data = await res.json();
    if (data.authenticated && data.user) {
      window.currentUser = data.user;
      renderNavbarUser(data.user);
    } else {
      window.currentUser = null;
      renderNavbarGuest();
    }
  } catch (err) {
    console.error("Session check failed:", err);
    renderNavbarGuest();
  }
}

function renderNavbarUser(user) {
  const actionsEl = document.getElementById("nav-auth-actions");
  if (!actionsEl) return;

  const roleClass = user.role === "admin" ? "role-admin" : "role-villager";
  const portalLink = user.role === "admin" ? "admin.html" : "dashboard.html";
  const portalText = user.role === "admin" ? "Admin Portal" : "Dashboard";

  actionsEl.innerHTML = `
    <a href="${portalLink}" class="btn btn-sm btn-outline-primary">${portalText}</a>
    <div class="user-menu">
      <span>${escapeHtml(user.full_name)}</span>
      <span class="user-role-badge ${roleClass}">${user.role}</span>
    </div>
    <button class="btn btn-sm btn-outline" onclick="handleLogout()">Logout</button>
  `;
}

function renderNavbarGuest() {
  const actionsEl = document.getElementById("nav-auth-actions");
  if (!actionsEl) return;

  actionsEl.innerHTML = `
    <a href="login.html" class="btn btn-sm btn-outline-primary" data-i18n="nav_login">Login</a>
    <a href="register.html" class="btn btn-sm btn-primary" data-i18n="nav_register">Register</a>
  `;
  setLanguage(currentLanguage);
}

async function handleLogout() {
  try {
    await fetch("/api/logout", { method: "POST", credentials: "same-origin" });
    showToast("Logged out successfully", "success");
    setTimeout(() => {
      window.location.href = "login.html";
    }, 500);
  } catch (err) {
    showToast("Logout failed", "error");
  }
}

function requireAuth(allowedRole = null) {
  if (!window.currentUser) {
    showToast("Please log in to access this page.", "warning");
    setTimeout(() => {
      window.location.href = "login.html";
    }, 600);
    return false;
  }
  if (allowedRole && window.currentUser.role !== allowedRole) {
    showToast("Unauthorized access: Administrative privileges required.", "error");
    setTimeout(() => {
      window.location.href = window.currentUser.role === "admin" ? "admin.html" : "dashboard.html";
    }, 600);
    return false;
  }
  return true;
}

// =========================================================================
// 4. COMMON UI UTILITIES (Badges, Formats)
// =========================================================================

function getStatusBadge(status) {
  const statusClasses = {
    "Submitted": "badge-submitted",
    "Verified": "badge-verified",
    "Assigned": "badge-assigned",
    "In Progress": "badge-inprogress",
    "Resolved": "badge-resolved",
    "Rejected": "badge-rejected"
  };
  const cls = statusClasses[status] || "badge-submitted";
  return `<span class="badge ${cls}">${escapeHtml(status)}</span>`;
}

function getPriorityBadge(priority) {
  const priorityClasses = {
    "Emergency": "priority-emergency",
    "High": "priority-high",
    "Medium": "priority-medium",
    "Low": "priority-low"
  };
  const cls = priorityClasses[priority] || "priority-medium";
  return `<span class="badge ${cls}">${escapeHtml(priority)}</span>`;
}

function formatDate(dateStr) {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr.replace(" ", "T"));
    return d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  } catch (e) {
    return dateStr;
  }
}

// Initialize common page features upon DOM load
document.addEventListener("DOMContentLoaded", () => {
  // Setup language selector
  const langSelect = document.getElementById("lang-select");
  if (langSelect) {
    langSelect.value = currentLanguage;
    langSelect.addEventListener("change", (e) => {
      setLanguage(e.target.value);
    });
  }
  setLanguage(currentLanguage);

  // Setup mobile nav toggle
  const navToggle = document.getElementById("nav-toggle");
  const navLinks = document.getElementById("nav-links");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      navLinks.classList.toggle("open");
    });
  }

  // Check auth session
  checkSession();
});
