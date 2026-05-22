/* koru wizard GUI — vanilla JS, no framework */
(function () {
  "use strict";

  const STEP_ORDER = ["ide", "project", "strategy", "confirm", "done"];
  const STEP_LABELS = {
    ide: "1. IDE",
    project: "2. Projekt",
    strategy: "3. Strategia",
    confirm: "4. Potwierdzenie",
    done: "Gotowe",
  };

  let state = null;
  let openHelpId = null;

  const el = (id) => document.getElementById(id);

  function showError(msg) {
    const box = el("error");
    if (box) {
      box.textContent = msg || "";
      box.style.display = msg ? "block" : "none";
    }
  }

  function stepIndex(step) {
    if (step === "confirm") return 3;
    if (step === "done") return 4;
    const i = STEP_ORDER.indexOf(step);
    return i >= 0 ? i : 0;
  }

  function updateStepPills(step) {
    const idx = stepIndex(step);
    document.querySelectorAll(".step-pill").forEach((pill, i) => {
      pill.classList.remove("active", "done");
      if (step === "done") {
        pill.classList.add("done");
      } else if (i < idx) {
        pill.classList.add("done");
      } else if (i === idx) {
        pill.classList.add("active");
      }
    });
  }

  function showPanel(step) {
    document.querySelectorAll(".panel").forEach((p) => {
      p.classList.toggle("active", p.dataset.step === step);
    });
    updateStepPills(step);
  }

  async function apiPost(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || res.statusText || "request failed");
    }
    return data;
  }

  async function loadState() {
    showError("");
    const res = await fetch("/wizard/api/state", { credentials: "same-origin" });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "failed to load state");
    }
    state = data;
    render();
  }

  function renderIde() {
    const list = el("ide-list");
    if (!list) return;
    list.innerHTML = "";
    (state.ides || []).forEach((ide) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "card";
      const badge = ide.running
        ? '<span class="badge">running</span>'
        : '<span class="badge installed">installed</span>';
      btn.innerHTML =
        '<div class="title">' +
        escapeHtml(ide.label) +
        badge +
        "</div>" +
        '<div class="meta">' +
        escapeHtml(ide.path) +
        "</div>";
      btn.addEventListener("click", () => selectIde(ide.id));
      list.appendChild(btn);
    });
    const skip = document.createElement("button");
    skip.type = "button";
    skip.className = "card";
    skip.innerHTML =
      '<div class="title">(pomiń — wybierz projekt ręcznie)</div>' +
      '<div class="meta">skip IDE selection</div>';
    skip.addEventListener("click", () => selectIde("__none"));
    list.appendChild(skip);
  }

  function renderProjects() {
    const list = el("project-list");
    if (!list) return;
    list.innerHTML = "";
    (state.projects || []).forEach((p) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "card";
      btn.innerHTML =
        '<div class="title">' + escapeHtml(p.path) + "</div>" +
        '<div class="meta">' + escapeHtml(p.source) + "</div>";
      btn.addEventListener("click", () => selectProject(p.path));
      list.appendChild(btn);
    });
    if (state.fallback_cwd) {
      const cwd = document.createElement("button");
      cwd.type = "button";
      cwd.className = "card";
      cwd.innerHTML =
        '<div class="title">Shell cwd</div>' +
        '<div class="meta">' + escapeHtml(state.fallback_cwd) + "</div>";
      cwd.addEventListener("click", () => selectProject("__cwd"));
      list.appendChild(cwd);
    }
  }

  function renderStrategy() {
    const strat = state.strategy || {};
    const prompt = el("strategy-prompt");
    if (prompt) prompt.textContent = strat.prompt || "";
    const list = el("strategy-list");
    if (!list) return;
    list.innerHTML = "";
    openHelpId = null;
    (strat.options || []).forEach((opt) => {
      const wrap = document.createElement("div");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "card";
      btn.innerHTML =
        '<div class="title">' +
        escapeHtml(opt.label) +
        (opt.has_help ? ' <span class="meta">[?]</span>' : "") +
        "</div>";
      btn.addEventListener("click", () => selectStrategy(opt.id));
      wrap.appendChild(btn);
      if (opt.has_help) {
        const helpBtn = document.createElement("button");
        helpBtn.type = "button";
        helpBtn.className = "btn secondary";
        helpBtn.style.marginTop = "0.35rem";
        helpBtn.style.fontSize = "0.8rem";
        helpBtn.textContent = "? " + opt.label.slice(0, 40);
        const box = document.createElement("div");
        box.className = "help-box";
        box.textContent = opt.help;
        helpBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          const show = openHelpId !== opt.id;
          openHelpId = show ? opt.id : null;
          box.classList.toggle("visible", show);
        });
        wrap.appendChild(helpBtn);
        wrap.appendChild(box);
      }
      list.appendChild(wrap);
    });
    const pathEl = el("strategy-path");
    if (pathEl && state.strategy_path && state.strategy_path.length) {
      pathEl.textContent = "Ścieżka: " + state.strategy_path.join(" → ");
      pathEl.style.display = "block";
    } else if (pathEl) {
      pathEl.style.display = "none";
    }
  }

  function renderConfirm() {
    const pending = state.pending || {};
    const box = el("confirm-details");
    if (!box) return;
    box.innerHTML =
      "<h3>" +
      escapeHtml(pending.title || "") +
      "</h3>" +
      "<pre>" +
      escapeHtml(pending.body || "") +
      "</pre>" +
      "<p class='meta'>Projekt: " +
      escapeHtml(state.project_path || "") +
      "</p>";
  }

  function renderDone() {
    const r = state.result || {};
    const box = el("done-details");
    if (!box) return;
    let html = "<h3>✓ Ticket gotowy</h3>";
    if (r.ticket_id) {
      html += "<p><strong>" + escapeHtml(r.ticket_id) + "</strong> — " + escapeHtml(r.ticket_title || "") + "</p>";
    } else {
      html += "<p>(podgląd — ticket nie zapisany, --no-create)</p>";
    }
    html += "<p>Strategia: " + escapeHtml((r.strategy_path || []).join(" → ")) + "</p>";
    if (r.next_steps && r.next_steps.length) {
      html += "<p><strong>Co teraz / What's next:</strong></p><ol class='next-steps'>";
      r.next_steps.forEach((s) => {
        html += "<li>" + escapeHtml(s) + "</li>";
      });
      html += "</ol>";
    }
    box.innerHTML = html;
  }

  function render() {
    if (!state) return;
    showPanel(state.step);
    if (state.step === "ide") renderIde();
    if (state.step === "project") renderProjects();
    if (state.step === "strategy") renderStrategy();
    if (state.step === "confirm") renderConfirm();
    if (state.step === "done") renderDone();
  }

  async function selectIde(ideId) {
    try {
      state = await apiPost("/wizard/api/ide", { csrf: state.csrf, ide_id: ideId });
      render();
    } catch (e) {
      showError(String(e.message || e));
    }
  }

  async function selectProject(projectPath) {
    try {
      state = await apiPost("/wizard/api/project", {
        csrf: state.csrf,
        project_path: projectPath,
      });
      render();
    } catch (e) {
      showError(String(e.message || e));
    }
  }

  async function selectStrategy(optionId) {
    try {
      state = await apiPost("/wizard/api/strategy", {
        csrf: state.csrf,
        option_id: optionId,
      });
      render();
    } catch (e) {
      showError(String(e.message || e));
    }
  }

  async function confirmTicket() {
    try {
      state = await apiPost("/wizard/api/confirm", { csrf: state.csrf });
      render();
      await apiPost("/wizard/done", { csrf: state.csrf });
    } catch (e) {
      showError(String(e.message || e));
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  el("btn-confirm")?.addEventListener("click", confirmTicket);
  el("btn-done-close")?.addEventListener("click", () => {
    window.close();
  });

  loadState().catch((e) => showError(String(e.message || e)));
})();
