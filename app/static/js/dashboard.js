/* ============================================================
   AttendanceMS — REAL-TIME Dashboard JS (FINAL CLEAN VERSION)
   Chart.js + Live polling + Search + Controls + UI sync
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {
  initAttendanceChart();
  initSearch();
  initNotificationToggle();
  initNavDate();
  initLiveUpdates();
  initRangeToggle();
  initDateFilter();
  initExportButtons();
});

let attendanceChart = null;
let currentMode = "week";
let pollInterval = null;
let currentFrom = null;
let currentTo = null;


/* ================= CHART INIT ================= */

function initAttendanceChart() {
  const canvas = document.getElementById("attendanceChart");
  if (!canvas || typeof Chart === "undefined") return;

  const initial = window.ATTENDANCE_CHART_DATA || {
    labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    values: [70, 80, 65, 90, 85, 60, 75],
  };

  const ctx = canvas.getContext("2d");

  const gradient = ctx.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, "rgba(79, 141, 255, 0.35)");
  gradient.addColorStop(1, "rgba(79, 141, 255, 0)");

  attendanceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: initial.labels,
      datasets: [{
        data: initial.values,
        borderColor: "#4f8dff",
        borderWidth: 2.5,
        tension: 0.4,
        fill: true,
        backgroundColor: gradient,
        pointRadius: 4,
        pointBackgroundColor: "#fff",
        pointBorderColor: "#4f8dff"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          grid: { display: false }
        },
        y: {
          min: 0,
          max: 100,
          ticks: {
            callback: v => v + "%"
          }
        }
      }
    }
  });
}


/* ================= REAL-TIME LIVE UPDATES ================= */

function initLiveUpdates() {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(() => {
    fetchDashboardData();
  }, 10000);
}


/* ================= FETCH HELPER ================= */

function fetchDashboardData() {
  let url = `/dashboard/data?mode=${currentMode}`;
  if (currentFrom && currentTo) {
    url += `&from=${currentFrom}&to=${currentTo}`;
  }

  fetch(url)
    .then(res => res.json())
    .then(data => {
      if (!data || !attendanceChart) return;
      attendanceChart.data.labels = data.chart.labels;
      attendanceChart.data.datasets[0].data = data.chart.values;
      attendanceChart.update();
      updateCounters(data);
    })
    .catch(err => console.log("Live update error:", err));
}


/* ================= RANGE SWITCH (DAY/WEEK/MONTH) ================= */

function initRangeToggle() {
  const buttons = document.querySelectorAll(".toggle-btn");
  if (!buttons.length) return;

  buttons.forEach(btn => {
    btn.addEventListener("click", function () {
      buttons.forEach(b => b.classList.remove("active"));
      this.classList.add("active");
      currentMode = this.dataset.range || "week";
      fetchDashboardData();
    });
  });
}


/* ================= DATE FILTER ================= */

function initDateFilter() {
  const fromInput = document.getElementById("fromDate");
  const toInput = document.getElementById("toDate");

  if (!fromInput || !toInput) return;

  function applyFilter() {
    const from = fromInput.value;
    const to = toInput.value;

    if (from && to) {
      currentFrom = from;
      currentTo = to;
      fetchDashboardData();
    }
  }

  fromInput.addEventListener("change", applyFilter);
  toInput.addEventListener("change", applyFilter);
}


/* ================= EXPORT BUTTONS (FIXED) ================= */

function initExportButtons() {
  // Use data attributes instead of relying on generic CSS classes.
  // In your HTML, add data-action="export-pdf" to the export button
  // and data-action="download-pdf" to the download button.
  // This prevents any accidental matching of form submit buttons.

  const exportBtn  = document.querySelector('[data-action="export-pdf"]');
  const downloadBtn = document.querySelector('[data-action="download-pdf"]');

  if (exportBtn) {
    exportBtn.addEventListener("click", (e) => {
      e.preventDefault();
      window.open("/dashboard/export-pdf", "_blank");
    });
  }

  if (downloadBtn) {
    downloadBtn.addEventListener("click", (e) => {
      e.preventDefault();
      const a = document.createElement("a");
      a.href = "/dashboard/export-pdf";
      a.download = "attendance_report.pdf";
      a.click();
    });
  }
}


/* ================= COUNTERS ================= */

function updateCounters(data) {
  const totalEl   = document.getElementById("totalRecords");
  const presentEl = document.getElementById("presentCount");
  const absentEl  = document.getElementById("absentCount");

  if (totalEl)   totalEl.textContent   = data.total   ?? 0;
  if (presentEl) presentEl.textContent = data.present ?? 0;
  if (absentEl)  absentEl.textContent  = data.absent  ?? 0;
}


