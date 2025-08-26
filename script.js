const sidebar = document.getElementById("sidebar");
const sidebarToggleArrow = document.getElementById("sidebarToggleArrow");

// Sidebar toggle function
function toggleSidebar() {
  const isShown = sidebar.classList.contains("show");
  if (window.innerWidth <= 768) {
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
    sidebar.classList.toggle("hidden");
    if (sidebar.classList.contains("hidden")) {
      document.querySelector(".main-content").style.marginLeft = "0";
    } else {
      document.querySelector(".main-content").style.marginLeft = "220px";
    }
  }
}

// Initialize arrow toggle on load and window resize
function initializeSidebarToggleArrow() {
  if (window.innerWidth <= 768) {
    sidebar.classList.remove("hidden");
    sidebar.classList.remove("show");
    sidebarToggleArrow.textContent = "▶";
    document.querySelector(".main-content").style.marginLeft = "0";
    sidebarToggleArrow.style.display = "block";
  } else {
    sidebarToggleArrow.style.display = "none";
    sidebar.classList.remove("show");
    sidebar.classList.remove("hidden");
    document.querySelector(".main-content").style.marginLeft = "220px";
  }
}

// Event listener for toggle arrow click
sidebarToggleArrow.addEventListener("click", toggleSidebar);
// Event listener for window resize
window.addEventListener("resize", initializeSidebarToggleArrow);

// Your existing code below for attendance tracker...

// Toast Notification
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("show");
  if (toast._timeout) clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => {
    toast.classList.remove("show");
  }, 2500);
}

function saveData() {
  localStorage.setItem("students", JSON.stringify(students));
  localStorage.setItem("attendance", JSON.stringify(attendance));
}
function loadData() {
  const s = localStorage.getItem("students");
  const a = localStorage.getItem("attendance");
  if (s) students = JSON.parse(s);
  if (a) attendance = JSON.parse(a);
}

let students = [];
let attendance = {};

const studentTable = document.getElementById("studentTable");
const attendanceTable = document.getElementById("attendanceTable");
const attendanceHeader = document.getElementById("attendanceHeader");

const viewSelect = document.getElementById("viewSelect");
const classSelector = document.getElementById("classSelector");

function updateAttendanceHeader() {
  attendanceHeader.innerHTML = "<th class='p-2 border'>ID</th><th class='p-2 border'>Name</th>";
  for (let i = 1; i <= 30; i++) {
    attendanceHeader.innerHTML += `<th class="p-2 border">${i}</th>`;
  }
}

function renderAttendance() {
  const month = document.getElementById("monthSelect").value;
  const year = document.getElementById("yearSelect").value;
  const classFilterSelection = document.getElementById("classFilter").value;

  attendanceTable.innerHTML = students
    .filter(s => classFilterSelection === "all" || s.studentClass === classFilterSelection)
    .map(s => {
      let days = "";
      for (let i = 1; i <= 30; i++) {
        const key = `${year}-${month}`;
        const checked = attendance[s.id] && attendance[s.id][key] && attendance[s.id][key][i] ? "checked" : "";
        days += `<td class="border p-2 text-center"><input type="checkbox" data-student="${s.id}" data-day="${i}" ${checked}></td>`;
      }
      return `<tr><td class="border p-2">${s.id}</td><td class="border p-2">${s.name}</td>${days}</tr>`;
    })
    .join("");
}

document.getElementById("studentForm").addEventListener("submit", function (e) {
  e.preventDefault();
  const student = {
    id: Date.now(),
    name: document.getElementById("name").value.trim(),
    roll: document.getElementById("roll").value.trim(),
    studentClass: document.getElementById("class").value.trim(),
    section: document.getElementById("section").value.trim(),
    mobile: document.getElementById("mobile").value.trim(),
  };
  students.push(student);
  saveData();
  renderStudents();
  renderAttendance();
  populateDashboardClassSelector();
  this.reset();
  closeStudentModal();
  updateStats();
  showToast(`Student ${student.name} added`);
});

