/* =======================================================================
   script.js  —  Student Attendance Demo App (Frontend Only)
   -----------------------------------------------------------------------
   WHAT THIS FILE DOES
   - Simple local “auth” (email+password) stored in localStorage (DEMO!)
   - Session with idle-timeout (auto-logout after 20 minutes of inactivity)
   - Students CRUD (Add / Delete)
   - Attendance marking (checkboxes across a 30-day grid)
   - Dashboard stats + charts (Chart.js)
   - Settings helpers (delete account, clear data, export/import, etc.)
   - Lots of inline comments and spacing so your friends can understand 🙂

   ⚠️ IMPORTANT: This is a demo without a backend. Do NOT use this exact
   auth/storage approach in production. Replace with a real server + JWT/session.
   ======================================================================= */



/* =============================================================================
   0) GLOBAL CONSTANTS & KEYS
   ========================================================================== */

const STORAGE_KEYS = {
  users:       "users",         // [{ email, password, createdAt }]
  session:     "sessionUser",   // { email, createdAt, expiresAt }
  students:    "students",      // array of student objects
  attendance:  "attendance"     // nested keyed attendance
};

const IDLE_TIMEOUT_MINUTES = 20;            // auto-logout after N minutes of inactivity
const IDLE_TIMEOUT_MS      = IDLE_TIMEOUT_MINUTES * 60 * 1000;



/* =============================================================================
   1) USER STORE HELPERS (DEMO ONLY)
   ---------------------------------------------------------------------------
   These wrap localStorage. In a real app, swap for API calls to a backend.
   ========================================================================== */

function getUsers() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEYS.users)) || []; }
  catch { return []; }
}

function saveUsers(users) {
  localStorage.setItem(STORAGE_KEYS.users, JSON.stringify(users));
}

function registerUser(email, password) {
  const users = getUsers();

  // Prevent duplicates (case-insensitive match)
  if (users.some(u => u.email.toLowerCase() === email.toLowerCase())) {
    return { ok: false, message: "Account already exists. Please login." };
  }

  users.push({
    email,
    password,
    createdAt: Date.now()
  });

  saveUsers(users);
  return { ok: true };
}

function loginUser(email, password) {
  const users = getUsers();
  const user  = users.find(u => u.email.toLowerCase() === email.toLowerCase());

  if (!user)                   return { ok: false, message: "Account not found. Please create one." };
  if (user.password !== password) return { ok: false, message: "Wrong password. Try again." };

  return { ok: true, user };
}

function deleteUserByEmail(email) {
  const users = getUsers();
  const next  = users.filter(u => u.email.toLowerCase() !== email.toLowerCase());
  saveUsers(next);
}



/* =============================================================================
   2) SESSION HELPERS (IDLE TIMEOUT)
   ---------------------------------------------------------------------------
   - Store a session with an "expiresAt".
   - Extend whenever the user interacts with the page.
   - If expired, redirect to index.html.
   ========================================================================== */

function setSession(email /* remember flag kept for future */, remember = false) {
  const now = Date.now();

  const sessionData = {
    email,
    createdAt: now,
    expiresAt: now + IDLE_TIMEOUT_MS
  };

  localStorage.setItem(STORAGE_KEYS.session, JSON.stringify(sessionData));

  // Note: "remember" could be used to persist a refresh token, etc., in real apps.
}

function getRawSession() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEYS.session)); }
  catch { return null; }
}

function getSessionUser() {
  const s = getRawSession();
  if (!s) return null;

  // If session expired, clear and return null
  if (Date.now() > s.expiresAt) {
    clearSession();
    return null;
  }

  return s.email;
}

function extendSession() {
  const s = getRawSession();
  if (!s) return;

  s.expiresAt = Date.now() + IDLE_TIMEOUT_MS;
  localStorage.setItem(STORAGE_KEYS.session, JSON.stringify(s));
}

function clearSession() {
  localStorage.removeItem(STORAGE_KEYS.session);
}

function requireAuthOrRedirect() {
  if (!getSessionUser()) {
    // No valid session — send to login page
    window.location.replace("index.html");
  }
}



/* =============================================================================
   3) GLOBAL TOAST (ONE REUSABLE LITTLE NOTIFICATION)
   ========================================================================== */

function showToastEl(el, message, bg) {
  if (!el) return;

  el.textContent = message;

  if (bg) el.style.background = bg;

  el.classList.add("show");
  el.classList.remove("hidden");

  clearTimeout(el._t);
  el._t = setTimeout(() => {
    el.classList.remove("show");
    el.classList.add("hidden");
    if (bg) el.style.background = "";
  }, 2500);
}