/* ================= SEARCH ================= */

function initSearch() {
  const form    = document.querySelector(".search-form");
  const input   = document.getElementById("searchInput");
  const results = document.getElementById("searchResults");

  if (!form || !input || !results) return;

  let debounce   = null;
  let controller = null;

  input.addEventListener("input", () => {
    clearTimeout(debounce);
    const q = input.value.trim();
    if (!q) return close();
    debounce = setTimeout(() => run(q), 250);
  });

  function run(query) {
    if (controller) controller.abort();
    controller = new AbortController();

    fetch(`/search?query=${encodeURIComponent(query)}`, {
      signal: controller.signal
    })
      .then(res => res.json())
      .then(data => render(data.results || []))
      .catch(() => render([]));
  }

  function render(items) {
    results.innerHTML = "";

    if (!items.length) {
      results.innerHTML = `<div class="search-empty">No results</div>`;
    } else {
      items.forEach(i => {
        const a       = document.createElement("a");
        a.href        = i.href || "#";
        a.className   = "search-item";
        a.textContent = i.label;
        results.appendChild(a);
      });
    }

    results.classList.add("open");
  }

  function close() {
    results.classList.remove("open");
    results.innerHTML = "";
  }
}


/* ================= NOTIFICATION ================= */

function initNotificationToggle() {
  const bell = document.querySelector(".notification-wrapper");
  if (!bell) return;

  bell.addEventListener("click", () => {
    document.querySelector(".activity-section")
      ?.scrollIntoView({ behavior: "smooth" });
  });
}


/* ================= NAV DATE ================= */

function initNavDate() {
  const nav = document.querySelector(".nav-right");
  if (!nav) return;

  if (document.getElementById("navDate")) return;

  const el      = document.createElement("span");
  el.id         = "navDate";
  el.className  = "nav-date";
  el.textContent = new Date().toDateString();

  nav.prepend(el);
}


/* ================= NOTIFICATION PANEL ================= */

function toggleNotifPanel() {
  const panel = document.getElementById("notif-panel");
  if (!panel) return;

  const isOpen = panel.style.display === "block";
  panel.style.display = isOpen ? "none" : "block";

  if (!isOpen) refreshNotifPanel();
}

function refreshNotifPanel() {
  fetch("/dashboard/live-notifications")
    .then(res => res.json())
    .then(data => {
      const list        = document.getElementById("notif-list");
      const navCount    = document.getElementById("nav-notif-count");
      const sidebarCount = document.getElementById("sidebar-notif-count");
      const urgentBadge = document.getElementById("notif-urgent-badge");

      if (!list) return;

      if (!data.alerts || !data.alerts.length) {
        list.innerHTML = `<div style="padding:1rem; color:#4a6a8a; text-align:center;">No notifications</div>`;
        return;
      }

      list.innerHTML = data.alerts.map(a => `
        <div style="padding:0.75rem 1.25rem; border-bottom:1px solid #1e3a5f;
                    display:flex; flex-direction:column; gap:0.2rem;">
          <span style="color:#cde; font-size:0.9rem;">${a.text}</span>
          <span style="color:#4a6a8a; font-size:0.75rem;">${a.time_ago}</span>
        </div>
      `).join("");

      const urgent = data.counts?.urgent ?? data.counts?.total ?? 0;
      if (navCount)    navCount.textContent    = urgent;
      if (urgentBadge) urgentBadge.textContent = `${urgent} urgent`;
      if (sidebarCount) {
        sidebarCount.textContent   = urgent;
        sidebarCount.style.display = urgent > 0 ? "inline-flex" : "none";
      }
    })
    .catch(err => console.error("Notif panel error:", err));
}


/* ================= NOTIFICATION COUNT POLLER ================= */

function startNotifCountPoller() {
  const bell = document.getElementById('nav-notif-count');
  if (!bell) return;

  async function fetchCount() {
    try {
      const res   = await fetch('/dashboard/alerts-data');
      const data  = await res.json();
      const count = data.counts?.urgent ?? data.counts?.total ?? 0;

      bell.textContent = count;

      const sidebar = document.getElementById('sidebar-notif-count');
      if (sidebar) {
        sidebar.textContent   = count;
        sidebar.style.display = count > 0 ? 'inline-flex' : 'none';
      }

      const urgentBadge = document.getElementById('notif-urgent-badge');
      if (urgentBadge) urgentBadge.textContent = `${count} urgent`;

    } catch (e) {
      // silent fail — non-critical
    }
  }

  fetchCount();
  setInterval(fetchCount, 30000);
}

document.addEventListener('DOMContentLoaded', startNotifCountPoller);