function renderStudents() {
  studentTable.innerHTML = students
    .map(s => `
      <tr>
        <td class="border p-2">${s.roll}</td>
        <td class="border p-2">${s.name}</td>
        <td class="border p-2">${s.studentClass}</td>
        <td class="border p-2">${s.section}</td>
        <td class="border p-2">${s.mobile}</td>
        <td class="border p-2 text-center">
          <button class="bg-red-500 text-white px-2 py-1 rounded" onclick="deleteStudent(${s.id})">🗑</button>
        </td>
      </tr>
    `).join("");
  document.getElementById("totalStudentsCard").textContent = students.length;
}

function deleteStudent(id) {
  const student = students.find(s => s.id === id);
  students = students.filter(s => s.id !== id);
  delete attendance[id];
  saveData();
  renderStudents();
  renderAttendance();
  populateDashboardClassSelector();
  updateStats();
  showToast(`Student ${student?.name || ""} deleted`);
}
window.deleteStudent = deleteStudent;

document.getElementById("attendanceSection").addEventListener("change", e => {
  if (e.target.type === "checkbox") {
    const studentId = e.target.dataset.student;
    const day = e.target.dataset.day;
    const month = document.getElementById("monthSelect").value;
    const year = document.getElementById("yearSelect").value;
    const key = `${year}-${month}`;
    if (!attendance[studentId]) attendance[studentId] = {};
    if (!attendance[studentId][key]) attendance[studentId][key] = {};
    attendance[studentId][key][day] = e.target.checked;
    saveData();
    updateStats();
    showToast(`Roll ${studentId} marked as ${e.target.checked ? "Present" : "Absent"} (Day ${day})`);
  }
});

let barChart, doughnutChart;

