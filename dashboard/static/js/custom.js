// custom.js

document.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".task-card");
  cards.forEach((card, idx) => {
    setTimeout(() => {
      card.classList.add("visible");
    }, idx * 100); // 100ms stagger between cards
  });

  // Show overlay while waiting for long-running tasks
  const overlay = document.getElementById("loadingOverlay");
  document.querySelectorAll("form.needs-wait").forEach(f => {
    f.addEventListener("submit", () => {
      if (overlay) {
        overlay.classList.remove("d-none");
      }
    });
  });
});
