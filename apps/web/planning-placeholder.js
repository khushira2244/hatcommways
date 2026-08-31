(async () => {
  if (!getToken()) { location.replace("./signin.html"); return; }
  try {
    await api("/auth/me");
    const saved = JSON.parse(sessionStorage.getItem("hatcommways_planning_result") || "null");
    if (!saved) { location.replace("./app.html"); return; }
    const proposal = saved.result;
    document.querySelector("#planning-summary").innerHTML = `<h2>${saved.event_name}</h2><dl><div><dt>Event ID</dt><dd>${saved.event_id}</dd></div><div><dt>Proposal ID</dt><dd>${proposal.id || proposal.proposal_id || "Recorded"}</dd></div><div><dt>Status</dt><dd>${proposal.status || "PENDING"}</dd></div></dl>`;
    document.querySelector("#planning-page").hidden = false;
  } catch { clearToken(); location.replace("./signin.html"); }
})();
