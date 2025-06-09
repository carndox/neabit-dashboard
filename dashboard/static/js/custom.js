// custom.js - handles animations and async task execution

document.addEventListener('DOMContentLoaded', () => {
  // fade in task cards
  document.querySelectorAll('.task-card').forEach((card, idx) => {
    setTimeout(() => card.classList.add('visible'), idx * 100);
  });

  // run-all button
  const runAllBtn = document.getElementById('runAllBtn');
  if (runAllBtn) {
    runAllBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const offset = document.getElementById('runAllOffset').value || 1;
      startRunAll(offset);
    });
  }

  // individual task forms
  document.querySelectorAll('.run-task-form').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const offset = form.querySelector('input[name="offset"]').value || 1;
      const action = form.getAttribute('action');
      startTaskRun(action, offset);
    });
  });
});

function showProgress() {
  $('#progressModal').modal({backdrop: 'static', keyboard: false});
  updateProgress(0, 1, 'Starting...');
}

function updateProgress(current, total, message) {
  const perc = Math.floor((current / total) * 100);
  const bar = document.querySelector('#progressModal .progress-bar');
  const text = document.getElementById('progressText');
  if (bar) bar.style.width = perc + '%';
  if (text) text.textContent = message;
}

function hideProgress() {
  $('#progressModal').modal('hide');
}

function pollProgress(id, onDone) {
  fetch(`/progress/${id}`)
    .then(r => r.json())
    .then(data => {
      updateProgress(data.current, data.total, data.message);
      if (data.done) {
        if (onDone) onDone();
      } else {
        setTimeout(() => pollProgress(id, onDone), 1000);
      }
    })
    .catch(() => { setTimeout(() => pollProgress(id, onDone), 1000); });
}

function startRunAll(offset) {
  showProgress();
  fetch('/run_all_async', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: `offset=${offset}`
  })
  .then(r => r.json())
  .then(data => {
    if (data.run_id) {
      pollProgress(data.run_id, () => { hideProgress(); location.reload(); });
    } else {
      hideProgress();
      alert('Failed to start');
    }
  })
  .catch(() => { hideProgress(); alert('Failed to start'); });
}

function startTaskRun(action, offset) {
  showProgress();
  fetch(action, {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: `offset=${offset}`
  })
  .then(r => r.json())
  .then(data => {
    if (data.run_id) {
      pollProgress(data.run_id, () => { hideProgress(); location.reload(); });
    } else {
      hideProgress();
      alert('Failed to start');
    }
  })
  .catch(() => { hideProgress(); alert('Failed to start'); });
}