/* =============================================================================
   4) LOGIN PAGE LOGIC
   ---------------------------------------------------------------------------
   HTML elements expected on index.html:
   - #loginForm, #email, #password, #rememberMe, #togglePassword
   - #registerModal, #openRegister, #closeRegister, #registerForm
   - #regEmail, #regPassword, #regPassword2, #toggleRegPassword, #toggleRegPassword2
   - #forgotPassword
   - #loginToast
   ========================================================================== */

function initLoginPage() {

  // This JS runs on both pages. Only proceed if the body marks this page as "login".
  if (document.body.dataset.page !== "login") return;

  // If a valid session exists, skip login and move to dashboard.
  if (getSessionUser()) {
    window.location.replace("dashboard.html");
    return;
  }

  const loginForm      = document.getElementById("loginForm");
  const emailInput     = document.getElementById("email");
  const passInput      = document.getElementById("password");
  const rememberInput  = document.getElementById("rememberMe");
  const togglePassword = document.getElementById("togglePassword");
  const loginToast     = document.getElementById("loginToast");

  const regModal           = document.getElementById("registerModal");
  const openRegister       = document.getElementById("openRegister");
  const closeRegister      = document.getElementById("closeRegister");
  const registerForm       = document.getElementById("registerForm");
  const regEmail           = document.getElementById("regEmail");
  const regPassword        = document.getElementById("regPassword");
  const regPassword2       = document.getElementById("regPassword2");
  const toggleRegPassword  = document.getElementById("toggleRegPassword");
  const toggleRegPassword2 = document.getElementById("toggleRegPassword2");
  const forgotPassword     = document.getElementById("forgotPassword");



  /* ---------- Reset inputs each fresh visit (browser autofill may still appear) ---------- */
  if (emailInput)    emailInput.value = "";
  if (passInput)     passInput.value  = "";
  if (rememberInput) rememberInput.checked = false;



  /* ---------- Eye toggles for password fields ---------- */
  const toggleEye = (input, el) => {
    if (!input || !el) return;
    el.addEventListener("click", () => {
      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      el.textContent = isHidden ? "🙈" : "👁️";
    });
  };

  toggleEye(passInput,     togglePassword);
  toggleEye(regPassword,   toggleRegPassword);
  toggleEye(regPassword2,  toggleRegPassword2);



  /* ---------- “Forgot password” demo ---------- */
  if (forgotPassword) {
    forgotPassword.addEventListener("click", (e) => {
      e.preventDefault();
      showToastEl(loginToast, "Demo only: password reset is not implemented.", "#f59e0b");
    });
  }



  /* ---------- Open/close Register modal ---------- */
  openRegister?.addEventListener("click", (e) => {
    e.preventDefault();
    regModal?.classList.remove("hidden");
  });

  closeRegister?.addEventListener("click", () => {
    regModal?.classList.add("hidden");
  });

  regModal?.addEventListener("click", (e) => {
    // click outside content closes the modal
    if (e.target === regModal) regModal.classList.add("hidden");
  });



  /* ---------- Register submit ---------- */
  registerForm?.addEventListener("submit", (e) => {
    e.preventDefault();

    const email = (regEmail?.value || "").trim();
    const pw1   = regPassword?.value || "";
    const pw2   = regPassword2?.value || "";

    // Super basic validation
    if (!email)          return showToastEl(loginToast, "Email required.", "#ef4444");
    if (pw1.length < 6)  return showToastEl(loginToast, "Password must be at least 6 characters.", "#ef4444");
    if (pw1 !== pw2)     return showToastEl(loginToast, "Passwords do not match.", "#ef4444");

    const res = registerUser(email, pw1);
    if (!res.ok) return showToastEl(loginToast, res.message, "#ef4444");

    showToastEl(loginToast, "Account created! You can login now.", "#10b981");

    // Clean the form and close
    registerForm.reset();
    regModal?.classList.add("hidden");
  });



  /* ---------- Login submit ---------- */
  loginForm?.addEventListener("submit", (e) => {
    e.preventDefault();

    const email    = (emailInput?.value || "").trim();
    const password = passInput?.value || "";

    if (!email || !password) {
      showToastEl(loginToast, "Enter email and password.", "#ef4444");
      return;
    }

    const res = loginUser(email, password);
    if (!res.ok) {
      showToastEl(loginToast, res.message + " — or create one using the “Create” link.", "#ef4444");
      return;
    }

    // Create a fresh session (20 minutes inactivity window)
    setSession(res.user.email, !!(rememberInput && rememberInput.checked));

    showToastEl(loginToast, "Login successful! Redirecting...", "#10b981");

    // Tiny delay so the toast is visible
    setTimeout(() => {
      window.location.replace("dashboard.html");
    }, 400);
  });
}



