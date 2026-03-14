const latestUrl = "./data/latest.json";
const DEFAULT_SORT_DIRECTION = {
  raised: "desc",
  donors: "desc",
  donorsPerMember: "desc",
};

const sortState = { key: "raised", direction: "desc" };
let teamsCache = [];

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

function fmtDonors(count) {
  if (typeof count === "number" && Number.isFinite(count)) {
    return count.toLocaleString();
  }
  return "N/A";
}

function fmtDonorsPerMember(donorsCount, members) {
  if (
    typeof donorsCount === "number" &&
    Number.isFinite(donorsCount) &&
    typeof members === "number" &&
    Number.isFinite(members) &&
    members > 0
  ) {
    return (donorsCount / members).toFixed(2);
  }
  return "N/A";
}

function donorsPerMemberValue(team) {
  if (
    typeof team?.donors_count === "number" &&
    Number.isFinite(team.donors_count) &&
    typeof team?.members === "number" &&
    Number.isFinite(team.members) &&
    team.members > 0
  ) {
    return team.donors_count / team.members;
  }
  return null;
}

function sortValue(team, key) {
  if (key === "raised") return team.raised_cents;
  if (key === "donors") return team.donors_count;
  if (key === "donorsPerMember") return donorsPerMemberValue(team);
  return null;
}

function compareTeams(a, b, key, direction) {
  const av = sortValue(a, key);
  const bv = sortValue(b, key);
  const aMissing = av === null || av === undefined || (typeof av === "number" && !Number.isFinite(av));
  const bMissing = bv === null || bv === undefined || (typeof bv === "number" && !Number.isFinite(bv));

  if (aMissing && bMissing) return (a.name ?? "").localeCompare(b.name ?? "", undefined, { sensitivity: "base" });
  if (aMissing) return 1;
  if (bMissing) return -1;

  const cmp = Number(av) - Number(bv);
  if (cmp === 0) return (a.name ?? "").localeCompare(b.name ?? "", undefined, { sensitivity: "base" });
  return direction === "asc" ? cmp : -cmp;
}

function setupSortableHeaders() {
  const headers = document.querySelectorAll("thead th[data-sort-key]");
  for (const header of headers) {
    header.addEventListener("click", () => {
      const key = header.dataset.sortKey;
      if (!key) return;

      if (sortState.key === key) {
        sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
      } else {
        sortState.key = key;
        sortState.direction = DEFAULT_SORT_DIRECTION[key] ?? "desc";
      }

      renderTable(teamsCache);
    });
  }
}

function renderTable(teams) {
  const body = document.getElementById("totals-body");
  body.innerHTML = "";

  const sorted = [...teams].sort((a, b) => compareTeams(a, b, sortState.key, sortState.direction));

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

    const donorsCell = document.createElement("td");
    donorsCell.textContent = fmtDonors(team.donors_count);

    const donorsPerMemberCell = document.createElement("td");
    donorsPerMemberCell.textContent = fmtDonorsPerMember(team.donors_count, team.members);

    tr.append(nameCell, raisedCell, donorsCell, donorsPerMemberCell);
    body.appendChild(tr);
  }
}

async function main() {
  try {
    const data = await loadLatest();
    document.getElementById("updated-at").textContent = `Last update: ${fmtTime(data.updated_at)}`;
    teamsCache = data.teams || [];
    setupSortableHeaders();
    renderTable(teamsCache);
  } catch (err) {
    document.getElementById("updated-at").textContent = `Error: ${err.message}`;
  }
}

main();
