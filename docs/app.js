const latestUrl = "./data/latest.json";

async function loadLatest() {
  const res = await fetch(latestUrl, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load ${latestUrl}: ${res.status}`);
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
    const av = a.raised_cents ?? 0;
    const bv = b.raised_cents ?? 0;
    return bv - av;
  });

  for (const team of sorted) {
    const tr = document.createElement("tr");

    const nameCell = document.createElement("td");
    if (team.url) {
      const link = document.createElement("a");
      link.href = team.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = team.name;
      nameCell.appendChild(link);
    } else {
      nameCell.textContent = team.name ?? "Unknown";
    }

    const raisedCell = document.createElement("td");
    raisedCell.textContent = team.raised_display ?? "N/A";

    tr.append(nameCell, raisedCell);
    body.appendChild(tr);
  }
}

async function main() {
  try {
    const data = await loadLatest();
    document.getElementById("updated-at").textContent = `Last update: ${fmtTime(data.updated_at)}`;
    const teams = data.teams || [];
    renderTable(teams);
  } catch (err) {
    document.getElementById("updated-at").textContent = `Error: ${err.message}`;
  }
}

main();