/* =============================================================================
   5) DASHBOARD PAGE LOGIC
   ---------------------------------------------------------------------------
   This controls the sidebar navigation, students table, attendance grid, and
   charts. Requires a valid session or we redirect back to index.html.
   ========================================================================== */

function initDashboardPage() {

  if (document.body.dataset.page !== "dashboard") return;

  // Protect the page. If session missing/expired, we will be redirected.
  requireAuthOrRedirect();



  /* ---------- Sidebar toggles & responsive behavior ---------- */

  const sidebar            = document.getElementById("sidebar");
  const sidebarToggleArrow = document.getElementById("sidebarToggleArrow");

  // Expose a global function (used by the header menu button)
  window.toggleSidebar = function toggleSidebar() {
    const isShown = sidebar.classList.contains("show");

    if (window.innerWidth <= 768) {
      // Mobile behavior slides the sidebar in/out, and shifts main-content margin
      if (isShown) {
        sidebar.classList.remove("show");
        sidebarToggleArrow.textContent = "▶";
        document.querySelector(".main-content").style.marginLeft = "0";
      } else {
        sidebar.classList.add("show");
        sidebarToggleArrow.textContent = "◀";
        document.querySelector(".main-content").style.marginLeft = "220px";
      }
    } else {
      // On desktop we “hide” by translating off-screen via a CSS class
      sidebar.classList.toggle("hidden");
      document.querySelector(".main-content").style.marginLeft =
        sidebar.classList.contains("hidden") ? "0" : "220px";
    }
  };

  function initializeSidebarToggleArrow() {
    if (window.innerWidth <= 768) {
      // On small screens, start sidebar hidden and show the floating arrow
      sidebar.classList.remove("hidden");
      sidebar.classList.remove("show");
      sidebarToggleArrow.textContent = "▶";
      document.querySelector(".main-content").style.marginLeft = "0";
      sidebarToggleArrow.style.display = "block";
    } else {
      // On larger screens, show sidebar by default and hide arrow
      sidebarToggleArrow.style.display = "none";
      sidebar.classList.remove("show");
      sidebar.classList.remove("hidden");
      document.querySelector(".main-content").style.marginLeft = "220px";
    }
  }

  sidebarToggleArrow?.addEventListener("click", toggleSidebar);
  window.addEventListener("resize", initializeSidebarToggleArrow);
  window.addEventListener("load",  initializeSidebarToggleArrow);
  initializeSidebarToggleArrow();



  /* ---------- Local data store (students & attendance) ---------- */

  let students   = [];   // [{ id, name, roll, studentClass, section, mobile }]
  let attendance = {};   // { [studentId]: { "YYYY-MM": { [dayNumber]: true/false } } }

  function saveData() {
    localStorage.setItem(STORAGE_KEYS.students,   JSON.stringify(students));
    localStorage.setItem(STORAGE_KEYS.attendance, JSON.stringify(attendance));
  }

  function loadData() {
    const s = localStorage.getItem(STORAGE_KEYS.students);
    const a = localStorage.getItem(STORAGE_KEYS.attendance);
    students   = s ? JSON.parse(s) : [];
    attendance = a ? JSON.parse(a) : {};
  }



  /* ---------- Grab DOM references ---------- */

  const studentTable     = document.getElementById("studentTable");
  const attendanceTable  = document.getElementById("attendanceTable");
  const attendanceHeader = document.getElementById("attendanceHeader");

  const viewSelect    = document.getElementById("viewSelect");
  const classSelector = document.getElementById("classSelector");

  const monthSelectEl  = document.getElementById("monthSelect");
  const yearSelectEl   = document.getElementById("yearSelect");
  const classFilterEl  = document.getElementById("classFilter");

  const toast = document.getElementById("toast");



  /* =============================================================================
     5A) Attendance header (Day 1..30)
     --------------------------------------------------------------------------
     For simplicity, we use a fixed 30-day grid. You can change this to the real
     number of days for the selected month if you prefer.
     ======================================================================== */

  function updateAttendanceHeader() {
    attendanceHeader.innerHTML =
      "<th class='p-2 border'>ID</th><th class='p-2 border'>Name</th>";

    for (let i = 1; i <= 30; i++) {
      attendanceHeader.innerHTML += `<th class="p-2 border">${i}</th>`;
    }
  }



  /* =============================================================================
     5B) Render attendance rows (checkbox grid)
     ======================================================================== */

  function renderAttendance() {
    const month = monthSelectEl.value;
    const year  = yearSelectEl.value;

    const classFilterSelection = classFilterEl.value;

    attendanceTable.innerHTML = students
      .filter(s => classFilterSelection === "all" || s.studentClass === classFilterSelection)
      .map(s => {
        const key = `${year}-${month}`;
        let days  = "";

        for (let i = 1; i <= 30; i++) {
          const checked = attendance[s.id] && attendance[s.id][key] && attendance[s.id][key][i]
            ? "checked"
            : "";
          days += `
            <td class="border p-2 text-center">
              <input type="checkbox" data-student="${s.id}" data-day="${i}" ${checked} />
            </td>`;
        }

        return `
          <tr>
            <td class="border p-2">${s.id}</td>
            <td class="border p-2">${s.name}</td>
            ${days}
          </tr>
        `;
      })
      .join("");
  }



  /* =============================================================================
     5C) Students table rendering + delete
     ======================================================================== */

  function renderStudents() {
    studentTable.innerHTML = students.map(s => `
      <tr>
        <td class="border p-2">${s.roll}</td>
        <td class="border p-2">${s.name}</td>
        <td class="border p-2">${s.studentClass}</td>
        <td class="border p-2">${s.section}</td>
        <td class="border p-2">${s.mobile}</td>
        <td class="border p-2 text-center">
          <button
            class="bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded"
            onclick="deleteStudent(${s.id})"
            title="Delete ${s.name}"
          >🗑</button>
        </td>
      </tr>
    `).join("");

    // Update dashboard card count
    const totalStudentsCard = document.getElementById("totalStudentsCard");
    if (totalStudentsCard) totalStudentsCard.textContent = students.length;
  }

  // Expose delete function globally (used by inline onclick on rows)
  window.deleteStudent = function deleteStudent(id) {
    const student = students.find(s => s.id === id);

    students = students.filter(s => s.id !== id);
    delete attendance[id];

    saveData();
    renderStudents();
    renderAttendance();
    populateDashboardClassSelector();
    updateStats();

    showToastEl(toast, `Student ${student?.name || ""} deleted`, "#ef4444");
  };



  /* =============================================================================
     5D) Add student (modal form)
     ======================================================================== */

  const studentForm = document.getElementById("studentForm");

  studentForm?.addEventListener("submit", function (e) {
    e.preventDefault();

    const student = {
      id:           Date.now(),  // quick unique-ish id
      name:         (document.getElementById("name")?.value || "").trim(),
      roll:         (document.getElementById("roll")?.value || "").trim(),
      studentClass: (document.getElementById("class")?.value || "").trim(),
      section:      (document.getElementById("section")?.value || "").trim(),
      mobile:       (document.getElementById("mobile")?.value || "").trim(),
    };

    // Simple validation (you can extend)
    if (!student.name || !student.roll || !student.studentClass || !student.section || !student.mobile) {
      showToastEl(toast, "Fill all fields to add a student.", "#ef4444");
      return;
    }

    students.push(student);

    saveData();
    renderStudents();
    renderAttendance();
    populateDashboardClassSelector();

    this.reset();
    closeStudentModal();

    updateStats();

    showToastEl(toast, `Student ${student.name} added`, "#10b981");
  });



  /* =============================================================================
     5E) Attendance checkbox change handler
     ======================================================================== */

  const attendanceSection = document.getElementById("attendanceSection");

  attendanceSection?.addEventListener("change", e => {
    if (e.target.type !== "checkbox") return;

    const studentId = e.target.dataset.student;
    const day       = e.target.dataset.day;
    const key       = `${yearSelectEl.value}-${monthSelectEl.value}`;

    if (!attendance[studentId])      attendance[studentId]      = {};
    if (!attendance[studentId][key]) attendance[studentId][key] = {};

    attendance[studentId][key][day] = e.target.checked;

    saveData();
    updateStats();

    showToastEl(toast, `ID ${studentId} marked ${e.target.checked ? "Present" : "Absent"} (Day ${day})`);
  });



  /* =============================================================================
     5F) Charts (Chart.js)
     ======================================================================== */

  let barChart, doughnutChart;

  function renderCharts(presentData, absentData, days) {
    const labels = Array.from({ length: days }, (_, i) => i + 1);

    if (barChart)      barChart.destroy();
    if (doughnutChart) doughnutChart.destroy();

    // --- Bar Chart: Present / Absent per day within selected range ---
    barChart = new Chart(document.getElementById("barChart"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Present", data: presentData.slice(0, days), backgroundColor: "#3b82f6" },
          { label: "Absent",  data: absentData .slice(0, days), backgroundColor: "#f87171" },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1 } }
        }
      },
    });

    // --- Doughnut Chart: Total Present vs Absent across selected range ---
    doughnutChart = new Chart(document.getElementById("doughnutChart"), {
      type: "doughnut",
      data: {
        labels: ["Present", "Absent"],
        datasets: [{
          data: [
            presentData.reduce((a, b) => a + b, 0),
            absentData .reduce((a, b) => a + b, 0),
          ],
          backgroundColor: ["#3b82f6", "#f87171"],
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } }
      }
    });
  }



  /* =============================================================================
     5G) Stats cards (Percentages) + Chart rendering
     ======================================================================== */

  function updateStats() {
    const key        = `${yearSelectEl.value}-${monthSelectEl.value}`;
    const totalDays  = parseInt(viewSelect.value, 10);
    const selectedClass = classSelector.value;

    // Keep arrays length 30 for the month grid
    const presentData = Array(30).fill(0);
    const absentData  = Array(30).fill(0);

    // Aggregate across students
    students.forEach(s => {
      if (selectedClass !== "all" && s.studentClass !== selectedClass) return;

      for (let i = 1; i <= 30; i++) {
        const isPresent = attendance[s.id]?.[key]?.[i] ?? false;
        if (isPresent) presentData[i - 1]++; else absentData[i - 1]++;
      }
    });

    // Totals across selected range
    const presentClipped = presentData.slice(0, totalDays);
    const absentClipped  = absentData .slice(0, totalDays);

    const totalChecks  = presentClipped.reduce((a, b) => a + b, 0) + absentClipped.reduce((a, b) => a + b, 0);
    const totalPresent = presentClipped.reduce((a, b) => a + b, 0);
    const totalAbsent  = absentClipped .reduce((a, b) => a + b, 0);

    const percentPresent = totalChecks ? ((totalPresent / totalChecks) * 100).toFixed(1) : 0;
    const percentAbsent  = totalChecks ? ((totalAbsent  / totalChecks) * 100).toFixed(1) : 0;

    // Update UI cards
    const presentPercentEl = document.getElementById("presentPercent");
    const absentPercentEl  = document.getElementById("absentPercent");

    if (presentPercentEl) presentPercentEl.textContent = percentPresent + "%";
    if (absentPercentEl)  absentPercentEl .textContent = percentAbsent  + "%";

    // (Re)draw charts
    renderCharts(presentData, absentData, totalDays);
  }



  /* =============================================================================
     5H) Populate class filters (both dashboard & attendance sections)
     ======================================================================== */

  function populateDashboardClassSelector() {
    classSelector.innerHTML = `<option value="all">All Classes</option>`;

    // Unique class names from students list
    [...new Set(students.map(s => s.studentClass))].forEach(c => {
      if (!c) return;
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      classSelector.appendChild(opt);
    });
  }

  function updateClassFilter() {
    classFilterEl.innerHTML = `<option value="all">All Classes</option>`;

    [...new Set(students.map(s => s.studentClass))].forEach(c => {
      if (!c) return;
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      classFilterEl.appendChild(opt);
    });
  }



  /* =============================================================================
     5I) Populate Month/Year selects
     ======================================================================== */

  function populateFilters() {
    const months = [ "01","02","03","04","05","06","07","08","09","10","11","12" ];

    // Month
    monthSelectEl.innerHTML = "";
    months.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = m;
      monthSelectEl.appendChild(opt);
    });
    monthSelectEl.value = new Date().toISOString().slice(5, 7); // current month (MM)

    // Year (current year down to -5 years)
    const currentYear = new Date().getFullYear();
    yearSelectEl.innerHTML = "";
    for (let y = currentYear; y >= currentYear - 5; y--) {
      const opt = document.createElement("option");
      opt.value = y;
      opt.textContent = y;
      yearSelectEl.appendChild(opt);
    }
    yearSelectEl.value = currentYear;

    // Make sure class filter dropdown is in sync with students
    updateClassFilter();
  }



  /* =============================================================================
     5J) Quick search on students table
     ======================================================================== */

  const searchInput = document.getElementById("searchInput");

  searchInput?.addEventListener("input", function () {
    const val = this.value.toLowerCase();

    document.querySelectorAll("#studentTable tr").forEach(row => {
      row.style.display = row.textContent.toLowerCase().includes(val) ? "" : "none";
    });
  });



  /* =============================================================================
     5K) Page navigation (Sidebar)
     ======================================================================== */

  const pages = {
    dashboard:  document.getElementById("dashboardSection"),
    students:   document.getElementById("studentsSection"),
    attendance: document.getElementById("attendanceSection"),
    settings:   document.getElementById("settingsSection"),
  };

  function showPage(page) {
    Object.values(pages).forEach(sec => sec?.classList.add("hidden"));

    if (pages[page]) {
      pages[page].classList.remove("hidden");
      const pageTitle = document.getElementById("pageTitle");
      if (pageTitle) pageTitle.textContent = page.charAt(0).toUpperCase() + page.slice(1);
    }

    // If entering settings, ensure controls are present
    if (page === "settings") ensureSettingsControls();
  }

  document.querySelectorAll(".sidebar nav ul li").forEach(item => {
    item.addEventListener("click", () => {
      // Activate clicked item
      document.querySelectorAll(".sidebar nav ul li").forEach(li => li.classList.remove("active"));
      item.classList.add("active");

      // Each li has data-page="dashboard|students|attendance|settings"
      showPage(item.dataset.page);
    });
  });



  /* =============================================================================
     5L) Student modal open/close helpers
     ======================================================================== */

  window.openStudentModal = function openStudentModal() {
    document.getElementById("studentModal")?.classList.remove("hidden");
  };

  window.closeStudentModal = function closeStudentModal() {
    document.getElementById("studentModal")?.classList.add("hidden");
  };



  /* =============================================================================
     5M) Listeners that recompute stats / re-render tables
     ======================================================================== */

  viewSelect     ?.addEventListener("change", () => { renderAttendance(); updateStats(); });
  classSelector  ?.addEventListener("change", () => { updateStats(); });
  monthSelectEl  ?.addEventListener("change", () => { renderAttendance(); updateStats(); });
  yearSelectEl   ?.addEventListener("change", () => { renderAttendance(); updateStats(); });
  classFilterEl  ?.addEventListener("change", () => { renderAttendance(); updateStats(); });



  /* =============================================================================
     5N) Initial load (bring everything to life)
     ======================================================================== */

  loadData();                       // restore students & attendance from localStorage
  populateFilters();                // fill Month/Year/Class filters
  renderStudents();                 // show students table
  populateDashboardClassSelector(); // fill dashboard class select
  updateAttendanceHeader();         // render "1..30" header
  renderAttendance();               // draw attendance grid for current filters
  updateStats();                    // update cards + charts
  showPage("dashboard");            // default visible section



  /* =============================================================================
     5O) Handle Chart resize on window resize (Chart.js also does this internally)
     ======================================================================== */

  window.addEventListener("resize", () => {
    barChart     ?.resize();
    doughnutChart?.resize();
  });



  /* =============================================================================
     5P) Session activity heartbeat & auto-logout
     --------------------------------------------------------------------------
     Whenever the user interacts, extend the session so it doesn’t expire while
     they’re working. Also, a small timer checks whether the session expired.
     ======================================================================== */

  const activityEvents = ["click", "keypress", "mousemove", "scroll", "touchstart"];

  activityEvents.forEach(evt => {
    window.addEventListener(evt, () => { extendSession(); }, { passive: true });
  });

  // Every 15 seconds, see if the session has passed expiresAt
  setInterval(() => {
    const s = getRawSession();
    if (!s) return; // already cleared elsewhere

    if (Date.now() > s.expiresAt) {
      showToastEl(toast, "Session expired due to inactivity.", "#ef4444");
      setTimeout(() => { logout(); }, 800);
    }
  }, 15000);



  /* =============================================================================
     5Q) SETTINGS SECTION — Build controls dynamically (so HTML can stay simple)
     --------------------------------------------------------------------------
     The settings page will include:
     - Show current account email
     - Change password (simple local update)
     - Delete my account (and all local data for that account)
     - Clear all students & attendance
     - Export students/attendance to JSON
     - Import students/attendance from JSON
     ======================================================================== */

  function ensureSettingsControls() {
    const settings = pages.settings;
    if (!settings) return;

    // If controls already exist, do nothing
    if (settings.dataset.enhanced === "1") return;

    settings.dataset.enhanced = "1";

    // Clear placeholder text and build UI
    settings.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "grid gap-4";

    // --- Account card ---
    const accountCard = document.createElement("div");
    accountCard.className = "bg-white shadow-md rounded p-4";
    const email = getSessionUser() || "(unknown)";

    accountCard.innerHTML = `
      <h3 class="text-lg font-bold mb-2">Account</h3>
      <p class="text-gray-700 mb-2">Signed in as: <span class="font-mono">${email}</span></p>

      <div class="grid sm:grid-cols-2 gap-3 mt-3">
        <div class="border rounded p-3">
          <h4 class="font-semibold mb-2">Change Password (local demo)</h4>
          <input type="password" id="newPassword" class="w-full border p-2 rounded mb-2" placeholder="New password (min 6 chars)" />
          <button id="changePasswordBtn" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded">Change Password</button>
        </div>

        <div class="border rounded p-3">
          <h4 class="font-semibold mb-2 text-red-600">Danger Zone</h4>
          <button id="deleteAccountBtn" class="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded">Delete My Account</button>
        </div>
      </div>
    `;

    // --- Data tools card ---
    const dataCard = document.createElement("div");
    dataCard.className = "bg-white shadow-md rounded p-4";
    dataCard.innerHTML = `
      <h3 class="text-lg font-bold mb-2">Data Tools</h3>

      <div class="grid sm:grid-cols-2 gap-3">
        <div class="border rounded p-3">
          <h4 class="font-semibold mb-2">Export</h4>
          <button id="exportStudentsBtn"   class="bg-gray-800 hover:bg-black text-white px-3 py-2 rounded mr-2">Export Students JSON</button>
          <button id="exportAttendanceBtn" class="bg-gray-800 hover:bg-black text-white px-3 py-2 rounded">Export Attendance JSON</button>
        </div>

        <div class="border rounded p-3">
          <h4 class="font-semibold mb-2">Import</h4>
          <input type="file" id="importFile" accept="application/json" class="w-full border p-2 rounded mb-2" />
          <button id="importDataBtn" class="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded">Import JSON (students+attendance)</button>
        </div>
      </div>

      <div class="border rounded p-3 mt-3">
        <h4 class="font-semibold mb-2 text-red-600">Danger Zone</h4>
        <button id="clearDataBtn" class="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded">Clear Students & Attendance</button>
      </div>
    `;

    wrapper.appendChild(accountCard);
    wrapper.appendChild(dataCard);
    settings.appendChild(wrapper);

    // Attach handlers

    // 1) Change password
    document.getElementById("changePasswordBtn")?.addEventListener("click", () => {
      const newPassEl = document.getElementById("newPassword");
      const newPass   = (newPassEl?.value || "").trim();

      if (newPass.length < 6) {
        showToastEl(toast, "Password must be at least 6 characters.", "#ef4444");
        return;
      }

      // Update the user in the local "users" store
      const users = getUsers();
      const idx   = users.findIndex(u => u.email.toLowerCase() === email.toLowerCase());
      if (idx === -1) {
        showToastEl(toast, "Account not found (unexpected).", "#ef4444");
        return;
      }

      users[idx].password = newPass;
      saveUsers(users);

      newPassEl.value = "";
      showToastEl(toast, "Password updated.", "#10b981");
    });

    // 2) Delete account
    document.getElementById("deleteAccountBtn")?.addEventListener("click", () => {
      if (!confirm("Delete your account and sign out? This cannot be undone.")) return;

      // Remove the account from local user store
      deleteUserByEmail(email);

      // Also sign out and return to login
      clearSession();

      showToastEl(toast, "Account deleted.", "#ef4444");
      setTimeout(() => { window.location.replace("index.html"); }, 600);
    });

    // 3) Export Students
    document.getElementById("exportStudentsBtn")?.addEventListener("click", () => {
      const blob = new Blob([ JSON.stringify(students, null, 2) ], { type: "application/json" });
      const url  = URL.createObjectURL(blob);
      downloadURL(url, "students.json");
      showToastEl(toast, "Students exported.", "#10b981");
    });

    // 4) Export Attendance
    document.getElementById("exportAttendanceBtn")?.addEventListener("click", () => {
      const blob = new Blob([ JSON.stringify(attendance, null, 2) ], { type: "application/json" });
      const url  = URL.createObjectURL(blob);
      downloadURL(url, "attendance.json");
      showToastEl(toast, "Attendance exported.", "#10b981");
    });

    // 5) Import JSON (students + attendance)
    document.getElementById("importDataBtn")?.addEventListener("click", async () => {
      const fileEl = document.getElementById("importFile");
      const file   = fileEl?.files?.[0];

      if (!file) {
        showToastEl(toast, "Choose a JSON file first.", "#ef4444");
        return;
      }

      try {
        const text = await file.text();
        const data = JSON.parse(text);

        // You can support two formats:
        //  (a) { students: [...], attendance: {...} }
        //  (b) just students array or just attendance object
        if (Array.isArray(data)) {
          // Guess: it’s students array
          students = data;
        } else if (data && typeof data === "object") {
          if (Array.isArray(data.students)) students = data.students;
          if (data.attendance && typeof data.attendance === "object") attendance = data.attendance;
        }

        saveData();
        renderStudents();
        updateAttendanceHeader();
        renderAttendance();
        populateDashboardClassSelector();
        updateStats();

        showToastEl(toast, "Import complete.", "#10b981");
        fileEl.value = "";
      } catch (err) {
        console.error(err);
        showToastEl(toast, "Invalid JSON.", "#ef4444");
      }
    });

    // 6) Clear Students & Attendance
    document.getElementById("clearDataBtn")?.addEventListener("click", () => {
      if (!confirm("Clear ALL students and attendance? This cannot be undone.")) return;

      students   = [];
      attendance = {};

      saveData();
      renderStudents();
      updateAttendanceHeader();
      renderAttendance();
      populateDashboardClassSelector();
      updateStats();

      showToastEl(toast, "All data cleared.", "#ef4444");
    });
  }



  /* =============================================================================
     5R) Utility: download a URL (used for exports)
     ======================================================================== */

  function downloadURL(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }
}



