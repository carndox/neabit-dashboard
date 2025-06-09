// custom.js

document.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".task-card");
  cards.forEach((card, idx) => {
    setTimeout(() => {
      card.classList.add("visible");
    }, idx * 100); // 100ms stagger between cards
  });

  const overlay = document.getElementById("loadingOverlay");
  const bar = document.getElementById("loadingBar");
  const text = document.getElementById("loadingText");
  let progress = 0;
  let timer;

  function startFakeProgress(msg) {
    if (!overlay) return;
    text.textContent = msg || "Working...";
    progress = 0;
    bar.style.width = "0%";
    overlay.classList.add("show");
    timer = setInterval(() => {
      progress = Math.min(progress + 5, 90);
      bar.style.width = progress + "%";
    }, 500);
  }

  document.querySelectorAll("button.show-progress").forEach((btn) => {
    const form = btn.closest("form");
    if (!form) return;
    form.addEventListener("submit", () => {
      startFakeProgress(btn.dataset.loadingText || "Working...");
    });
  });
});
