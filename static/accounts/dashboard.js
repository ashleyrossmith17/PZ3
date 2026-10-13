document.addEventListener('DOMContentLoaded', () => {
  const source = document.getElementById('dashboard-data');
  if (!source) return;
  const data = JSON.parse(source.textContent);
  const colors = ['#206bc4', '#2fb344', '#f76707', '#ae3ec9', '#d63939', '#1098ad'];
  [['coursesChart', 'courses', 'doughnut'], ['studentsChart', 'students', 'bar'], ['loadChart', 'load', 'pie']].forEach(([id, key, type]) => new Chart(document.getElementById(id), {type, data: {labels: data[key].labels, datasets: [{label: 'Количество', data: data[key].values, backgroundColor: colors, borderWidth: 0}]}, options: {responsive: true, maintainAspectRatio: false, animation: false, plugins: {legend: {position: 'bottom'}}, scales: type === 'bar' ? {y: {beginAtZero: true, ticks: {precision: 0}}} : {}}}));
});