function renderCharts(presentData, absentData, days) {
  const labels = Array.from({ length: days }, (_, i) => i + 1);

  if (barChart) barChart.destroy();
  if (doughnutChart) doughnutChart.destroy();

  barChart = new Chart(document.getElementById("barChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Present",
          data: presentData.slice(0, days),
          backgroundColor: "#3b82f6",
        },
        {
          label: "Absent",
          data: absentData.slice(0, days),
          backgroundColor: "#f87171",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
      },
      plugins: {
        zoom: {
          zoom: {
            wheel: { enabled: false },
            pinch: { enabled: false },
          },
          pan: { enabled: false },
        },
      },
    },
  });

  doughnutChart = new Chart(document.getElementById("doughnutChart"), {
    type: "doughnut",
    data: {
      labels: ["Present", "Absent"],
      datasets: [
        {
          data: [
            presentData.reduce((a, b) => a + b, 0),
            absentData.reduce((a, b) => a + b, 0),
          ],
          backgroundColor: ["#3b82f6", "#f87171"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });
}

function updateStats() {
  const month = document.getElementById("monthSelect").value;
  const year = document.getElementById("yearSelect").value;
  const key = `${year}-${month}`;

  const totalDays = parseInt(viewSelect.value, 10);
  const selectedClass = classSelector.value;

  const presentData = Array(30).fill(0);
  const absentData = Array(30).fill(0);

  students.forEach(s => {
    if (selectedClass !== "all" && s.studentClass !== selectedClass) return;
    if (attendance[s.id] && attendance[s.id][key]) {
      for (let i = 1; i <= 30; i++) {
        if (attendance[s.id][key][i]) presentData[i - 1]++;
        else absentData[i - 1]++;
      }
    } else {
      for (let i = 1; i <= 30; i++) {
        absentData[i - 1]++;
      }
    }
  });

  const presentClipped = presentData.slice(0, totalDays);
  const absentClipped = absentData.slice(0, totalDays);

  const totalChecks = presentClipped.reduce((a, b) => a + b, 0) + absentClipped.reduce((a, b) => a + b, 0);
  const totalPresent = presentClipped.reduce((a, b) => a + b, 0);
  const totalAbsent = absentClipped.reduce((a, b) => a + b, 0);

  const percentPresent = totalChecks ? ((totalPresent / totalChecks) * 100).toFixed(1) : 0;
  const percentAbsent = totalChecks ? ((totalAbsent / totalChecks) * 100).toFixed(1) : 0;

  document.getElementById("presentPercent").textContent = percentPresent + "%";
  document.getElementById("absentPercent").textContent = percentAbsent + "%";

  renderCharts(presentData, absentData, totalDays);
}

// Populate dashboard class selector from students list
function populateDashboardClassSelector() {
  classSelector.innerHTML = `<option value="all">All Classes</option>`;
  [...new Set(students.map(s => s.studentClass))].forEach(c => {
    if (c) {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      classSelector.appendChild(opt);
    }
  });
}

viewSelect.addEventListener("change", () => {
  renderAttendance();
  updateStats();
});

classSelector.addEventListener("change", () => {
  updateStats();
});

// Populate filters for attendance section
function populateFilters() {
  const monthSelect = document.getElementById("monthSelect");
  const months = [
    "01","02","03","04","05","06",
    "07","08","09","10","11","12"
  ];
  months.forEach(m => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    monthSelect.appendChild(opt);
  });
  monthSelect.value = new Date().toISOString().slice(5,7);

  const yearSelect = document.getElementById("yearSelect");
  const currentYear = new Date().getFullYear();
  for (let y = currentYear; y >= currentYear - 5; y--) {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = y;
    yearSelect.appendChild(opt);
  }
  yearSelect.value = currentYear;

  updateClassFilter();
}

function updateClassFilter() {
  const classFilter = document.getElementById("classFilter");
  classFilter.innerHTML = `<option value="all">All Classes</option>`;
  [...new Set(students.map(s => s.studentClass))].forEach(c => {
    if (c) {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      classFilter.appendChild(opt);
    }
  });
}

document.getElementById("monthSelect").addEventListener("change", () => {
  renderAttendance();
  updateStats();
});
document.getElementById("yearSelect").addEventListener("change", () => {
  renderAttendance();
  updateStats();
});
document.getElementById("classFilter").addEventListener("change", () => {
  renderAttendance();
  updateStats();
});

// Search input filter
const searchInput = document.getElementById("searchInput");
if (searchInput){
  searchInput.addEventListener("input", function() {
    const val = this.value.toLowerCase();
    document.querySelectorAll("#studentTable tr").forEach(row => {
      row.style.display = row.textContent.toLowerCase().includes(val) ? "" : "none";
    });
  });
}
// Page navigation and section show/hide
const pages = {
  dashboard: document.getElementById("dashboardSection"),
  students: document.getElementById("studentsSection"),
  attendance: document.getElementById("attendanceSection"),
  settings: document.getElementById("settingsSection"),
};
function showPage(page){
  Object.values(pages).forEach(sec=>sec.classList.add("hidden"));
  if(pages[page]){
    pages[page].classList.remove("hidden");
    document.getElementById("pageTitle").textContent=page.charAt(0).toUpperCase()+page.slice(1);
  }
}
document.querySelectorAll(".sidebar nav ul li").forEach(item=>{
  item.addEventListener("click",()=>{
    document.querySelectorAll(".sidebar nav ul li").forEach(li=>li.classList.remove("active"));
    item.classList.add("active");
    showPage(item.dataset.page);
  });
});
// Modal open/close functions
function openStudentModal(){
  document.getElementById("studentModal").classList.remove("hidden");
}
function closeStudentModal(){
  document.getElementById("studentModal").classList.add("hidden");
}
window.openStudentModal=openStudentModal;
window.closeStudentModal=closeStudentModal;
// Initializations
loadData();
populateFilters();
renderStudents();
populateDashboardClassSelector();
updateAttendanceHeader();
renderAttendance();
updateStats();
showPage("dashboard");
// Responsive chart resize
window.addEventListener("resize",()=>{
  if(barChart)barChart.resize();
  if(doughnutChart)doughnutChart.resize();
});

// Initialize sidebar toggle arrow state
window.addEventListener("load", () => {
  if(window.innerWidth <= 768){
    sidebar.classList.remove("hidden");
    sidebar.classList.remove("show");
    sidebarToggleArrow.textContent = "▶";
    document.querySelector(".main-content").style.marginLeft = "0";
    sidebarToggleArrow.style.display = "block";
  } else {
    sidebarToggleArrow.style.display = "none";
    sidebar.classList.remove("show");
    sidebar.classList.remove("hidden");
    document.querySelector(".main-content").style.marginLeft = "220px";
  }
});
