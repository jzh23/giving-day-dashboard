const historyUrl = "./data/history.json";

async function loadHistory() {
  const res = await fetch(historyUrl, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load ${historyUrl}: ${res.status}`);
  }
  return res.json();
}

function fmtTime(ts) {
  if (!ts) return "unknown";
  const d = new Date(ts);
  return d.toLocaleString();
}

function renderTable(teams) {
  const body = document.getElementById("totals-body");
  body.innerHTML = "";

  const sorted = [...teams].sort((a, b) => {
    const av = a.points.at(-1)?.raised_cents ?? 0;
    const bv = b.points.at(-1)?.raised_cents ?? 0;
    return bv - av;
  });

  for (const team of sorted) {
    const latest = team.points.at(-1);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${team.name}</td>
      <td>${latest ? latest.raised_display : "N/A"}</td>
      <td><a href="${team.url}" target="_blank" rel="noopener noreferrer">Open</a></td>
    `;
    body.appendChild(tr);
  }
}

function renderChart(teams) {
  const labels = [...new Set(teams.flatMap((t) => t.points.map((p) => fmtTime(p.ts))))];

  const palette = ["#1363df", "#ff7a59", "#15a974", "#7b61ff", "#de3c4b", "#12b5cb"];

  const datasets = teams.map((team, idx) => ({
    label: team.name,
    data: team.points.map((p) => p.raised_cents / 100),
    borderColor: palette[idx % palette.length],
    backgroundColor: "transparent",
    tension: 0.2,
    pointRadius: 2,
  }));

  const ctx = document.getElementById("history-chart").getContext("2d");
  new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      maintainAspectRatio: false,
      scales: {
        y: {
          ticks: {
            callback: (value) => `$${Number(value).toLocaleString()}`,
          },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: (context) => `${context.dataset.label}: $${context.parsed.y.toLocaleString()}`,
          },
        },
      },
    },
  });
}

async function main() {
  try {
    const data = await loadHistory();
    document.getElementById("updated-at").textContent = `Last update: ${fmtTime(data.updated_at)}`;
    const teams = data.teams || [];
    renderTable(teams);
    if (teams.length) {
      renderChart(teams);
    }
  } catch (err) {
    document.getElementById("updated-at").textContent = `Error: ${err.message}`;
  }
}

main();
