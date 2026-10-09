/* DRC Expat Compliance — Dashboard Charts */

document.addEventListener('DOMContentLoaded', function() {
  const trendCanvas = document.getElementById('trendChart');
  if (!trendCanvas) return;

  const data = window.__DASHBOARD_DATA__;
  if (!data) return;

  new Chart(trendCanvas, {
    type: 'bar',
    data: {
      labels: data.trend_labels,
      datasets: [
        { label: 'Passports', data: data.trend_passports, backgroundColor: '#1565C0', borderRadius: 6 },
        { label: 'Cartes', data: data.trend_cartes, backgroundColor: '#2A9D8F', borderRadius: 6 },
        { label: 'Visas', data: data.trend_visas, backgroundColor: '#F4A261', borderRadius: 6 },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 12, weight: 600 }, boxWidth: 12, padding: 16 } },
        tooltip: { backgroundColor: '#0B132B', titleFont: { family: 'Inter' }, bodyFont: { family: 'Inter' } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 } } },
        y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { font: { family: 'Inter', size: 11 }, stepSize: 1 } }
      }
    }
  });

  // Quota doughnut
  const quotaCanvas = document.getElementById('quotaChart');
  if (quotaCanvas && data.quota_pct !== undefined) {
    const pct = parseFloat(data.quota_pct);
    const cap = parseFloat(data.quota_cap);
    new Chart(quotaCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Current Expat %', 'Remaining Headroom'],
        datasets: [{
          data: [pct, Math.max(0, cap - pct)],
          backgroundColor: [pct > cap ? '#E63946' : '#2A9D8F', '#E2E8F0'],
          borderWidth: 0,
          cutout: '78%'
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0B132B', titleFont: { family: 'Inter' }, bodyFont: { family: 'Inter' },
            callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw}%` }
          }
        }
      }
    });
  }
});