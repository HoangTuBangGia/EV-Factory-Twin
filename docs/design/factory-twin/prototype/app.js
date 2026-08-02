const screens = document.querySelectorAll(".screen");
const toast = document.querySelector("#toast");
const robots = {
  "agv-01": {
    name: "AGV-01", number: "01", model: "MiR250 · AMR", health: "Healthy", healthClass: "healthy",
    status: "Running", battery: 81, speed: "1.2 m/s", task: "Move pallet #P-204",
    destination: "Outbound dock", direction: "East → South", eta: "02:18",
  },
  "agv-07": {
    name: "AGV-07", number: "07", model: "Geek+ P800 · AGV", health: "Attention", healthClass: "warning",
    status: "Drift warning", battery: 66, speed: "0.8 m/s", task: "Deliver tote #T-091",
    destination: "Charging bay 02", direction: "East → South-east", eta: "04:52",
  },
  "agv-12": {
    name: "AGV-12", number: "12", model: "MiR250 · AMR", health: "Idle", healthClass: "idle",
    status: "Waiting", battery: 64, speed: "0.0 m/s", task: "Awaiting assignment",
    destination: "Inbound dock", direction: "Planned: West → North", eta: "--:--",
  },
};

function showScreen(name) {
  screens.forEach((screen) => screen.classList.toggle("active", screen.dataset.screen === name));
  window.scrollTo(0, 0);
}

function notify(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2600);
}

function selectRobot(robotId, announce = false) {
  const robot = robots[robotId];
  if (!robot) return;

  document.querySelectorAll("[data-robot]").forEach((button) => {
    const selected = button.dataset.robot === robotId;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  document.querySelectorAll(".robot-route").forEach((route) => {
    route.classList.toggle("active", route.id === `route-${robotId}`);
  });

  document.querySelector("#robot-health").textContent = robot.health;
  document.querySelector("#robot-health").className = `health ${robot.healthClass}`;
  document.querySelector("#robot-icon").textContent = robot.number;
  document.querySelector("#robot-name").textContent = robot.name;
  document.querySelector("#robot-model").textContent = robot.model;
  document.querySelector("#robot-status").textContent = robot.status;
  document.querySelector("#robot-battery").textContent = `${robot.battery}%`;
  document.querySelector("#battery-level").style.width = `${robot.battery}%`;
  document.querySelector("#battery-level").style.background = robot.battery < 70 ? "var(--amber)" : "var(--green)";
  document.querySelector("#robot-speed").textContent = robot.speed;
  document.querySelector("#robot-task").textContent = robot.task;
  document.querySelector("#robot-destination").textContent = robot.destination;
  document.querySelector("#robot-direction").textContent = robot.direction;
  document.querySelector("#robot-eta").textContent = robot.eta;

  if (announce) notify(`${robot.name} · Hiển thị thông tin và hướng di chuyển`);
}

document.querySelectorAll("[data-go]").forEach((button) => {
  button.addEventListener("click", () => showScreen(button.dataset.go));
});

document.querySelectorAll("[data-robot]").forEach((button) => {
  button.addEventListener("click", () => selectRobot(button.dataset.robot, true));
});

document.querySelector("#wow").addEventListener("click", () => {
  document.querySelector("#overlay").classList.toggle("hidden");
});

document.querySelector("#play").addEventListener("click", (event) => {
  event.currentTarget.textContent = event.currentTarget.textContent.includes("Pause") ? "▶ Play" : "⏸ Pause";
});

document.querySelector("#benchmark").addEventListener("click", () => notify("Đã lưu baseline KPI giả lập: BL-221"));
document.querySelector("#alert").addEventListener("click", () => {
  selectRobot("agv-07");
  notify("Camera focus vào AGV-07 · Hiển thị tuyến tới Charging bay 02");
});

document.querySelector("#run").addEventListener("click", () => {
  const status = document.querySelector("#run-status");
  const submit = document.querySelector("#submit");
  status.textContent = "SIM-2026-0814 hoàn tất · Guardrails passed · Risk: 1 warning, 0 critical";
  submit.disabled = false;
  notify("Simulation hoàn tất. Submit for Review đã được mở khóa.");
});

document.querySelector("#submit").addEventListener("click", () => {
  notify("Đã tạo review RV-1042");
  showScreen("review");
});

const reviewNotes = document.querySelector("#review-notes");
const approve = document.querySelector("#approve");
reviewNotes.addEventListener("input", () => {
  approve.disabled = reviewNotes.value.trim().length < 3;
});

document.querySelector("#reject").addEventListener("click", () => {
  notify("Đã yêu cầu chỉnh sửa. Scenario quay về Draft.");
  showScreen("scenario");
});

approve.addEventListener("click", () => {
  notify("Đã ghi nhận phê duyệt của con người.");
  showScreen("deploy");
});

const confirmation = document.querySelector("#confirmation");
const deploymentWindow = document.querySelector("#deployment-window");
const queue = document.querySelector("#queue");
function validateDeployment() {
  queue.disabled = confirmation.value !== "DEPLOY-ZONE-B" || !deploymentWindow.value;
}
confirmation.addEventListener("input", validateDeployment);
deploymentWindow.addEventListener("input", validateDeployment);

queue.addEventListener("click", () => {
  document.querySelector("#deploy-status").textContent = "DEP-208 đã được xếp hàng giả lập. Không có lệnh nào gửi tới ROS2.";
  queue.disabled = true;
  notify("Deployment intent DEP-208 được tạo trong prototype.");
});

selectRobot("agv-01");
