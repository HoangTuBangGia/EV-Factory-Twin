const screens = document.querySelectorAll(".screen");
const toast = document.querySelector("#toast");

function showScreen(name) {
  screens.forEach((screen) => screen.classList.toggle("active", screen.dataset.screen === name));
  window.scrollTo(0, 0);
}

function notify(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2600);
}

document.querySelectorAll("[data-go]").forEach((button) => {
  button.addEventListener("click", () => showScreen(button.dataset.go));
});

document.querySelector("#wow").addEventListener("click", () => {
  document.querySelector("#overlay").classList.toggle("hidden");
});

document.querySelector("#play").addEventListener("click", (event) => {
  event.currentTarget.textContent = event.currentTarget.textContent.includes("Pause") ? "▶ Play" : "⏸ Pause";
});

document.querySelector("#benchmark").addEventListener("click", () => notify("Đã lưu baseline KPI giả lập: BL-221"));
document.querySelector("#alert").addEventListener("click", () => notify("Camera focus vào AGV-07 · Mở chi tiết drift warning"));

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
