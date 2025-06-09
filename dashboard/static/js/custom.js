// custom.js

document.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".task-card");
  cards.forEach((card, idx) => {
    setTimeout(() => {
      card.classList.add("visible");
    }, idx * 100); // 100ms stagger between cards
  });
});
