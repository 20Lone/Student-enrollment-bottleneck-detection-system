// Real-time forecast chart with AJAX polling

document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('forecastChart');
    if (!ctx) return;

    let chart = null;
    const pollInterval = 60000;

    function fetchData() {
        fetch('/api/realtime-forecast')
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    console.error(data.error);
                    return;
                }
                updateChart(data);
                updateLiveIndicator();
            })
            .catch(err => console.error('Fetch error:', err));
    }

    function formatTime(isoString) {
        const d = new Date(isoString);
        return d.getHours().toString().padStart(2, '0') + ':' +
               d.getMinutes().toString().padStart(2, '0');
    }

    function updateChart(data) {
        const history = data.history || [];
        const forecast = data.forecast || [];

        // Use actual timestamps for labels
        const historyLabels = history.map(h => formatTime(h.log_time));
        const forecastLabels = forecast.map(f => formatTime(f.time));
        const allLabels = [...historyLabels, ...forecastLabels];

        const historyRequests = history.map(h => h.request_count);
        const forecastRequests = forecast.map(f => f.request_count || 0);

        const nullPadding = new Array(historyLabels.length).fill(null);
        const forecastData = [...nullPadding, ...forecastRequests];

        const nullForecastPadding = new Array(forecastLabels.length).fill(null);
        const historyData = [...historyRequests, ...nullForecastPadding];

        // Color each forecast point by predicted load class
        const forecastBgColors = forecast.map(f => {
            if (f.load_class === 2) return 'rgba(220, 38, 38, 0.7)';
            if (f.load_class === 1) return 'rgba(249, 115, 22, 0.7)';
            return 'rgba(37, 99, 235, 0.5)';
        });
        const forecastBorderColors = forecast.map(f => {
            if (f.load_class === 2) return 'rgba(220, 38, 38, 1)';
            if (f.load_class === 1) return 'rgba(249, 115, 22, 1)';
            return 'rgba(37, 99, 235, 0.5)';
        });
        const forecastPointBg = [...nullPadding, ...forecastBgColors];
        const forecastPointBorder = [...nullPadding, ...forecastBorderColors];

        const nowIndex = history.length - 0.5;

        const nowLinePlugin = {
            id: 'nowLine',
            afterDraw(chart) {
                const meta = chart.getDatasetMeta(0);
                if (!meta || !meta.data || meta.data.length === 0) return;
                const xScale = chart.scales.x;
                const yScale = chart.scales.y;
                const xPos = xScale.getPixelForValue(nowIndex);
                if (xPos < xScale.left || xPos > xScale.right) return;
                const ctx2 = chart.ctx;
                ctx2.save();
                ctx2.beginPath();
                ctx2.setLineDash([4, 4]);
                ctx2.strokeStyle = '#ef4444';
                ctx2.lineWidth = 2;
                ctx2.moveTo(xPos, yScale.top);
                ctx2.lineTo(xPos, yScale.bottom);
                ctx2.stroke();
                ctx2.fillStyle = '#ef4444';
                ctx2.font = 'bold 11px sans-serif';
                ctx2.textAlign = 'center';
                ctx2.fillText('NOW', xPos, yScale.top - 6);
                ctx2.restore();
            }
        };

        if (chart) {
            chart.destroy();
            chart = null;
        }

        chart = new Chart(ctx, {
            type: 'line',
            plugins: [nowLinePlugin],
            data: {
                labels: allLabels,
                datasets: [
                    {
                        label: 'Actual Requests',
                        data: historyData,
                        borderColor: 'rgba(37, 99, 235, 1)',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        pointHitRadius: 6,
                    },
                    {
                        label: 'Forecasted Requests',
                        data: forecastData,
                        borderColor: forecastBorderColors.length ? undefined : 'rgba(37, 99, 235, 0.5)',
                        backgroundColor: 'rgba(37, 99, 235, 0.05)',
                        borderWidth: 2,
                        borderDash: [6, 4],
                        fill: true,
                        tension: 0.3,
                        pointRadius: forecastPointBg.map(c => c && c.includes('220, 38, 38') ? 4 : 0),
                        pointBackgroundColor: forecastPointBg,
                        pointBorderColor: forecastPointBorder,
                        pointHitRadius: 6,
                    },
                    {
                        label: 'Bottleneck',
                        data: forecastData.map((v, i) => {
                            const fc = forecast[i - history.length];
                            if (fc && fc.load_class === 2) return v;
                            return null;
                        }),
                        borderColor: 'rgba(220, 38, 38, 0.8)',
                        backgroundColor: 'rgba(220, 38, 38, 0.15)',
                        borderWidth: 2,
                        borderDash: [3, 3],
                        fill: true,
                        tension: 0.3,
                        pointRadius: 5,
                        pointBackgroundColor: 'rgba(220, 38, 38, 0.9)',
                        pointBorderColor: 'rgba(220, 38, 38, 1)',
                        pointStyle: 'triangle',
                        pointHitRadius: 6,
                        spanGaps: false,
                    },
                    {
                        label: 'Moderate',
                        data: forecastData.map((v, i) => {
                            const fc = forecast[i - history.length];
                            if (fc && fc.load_class === 1) return v;
                            return null;
                        }),
                        borderColor: 'rgba(249, 115, 22, 0.8)',
                        backgroundColor: 'rgba(249, 115, 22, 0.1)',
                        borderWidth: 2,
                        borderDash: [3, 3],
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: 'rgba(249, 115, 22, 0.9)',
                        pointBorderColor: 'rgba(249, 115, 22, 1)',
                        pointStyle: 'rectRot',
                        pointHitRadius: 6,
                        spanGaps: false,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: function(items) {
                                const idx = items[0].dataIndex;
                                const isHistory = idx < history.length;
                                const label = isHistory ? 'Actual' : 'Forecasted';
                                return items[0].label + ' (' + label + ')';
                            },
                            label: function(item) {
                                const lines = [item.dataset.label + ': ' + Math.round(item.raw) + ' req/min'];
                                if (!item.datasetIndex) {
                                    const fcIdx = item.dataIndex - history.length;
                                    const fc = forecast[fcIdx];
                                    if (fc && fc.load_class_name) {
                                        lines.push('Status: ' + fc.load_class_name);
                                        lines.push('Bottleneck risk: ' + Math.round((fc.bottleneck_prob || 0) * 100) + '%');
                                    }
                                }
                                return lines;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            maxTicksLimit: 20,
                            font: { size: 11 }
                        },
                        title: {
                            display: true,
                            text: 'Time',
                            font: { size: 12 }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        title: {
                            display: true,
                            text: 'Requests/min',
                            font: { size: 12 }
                        }
                    }
                }
            }
        });
    }

    function updateLiveIndicator() {
        const el = document.getElementById('liveIndicator');
        if (el) {
            el.style.background = '#22c55e';
            el.title = 'Live - updated ' + new Date().toLocaleTimeString();
        }
    }

    fetchData();
    setInterval(fetchData, pollInterval);
});