/* =============================================================================
   6) GLOBAL LOGOUT
   ---------------------------------------------------------------------------
   This is called from the dashboard sidebar "Logout" button.
   ========================================================================== */

function logout() {
  clearSession();

  // NOTE: We intentionally keep students/attendance to preserve demo data.
  // If you want to clear them on logout, uncomment:
  // localStorage.removeItem(STORAGE_KEYS.students);
  // localStorage.removeItem(STORAGE_KEYS.attendance);

  window.location.replace("index.html");
}



/* =============================================================================
   7) BOOTSTRAP BOTH PAGES
   ---------------------------------------------------------------------------
   Detect which page we are on via <body data-page="login|dashboard"> and run
   the appropriate initialization.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  initLoginPage();
  initDashboardPage();
});



/* =============================================================================
   8) OPTIONAL: SEED DEMO DATA (ONLY if no students exist)
   ---------------------------------------------------------------------------
   This helps first-time testers see something right away. You can remove this
   block if you don’t want any auto-seeded content.
   ========================================================================== */

(function seedDemoIfEmpty() {
  if (document.body.dataset.page !== "dashboard") return;

  // If students already exist, skip seeding
  try {
    const s = JSON.parse(localStorage.getItem(STORAGE_KEYS.students)) || [];
    if (s.length > 0) return;
  } catch {}

  const demoStudents = [
    { id: Date.now() + 1,  name: "Aarav Kumar",  roll: "1",  studentClass: "10", section: "A", mobile: "9000000001" },
    { id: Date.now() + 2,  name: "Priya Sharma", roll: "2",  studentClass: "10", section: "A", mobile: "9000000002" },
    { id: Date.now() + 3,  name: "Rahul Singh",  roll: "3",  studentClass: "10", section: "B", mobile: "9000000003" },
    { id: Date.now() + 4,  name: "Neha Verma",   roll: "4",  studentClass: "9",  section: "A", mobile: "9000000004" },
    { id: Date.now() + 5,  name: "Karan Patel",  roll: "5",  studentClass: "9",  section: "A", mobile: "9000000005" },
  ];

  localStorage.setItem(STORAGE_KEYS.students, JSON.stringify(demoStudents));

  // Some random attendance marks for current month/year so charts look alive
  const now    = new Date();
  const key    = `${String(now.getFullYear())}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const aStore = {};

  demoStudents.forEach(s => {
    aStore[s.id] = {};
    aStore[s.id][key] = {};
    for (let day = 1; day <= 30; day++) {
      // 70% chance present
      aStore[s.id][key][day] = Math.random() < 0.7;
    }
  });

  localStorage.setItem(STORAGE_KEYS.attendance, JSON.stringify(aStore));

  // If we’re on dashboard (after DOMContentLoaded), the page code will pick these up.
})();



/* =============================================================================
   9) EXTRA: SMALL ACCESSIBILITY / UX IMPROVEMENTS
   ---------------------------------------------------------------------------
   These are optional enhancements to improve keyboard navigation & focus.
   ========================================================================== */

// Press “/” to focus search input on Students page
document.addEventListener("keydown", (e) => {
  if (document.body.dataset.page !== "dashboard") return;

  const key = e.key || e.code;

  // If user is typing in an input/textarea/select, skip the shortcut
  const tag = (document.activeElement?.tagName || "").toLowerCase();
  if (["input", "textarea", "select"].includes(tag)) return;

  if (key === "/") {
    e.preventDefault();
    const searchInput = document.getElementById("searchInput");
    searchInput?.focus();
  }
});



/* =============================================================================
   10) NOTES FOR YOUR FRIENDS READING THIS FILE
   ---------------------------------------------------------------------------
   - This file is intentionally verbose with comments and spacing.
   - The logic is split into clear sections with big headers.
   - Replace localStorage auth with a real backend for production apps.
   - The attendance grid uses a fixed 30 days to keep the UI simple.
   - You can improve: real month lengths, CSV exports, pagination, edit student,
     class/section management, teacher roles, etc.
   Happy hacking! 💙
   ========================================================================== */
