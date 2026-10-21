/* ═══════════════════════════════════════════════════════════
   ECharts Dashboard Visualizations — Bilingual
   Reads window.__DASHBOARD__ (injected by Django template)
   ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {
  if (typeof echarts === 'undefined') {
    console.warn('ECharts not loaded');
    return;
  }

  const data = window.__DASHBOARD__ || {};
  const L = data.labels || {};   // translated labels from Django

  function isDark() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
  }

  function palette() {
    const dark = isDark();
    return {
      text: dark ? '#f8fafc' : '#0f172a',
      textMuted: dark ? '#94a3b8' : '#64748b',
      grid: dark ? '#334155' : '#e2e8f0',
      brand: '#0d9488',
      brandLight: '#2dd4bf',
      warn: '#f59e0b',
      danger: '#dc2626',
      info: '#3b82f6',
      expired: '#991b1b',
    };
  }

  // ═══════════════════════════════════════════════════════
  // CHART 1 — Document Expiry Funnel (grouped bars + expired)
  // ═══════════════════════════════════════════════════════
  const funnelEl = document.getElementById('chart-expiry-funnel');
  if (funnelEl) {
    const c = palette();

    const labels = [L.already_expired || 'Already Expired', ...(data.trend_labels || [])];
    const passports = [data.trend_passports_expired || 0, ...(data.trend_passports || [])];
    const cartes = [data.trend_cartes_expired || 0, ...(data.trend_cartes || [])];
    const visas = [data.trend_visas_expired || 0, ...(data.trend_visas || [])];

    const chart = echarts.init(funnelEl);
    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      legend: {
        data: [L.passports || 'Passports', L.cartes || 'Cartes', L.visas || 'Visas'],
        textStyle: { color: c.textMuted, fontFamily: 'Inter', fontSize: 11 },
        bottom: 0,
        itemGap: 20,
        icon: 'roundRect',
        itemWidth: 12,
        itemHeight: 12,
      },
      grid: { left: 40, right: 20, top: 20, bottom: 60, containLabel: true },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { color: c.textMuted, fontFamily: 'Inter', fontSize: 10, interval: 0, rotate: 0 },
        axisLine: { lineStyle: { color: c.grid } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        axisLabel: {
          color: c.textMuted, fontFamily: 'Inter', fontSize: 11,
          formatter: (v) => Number.isInteger(v) ? v : '',
        },
        splitLine: { lineStyle: { color: c.grid, type: 'dashed' } },
        axisLine: { show: false },
      },
      series: [
        {
          name: L.passports || 'Passports', type: 'bar', data: passports,
          itemStyle: { color: (p) => p.dataIndex === 0 ? c.expired : c.brand, borderRadius: [4, 4, 0, 0] },
          barMaxWidth: 28,
        },
        {
          name: L.cartes || 'Cartes', type: 'bar', data: cartes,
          itemStyle: { color: (p) => p.dataIndex === 0 ? c.expired : c.info, borderRadius: [4, 4, 0, 0] },
          barMaxWidth: 28,
        },
        {
          name: L.visas || 'Visas', type: 'bar', data: visas,
          itemStyle: { color: (p) => p.dataIndex === 0 ? c.expired : c.warn, borderRadius: [4, 4, 0, 0] },
          barMaxWidth: 28,
        },
      ],
    });

    window.addEventListener('resize', () => chart.resize());
  }

  // ═══════════════════════════════════════════════════════
  // CHART 2 — Expat Quota Gauge
  // ═══════════════════════════════════════════════════════
  const gaugeEl = document.getElementById('chart-quota-gauge');
  if (gaugeEl) {
    const c = palette();
    const pct = parseFloat(data.quota_pct || 0);
    const cap = parseFloat(data.quota_cap || 6.5);
    const headroom = parseInt(data.quota_headroom || 0, 10);
    const expat = parseInt(data.quota_expat || 0, 10);
    const congo = parseInt(data.quota_congo || 0, 10);
    const overCap = pct > cap;
    const axisMax = Math.max(cap * 1.5, pct * 1.2, 10);

    // Build the "X expats · Y Congolese" label
    const quotaLabel = (L.of_cap || '{cap}% cap — {n} expats')
      .replace('{cap}', cap)
      .replace('{n}', expat);

    const chart = echarts.init(gaugeEl);
    chart.setOption({
      series: [
        {
          type: 'gauge',
          startAngle: 210,
          endAngle: -30,
          min: 0,
          max: axisMax,
          splitNumber: 5,
          radius: '92%',
          progress: {
            show: true, width: 20, roundCap: false,
            itemStyle: { color: overCap ? c.danger : c.brand },
          },
          axisLine: { lineStyle: { width: 20, color: [[1, c.grid]] } },
          pointer: { show: false },
          axisTick: { show: true, length: 4, lineStyle: { color: c.textMuted, width: 1 } },
          splitLine: { show: true, length: 8, lineStyle: { color: c.textMuted, width: 2 } },
          axisLabel: {
            show: true, distance: -30, color: c.textMuted,
            fontSize: 10, fontFamily: 'Inter',
            formatter: (v) => v.toFixed(0),
          },
          anchor: { show: false },
          detail: {
            valueAnimation: true, formatter: '{value}%',
            color: overCap ? c.danger : c.brand,
            fontSize: 28, fontWeight: 800, fontFamily: 'Inter',
            offsetCenter: [0, '-8%'],
          },
          title: {
            offsetCenter: [0, '22%'],
            color: c.textMuted, fontSize: 11, fontFamily: 'Inter',
          },
          data: [{
            value: pct,
            name: quotaLabel,
            itemStyle: { color: overCap ? c.danger : c.brand },
          }],
        },
        {
          type: 'gauge',
          startAngle: 210,
          endAngle: -30,
          min: 0,
          max: axisMax,
          radius: '92%',
          axisLine: { show: false },
          pointer: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          anchor: { show: false },
          data: [],
          detail: { show: false },
          title: { show: false },
          graphic: (() => {
            const capAngle = 210 - (cap / axisMax) * 240;
            const rad = (capAngle * Math.PI) / 180;
            const r = 105;
            const x = r * Math.cos(rad);
            const y = r * Math.sin(rad);
            return [
              {
                type: 'circle',
                left: 'center', top: 'center',
                shape: { cx: x, cy: -y, r: 5 },
                style: { fill: c.danger, stroke: '#fff', lineWidth: 2 },
                z: 100,
              },
              {
                type: 'text',
                left: 'center', top: 'center',
                style: {
                  text: `${L.cap || 'CAP'} ${cap}%`,
                  x: x + 12, y: -y - 4,
                  fill: c.danger,
                  font: '600 10px Inter',
                },
                z: 100,
              },
            ];
          })(),
        },
      ],
    });

    window.addEventListener('resize', () => chart.resize());
  }

  // Re-render on theme switch
  window.addEventListener('theme-changed', function () {
    location.reload();
  });
});