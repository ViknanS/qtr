/* qqr site interactions. Depends on arena.js (window.Arena). */
(function () {
  "use strict";
  const A = window.Arena;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const fmt = (v, d = 2) => (Number.isFinite(v) ? v.toFixed(d) : "–");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Same eight rollouts as qqr/demo.py (SAMPLE_ROLLOUTS)
  const SAMPLE = [
    { id: "R0", quality: 6.0, summary: "Reasonable itinerary, misses opening hours" },
    { id: "R1", quality: 8.5, summary: "Checks weather + transit, balanced pacing" },
    { id: "R2", quality: 4.0, summary: "Generic list, no tool calls" },
    { id: "R3", quality: 7.0, summary: "Good POIs, budget slightly over" },
    { id: "R4", quality: 9.0, summary: "Verified routes, costs and backups" },
    { id: "R5", quality: 3.0, summary: "Hallucinated attraction" },
    { id: "R6", quality: 7.0, summary: "Solid plan, terse explanation" },
    { id: "R7", quality: 5.5, summary: "Over-packed day one" },
  ];

  // ------------------------------------------------------------ utilities
  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove("show"), 1800);
  }
  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied to clipboard");
    } catch (e) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); toast("Copied to clipboard"); } catch (err) { toast("Copy failed: select the text manually"); }
      ta.remove();
    }
  }
  function setupTablist(list, onSelect) {
    const tabs = $$('[role="tab"]', list);
    function select(tab, focus) {
      tabs.forEach((t) => {
        const on = t === tab;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
      });
      if (focus) tab.focus();
      onSelect(tab);
    }
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => select(t, false));
      t.addEventListener("keydown", (e) => {
        let j = null;
        if (e.key === "ArrowRight") j = (i + 1) % tabs.length;
        if (e.key === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
        if (e.key === "Home") j = 0;
        if (e.key === "End") j = tabs.length - 1;
        if (j !== null) { e.preventDefault(); select(tabs[j], true); }
      });
    });
    return select;
  }

  // ---------------------------------------------------------------- theme
  (function theme() {
    const btn = $("#theme-toggle");
    const root = document.documentElement;
    const effective = () => root.getAttribute("data-theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const label = () => btn.setAttribute("aria-label", effective() === "dark" ? "Switch to light theme" : "Switch to dark theme");
    label();
    btn.addEventListener("click", () => {
      const next = effective() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("qqr-theme", next); } catch (e) {}
      label();
    });
  })();

  // ------------------------------------------------------------------ nav
  (function nav() {
    const btn = $("#menu-btn");
    const links = $("#nav-links");
    btn.addEventListener("click", () => {
      const open = links.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
    $$("a", links).forEach((a) => a.addEventListener("click", () => {
      links.classList.remove("open");
      btn.setAttribute("aria-expanded", "false");
    }));
    if ("IntersectionObserver" in window) {
      const map = new Map($$("a", links).map((a) => [a.getAttribute("href").slice(1), a]));
      const io = new IntersectionObserver((entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            map.forEach((a) => a.removeAttribute("aria-current"));
            const a = map.get(en.target.id);
            if (a) a.setAttribute("aria-current", "true");
          }
        });
      }, { rootMargin: "-45% 0px -50% 0px" });
      map.forEach((_, id) => { const s = document.getElementById(id); if (s) io.observe(s); });
    }
  })();

  // ------------------------------------------------------- hero bracket
  (function hero() {
    const host = $("#hero-bracket");
    const callsEl = $("#hero-calls");
    let timers = [];
    function play() {
      timers.forEach(clearTimeout);
      timers = [];
      const q = SAMPLE.map((r) => r.quality);
      const res = A.run("single_elimination", q, { seed: 0, noise: 0 });
      const bracket = res.trace.filter((m) => m.stage === "bracket");
      const rounds = [...new Set(bracket.map((m) => m.round))];
      const seeding = res.trace.filter((m) => m.stage === "seeding").length;
      const titles = ["Quarterfinal", "Semifinal", "Final", "Champion"];
      host.innerHTML = "";
      const cols = [];
      rounds.forEach((r, k) => {
        const col = document.createElement("div");
        col.className = "col";
        col.innerHTML = `<div class="col-title">${titles[k] || "Round " + r}</div><div class="col-body"></div>`;
        const body = col.lastElementChild;
        bracket.filter((m) => m.round === r).forEach((m) => {
          [m.a, m.b].forEach((p) => {
            if (p === null) return;
            const s = document.createElement("div");
            s.className = "slot";
            s.dataset.p = p;
            s.dataset.round = r;
            s.dataset.win = m.winner === p ? "1" : "0";
            s.innerHTML = `<span class="dot"></span>${SAMPLE[p].id}<span class="q">${SAMPLE[p].quality.toFixed(1)}</span>`;
            body.appendChild(s);
          });
        });
        host.appendChild(col);
        cols.push(col);
      });
      const champ = document.createElement("div");
      champ.className = "col";
      const c = res.order[0];
      champ.innerHTML = `<div class="col-title">${titles[rounds.length] || "Champion"}</div><div class="col-body"><div class="slot champ" data-final="1"><span class="dot"></span>${SAMPLE[c].id}<span class="q">${SAMPLE[c].quality.toFixed(1)}</span></div></div>`;
      host.appendChild(champ);
      cols.push(champ);

      const step = reduceMotion ? 0 : 650;
      let calls = seeding;
      callsEl.textContent = `${calls} seeding calls`;
      cols.forEach((col, k) => {
        timers.push(setTimeout(() => {
          $$(".slot", col).forEach((s) => s.classList.add("in"));
          if (k > 0) {
            $$(".slot", cols[k - 1]).forEach((s) => s.classList.add(s.dataset.win === "1" ? "won" : "lost"));
            calls += bracket.filter((m) => m.round === rounds[k - 1] && m.b !== null).length;
            callsEl.textContent = `${calls} judge calls`;
          }
        }, 150 + k * step * 1.4));
      });
    }
    $("#hero-replay").addEventListener("click", play);
    play();
  })();

  // ------------------------------------------- pointwise vs tournament
  (function contrast() {
    // Fine-grained hidden qualities; a pointwise judge only emits integers.
    const hidden = [6.8, 7.9, 7.1, 6.9, 8.3, 7.0, 6.2, 7.6];
    const pointwise = hidden.map((h) => Math.round(h));
    const advPoint = A.normalize(pointwise);
    const tour = A.run("round_robin", hidden, { noise: 0 });
    function bars(host, adv) {
      const max = Math.max(...adv.map(Math.abs), 1e-9);
      host.innerHTML = adv.map((v, i) => {
        const w = (Math.abs(v) / max) * 50;
        return `<div class="bar-row"><span>R${i}</span><span class="bar-track"><span class="bar-fill ${v >= 0 ? "pos" : "neg"}" style="width:${w}%"></span></span><span class="v">${v >= 0 ? "+" : ""}${v.toFixed(2)}</span></div>`;
      }).join("");
    }
    const distinct = (xs) => new Set(xs.map((v) => v.toFixed(4))).size;
    bars($("#contrast-point"), advPoint);
    bars($("#contrast-tour"), tour.rewards);
    $("#contrast-point-cap").textContent = `Scores ${pointwise.join(", ")}: only ${distinct(advPoint)} distinct advantage values, so many rollouts get identical credit.`;
    $("#contrast-tour-cap").textContent = `${tour.calls} pairwise comparisons: ${distinct(tour.rewards)} distinct advantage values, one per rollout.`;
  })();

  // ------------------------------------------------------------ simulator
  const sim = (function simulator() {
    const state = { method: "single_elimination", data: "sample", size: 8, noise: 0, seed: 0, view: "standings" };
    const seg = $("#method-seg");
    seg.innerHTML = A.METHODS.map((m) => `<button type="button" data-method="${m}" aria-pressed="${m === state.method}">${A.LABELS[m]}<span id="cost-${m}"></span></button>`).join("");

    function qualities() {
      if (state.data === "sample") return SAMPLE.map((r) => r.quality);
      const rand = A.mulberry32(state.seed * 31 + 17);
      return Array.from({ length: state.size }, () => Math.round((1 + rand() * 9) * 10) / 10);
    }
    function label(i) {
      return state.data === "sample" ? SAMPLE[i] : { id: "R" + i, summary: "" };
    }
    function updateCosts() {
      const n = state.data === "sample" ? 8 : state.size;
      A.METHODS.forEach((m) => {
        const c = A.expectedCalls(m, n);
        $("#cost-" + m).textContent = c === null ? `~${2 * n - 2} calls` : `${c} calls`;
      });
    }

    function scoreHeader(m) {
      return { anchor: "Score vs anchor", round_robin: "Wins", swiss: "Points (Buchholz)", double_elimination: "Avg judge score", single_elimination: "Avg judge score" }[m];
    }

    function render(res, q) {
      const n = q.length;
      // KPIs
      const best = Math.max(...q);
      const topReward = Math.max(...res.rewards);
      const bestIdx = q.map((v, i) => (v === best ? i : -1)).filter((i) => i >= 0);
      const topOk = bestIdx.some((i) => Math.abs(res.rewards[i] - topReward) < 1e-9);
      $("#kpi-calls").textContent = res.calls;
      $("#kpi-tau").textContent = fmt(A.kendallTau(res.rewards, q));
      $("#kpi-top").textContent = topOk ? "Yes" : "No";
      $("#kpi-spread").textContent = `${new Set(res.rewards.map((v) => v.toFixed(4))).size} / ${n}`;
      $("#kpi-spread").previousElementSibling.textContent = "Distinct reward levels";

      // standings
      $("#score-col").textContent = scoreHeader(res.method);
      const scoreOf = {};
      (res.standings || []).forEach((s) => (scoreOf[s.idx] = s));
      const order = q.map((_, i) => i).sort((a, b) => res.rewards[b] - res.rewards[a] || a - b);
      const maxAbs = Math.max(...res.rewards.map(Math.abs), 1e-9);
      let rank = 0;
      let prev = null;
      $("#standings tbody").innerHTML = order.map((i, k) => {
        if (prev === null || Math.abs(res.rewards[i] - prev) > 1e-9) rank = k + 1;
        prev = res.rewards[i];
        const s = scoreOf[i];
        let score = "–";
        if (s) score = res.method === "swiss" ? `${s.score} (${s.buchholz})` : fmt(s.score, res.method === "round_robin" ? 1 : 2);
        const r = res.rewards[i];
        const w = (Math.abs(r) / maxAbs) * 50;
        const L = label(i);
        return `<tr><td><span class="rank-badge ${rank === 1 ? "first" : ""}">${rank}</span></td>
          <td><span class="rid">${esc(L.id)}</span>${L.summary ? `<span class="rdesc">${esc(L.summary)}</span>` : ""}</td>
          <td class="num">${q[i].toFixed(1)}</td><td class="num">${score}</td>
          <td><div class="adv"><span class="bar-track"><span class="bar-fill ${r >= 0 ? "pos" : "neg"}" style="width:${w}%"></span></span><span class="num">${r >= 0 ? "+" : ""}${r.toFixed(2)}</span></div></td></tr>`;
      }).join("");

      // matches
      const host = $("#panel-matches");
      if (res.method === "round_robin") {
        const cell = {};
        res.trace.forEach((m) => {
          const ra = m.winner === null ? "t" : m.winner === m.a ? "w" : "l";
          const rb = m.winner === null ? "t" : m.winner === m.b ? "w" : "l";
          cell[m.a + "," + m.b] = ra;
          cell[m.b + "," + m.a] = rb;
        });
        let h = '<div class="table-scroll"><table class="matrix" aria-label="Round-robin results, row versus column"><tr><th></th>' + q.map((_, j) => `<th scope="col">${esc(label(j).id)}</th>`).join("") + "</tr>";
        q.forEach((_, i) => {
          h += `<tr><th scope="row">${esc(label(i).id)}</th>` + q.map((__, j) => {
            if (i === j) return '<td class="cell-x"></td>';
            const c = cell[i + "," + j];
            const txt = { w: "W", l: "L", t: "=" }[c];
            return `<td class="cell-${c}" title="${esc(label(i).id)} vs ${esc(label(j).id)}: ${txt}">${txt}</td>`;
          }).join("") + "</tr>";
        });
        h += '</table></div><div class="legend"><span><i class="cell-w"></i>row wins</span><span><i class="cell-l"></i>row loses</span><span><i class="cell-t"></i>tie (half point each)</span></div>';
        host.innerHTML = h;
      } else {
        const groups = [];
        const key = (m) => m.stage + "|" + m.round;
        res.trace.forEach((m) => {
          let g = groups.find((x) => x.key === key(m));
          if (!g) { g = { key: key(m), title: groupTitle(res.method, m), items: [] }; groups.push(g); }
          g.items.push(m);
        });
        host.innerHTML = '<div class="rounds">' + groups.map((g) => `<div class="round"><h4>${esc(g.title)}</h4>` + g.items.map(matchCard).join("") + "</div>").join("") + "</div>" +
          (res.method === "anchor" ? '<p class="muted" style="font-size:.85rem;margin-top:10px">Every rollout is judged once against R0. R0\'s own score is the mean of the scores it received.</p>' : "");
      }
    }
    function groupTitle(method, m) {
      if (method === "anchor") return "Against anchor R0";
      if (method === "swiss") return "Round " + m.round;
      if (method === "single_elimination") return m.stage === "seeding" ? "Seeding vs R0" : "Bracket round " + m.round;
      if (method === "double_elimination") return (m.stage === "winners" ? "Winners' bracket" : m.stage === "losers" ? "Losers' bracket" : "Grand final") + " · r" + m.round;
      return m.stage;
    }
    function matchCard(m) {
      if (m.bye) return `<div class="m bye"><div><span>${esc(label(m.a).id)}</span><span class="s">bye</span></div></div>`;
      const row = (p, s) => `<div class="${m.winner === p ? "w" : ""}"><span>${esc(label(p).id)}</span><span class="s">${s.toFixed(2)}</span></div>`;
      return `<div class="m">${row(m.a, m.sa)}${row(m.b, m.sb)}</div>`;
    }

    function run() {
      const q = qualities();
      const res = A.run(state.method, q, { seed: state.seed, noise: state.noise });
      render(res, q);
      return res;
    }

    function compare() {
      const n = state.data === "sample" ? 8 : state.size;
      const trials = n > 10 ? 150 : 300;
      $("#cmp-trials").textContent = trials;
      const rand = A.mulberry32(state.seed * 7 + 3);
      const stats = Object.fromEntries(A.METHODS.map((m) => [m, { tau: 0, top: 0, calls: 0 }]));
      for (let t = 0; t < trials; t++) {
        const q = Array.from({ length: n }, () => 1 + rand() * 9);
        const best = q.indexOf(Math.max(...q));
        A.METHODS.forEach((m) => {
          const res = A.run(m, q, { seed: state.seed * 1000 + t, noise: state.noise });
          const s = stats[m];
          s.tau += A.kendallTau(res.rewards, q);
          s.top += res.rewards[best] >= Math.max(...res.rewards) - 1e-9 ? 1 : 0;
          s.calls += res.calls;
        });
      }
      const rows = A.METHODS.map((m) => ({ m, tau: stats[m].tau / trials, top: stats[m].top / trials, calls: stats[m].calls / trials }));
      $("#compare-out").innerHTML =
        `<p class="muted" style="font-size:.88rem">Group size ${n}, judge noise ${state.noise.toFixed(1)}, ${trials} groups. Bar: mean Kendall τ between rewards and hidden quality.</p>` +
        '<div class="compare-bars">' + rows.map((r) => `<div class="cmp-row"><span>${A.LABELS[r.m]}</span><span class="cmp-track"><span class="cmp-fill" style="width:${Math.max(0, r.tau) * 100}%"></span><span>τ ${r.tau.toFixed(2)}</span></span></div>`).join("") + "</div>" +
        '<div class="table-scroll" style="margin-top:16px"><table><thead><tr><th>Topology</th><th class="num">Mean τ</th><th class="num">Best ranked first</th><th class="num">Judge calls / group</th></tr></thead><tbody>' +
        rows.map((r) => `<tr><td>${A.LABELS[r.m]}</td><td class="num">${r.tau.toFixed(3)}</td><td class="num">${(r.top * 100).toFixed(0)}%</td><td class="num">${r.calls.toFixed(1)}</td></tr>`).join("") +
        "</tbody></table></div>";
    }

    // wiring
    seg.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-method]");
      if (!b) return;
      state.method = b.dataset.method;
      $$("button", seg).forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
      run();
    });
    $("#data-seg").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-data]");
      if (!b) return;
      state.data = b.dataset.data;
      $$("#data-seg button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
      $("#size-field").hidden = state.data === "sample";
      $("#data-hint").innerHTML = state.data === "sample"
        ? "8 trip-planning rollouts from <code>python -m qqr.demo</code>."
        : "Hidden qualities drawn uniformly from 1–10 using the seed.";
      updateCosts();
      run();
    });
    const size = $("#group-size");
    size.addEventListener("input", () => { state.size = +size.value; $("#group-size-out").textContent = size.value; updateCosts(); run(); });
    const noise = $("#noise");
    noise.addEventListener("input", () => { state.noise = +noise.value; $("#noise-out").textContent = (+noise.value).toFixed(1); run(); });
    const seed = $("#seed");
    seed.addEventListener("change", () => {
      let v = Math.floor(Number(seed.value));
      if (!Number.isFinite(v) || v < 0) v = 0;
      if (v > 999999) v = 999999;
      seed.value = v;
      state.seed = v;
      run();
    });
    $("#run-btn").addEventListener("click", () => { run(); toast(`${A.LABELS[state.method]}: ranked ${state.data === "sample" ? 8 : state.size} rollouts`); });
    $("#reseed-btn").addEventListener("click", () => { state.seed = Math.floor(Math.random() * 100000); seed.value = state.seed; run(); });
    $("#compare-btn").addEventListener("click", compare);
    setupTablist($('[aria-label="Simulator views"]'), (tab) => {
      ["standings", "matches", "compare"].forEach((v) => ($("#panel-" + v).hidden = tab.id !== "tab-" + v));
    });

    updateCosts();
    run();
    return { run, compare, state };
  })();
  window.__qqrSim = sim; // exposed for automated browser tests

  // ------------------------------------------------------------- workflow
  (function workflow() {
    const FLOWS = {
      arena: [
        { t: "Sample queries", s: "Prompts from data/*.jsonl", body: "slime draws a batch of prompts (16 per step in the travel recipe). Each prompt is an open-ended request such as planning a multi-day trip.", where: "scripts/travel/run-qwen3-8B.sh · --rollout-batch-size 16" },
        { t: "Roll out a group", s: "G trajectories per query, with tools", body: "For every query the policy produces a group of trajectories (16 in the travel recipe). Each trajectory is a multi-turn conversation where the model calls MCP tools such as map search or transport lookup, and qqr parses Qwen tool calls and feeds tool results back.", where: "qqr/rollout/agent_rollout.py · qqr/mcp/" },
        { t: "Play the tournament", s: "Pairwise LLM judge", body: "The group is handed to an arena reward model. An LLM judge compares two trajectories at a time (in both orders for the travel judge) and returns a score for each. The topology decides which pairs meet.", formula: "judge(τ_a, τ_b, query) → {prediction, reference}", where: "qqr/reward_models/arena/ · qqr/examples/travel/reward_model.py" },
        { t: "Turn standings into rewards", s: "Rank, then group-normalise", body: "Final standings become linear rank rewards in [0, 1] (ties share their average), which are z-scored within the group so every query contributes a zero-mean, unit-variance signal.", formula: "r_i = (R − rank_i) / (R − 1);   A_i = (r_i − mean r) / (std r + 1e-6)", where: "qqr/reward_models/arena/_common.py" },
        { t: "Update the policy", s: "GRPO in slime", body: "The advantages flow back to slime, which runs the GRPO policy-gradient update on Megatron and syncs the new weights to the sglang rollout engines for the next step.", where: "--advantage-estimator grpo · --custom-rm-path qqr.examples.travel.group_reward" },
      ],
      arise: [
        { t: "Generator proposes tasks", s: "Tasks + rubrics grounded in tools", body: "The Generator writes a new task together with a grading rubric. Tool-related rubric items are grounded in real tool observations, so the rubric reflects what the environment actually returns.", where: "qqr/examples/arise_rl_generator/" },
        { t: "Solver attempts each task", s: "K = 8 frozen-solver attempts", body: "A separately served Solver (the executor service) attempts each generated task K times. Its success rate measures how hard the task is right now.", where: "scripts/arise_rl_generator/*/start_executor_server.sh" },
        { t: "Difficulty-shaped Generator reward", s: "Peaks near 50% Solver success", body: "R_tool and R_fmt are 0/1 gates for real tool grounding and a well-formed task. R_diff is a triangular bonus that peaks when c, the number of Solver attempts scoring at least γ = 0.9, is K/2, so generated tasks track the Solver's ability boundary.", formula: "R_G = R_tool · R_fmt · (1 + R_diff),   R_diff = 2 · max(0, 1 − |c − K/2| / (K/2))", where: "qqr/examples/arise_rl_generator/*/reward_model.py" },
        { t: "Solver learns from rubrics", s: "Fine-grained satisfaction reward", body: "The Solver is trained with G = 16 rollouts per query on rubric satisfaction s ∈ [0, 1], with a bonus for fully satisfying the rubric.", formula: "r = 0.8 · s + 0.2 · 𝟙[s = 1]", where: "qqr/examples/arise_rl_solver/" },
        { t: "Reward-gated self-distillation", s: "RG-SED", body: "The same policy, conditioned on coach memory, acts as a transient teacher. Token-level reverse-KL distillation is applied only when that memory actually improved reward, via a sigmoid gate on the reward gain (λ₀ = 0.5, τ = 0.05).", formula: "λ = λ₀ · σ((Δr − τ) / T) · warmup · decay", where: "patches/slime-rg-sed-v0.3.1.patch · qqr/examples/arise_rl_solver/*/rollout.py" },
      ],
      rti: [
        { t: "Roll out a group", s: "G = 8 on-policy trajectories", body: "As in GRPO, the policy produces a group of trajectories and the task's official grader scores them (navigation, τ²-bench, Claw-Eval).", where: "qqr/off_policy/group_rollout.py" },
        { t: "Detect an all-fail group", s: "Intervene only when nothing succeeded", body: "If at least one rollout succeeds the group is used as-is, so training reduces exactly to GRPO. Only when every rollout fails does the intervention pipeline run.", where: "qqr/off_policy/group_rollout.py" },
        { t: "Judge, correct, post-check", s: "Agents instantiated with the policy", body: "A Validity Judge locates the decisive error using reward-side evidence, a Corrector writes a minimal rewrite of that step, a de-leak pass removes references to hidden answers, and a Post-Check verifies integrity. The repaired trajectory replaces a failed sample.", where: "qqr/off_policy/rti/pipeline.py · qqr/off_policy/rti/agents/" },
        { t: "Perplexity gate", s: "Drop large distribution shifts", body: "Intervened responses are off-policy. Any whose perplexity under the rollout policy exceeds δ is discarded (δ = 5 for navigation, 20 for τ²-bench and Claw-Eval).", formula: "keep ũ  iff  PPL_roll(ũ) ≤ δ", where: "qqr/off_policy/rti/utils/metrics.py" },
        { t: "Reweight corrected tokens", s: "Reasoning-shift-aware TIS", body: "Only the intervened tokens get an importance weight, the likelihood ratio between the calibration and rollout policies, clipped to [0.8, 1.2], so updates focus on the decisive correction.", formula: "w = clip(π_cal / π_roll, 1 − ε, 1 + ε)", where: "qqr/reward_models/utils.py · reshape_gt_tis_function" },
      ],
    };
    let flow = "arena";
    let idx = 0;
    const list = $("#flow-steps");
    const detail = $("#flow-detail");
    function draw() {
      const steps = FLOWS[flow];
      list.innerHTML = steps.map((s, i) => `<li><button type="button" data-i="${i}" ${i === idx ? 'aria-current="step"' : ""}><span class="n">${i + 1}</span><span>${esc(s.t)}<small>${esc(s.s)}</small></span></button></li>`).join("");
      const s = steps[idx];
      detail.innerHTML = `<h3>${esc(s.t)}</h3><p>${esc(s.body)}</p>${s.formula ? `<div class="formula">${esc(s.formula)}</div>` : ""}<p class="where">In the code: <code>${esc(s.where)}</code></p>
        <div class="step-nav"><button type="button" class="btn btn-ghost" data-go="-1" ${idx === 0 ? "disabled" : ""}>Previous step</button><button type="button" class="btn btn-primary" data-go="1" ${idx === steps.length - 1 ? "disabled" : ""}>Next step</button></div>`;
    }
    list.addEventListener("click", (e) => { const b = e.target.closest("button[data-i]"); if (b) { idx = +b.dataset.i; draw(); } });
    detail.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-go]");
      if (!b) return;
      idx = Math.min(Math.max(0, idx + +b.dataset.go), FLOWS[flow].length - 1);
      draw();
      const cur = $(`button[data-i="${idx}"]`, list);
      if (cur) cur.focus({ preventScroll: true });
    });
    setupTablist($("#flow-tabs"), (tab) => { flow = tab.dataset.flow; idx = 0; draw(); });
    draw();
  })();

  // --------------------------------------------------------- architecture
  (function architecture() {
    const NODES = {
      trainer: { t: "Megatron trainer (slime)", d: "Runs the GRPO policy update on the training GPUs. For ARISE-RL, the RG-SED patch adds reward-gated reverse-KL self-distillation.", p: "patches/slime-rg-sed-v0.3.1.patch" },
      sglang: { t: "sglang rollout engines (slime)", d: "Serve the current policy behind a router. qqr's rollout sends /generate requests here, token by token, for every agent turn.", p: "qqr/rollout/agent_rollout.py · get_model_url" },
      data: { t: "Prompt data", d: "JSONL files of queries (and labels or rubrics where a benchmark has them), loaded by slime's dataset reader.", p: "data/" },
      rollout: { t: "Agent rollout", d: "The multi-turn loop: generate, parse Qwen3 / Qwen3.5 tool calls, call tools through MCP, append observations, repeat until an answer or the turn limit. Groups are then scored together.", p: "qqr/rollout/agent_rollout.py · qqr/data/prompts/" },
      mcp: { t: "MCP layer", d: "Wraps openai-agents MCP servers with a TTL result cache, a per-server concurrency limit, a tool blocklist, and warnings for missing credentials.", p: "qqr/mcp/server.py" },
      arena: { t: "Arena reward models", d: "Anchor, round-robin, Swiss, double and seeded single elimination. Each turns pairwise judge results into group-normalised rewards.", p: "qqr/reward_models/arena/" },
      rti: { t: "Off-policy RTI and ARISE-RL", d: "RTI's two-stage group rollout and intervention agents, the async training entry point, and ARISE-RL's Generator / Solver examples with coach memory.", p: "qqr/off_policy/ · qqr/examples/arise_rl_*" },
      tools: { t: "MCP tool servers", d: "Stdio servers shipped in qqr/tools: AMap and navigation, web search, mock transport, τ²-bench domains and Claw-Eval mock services. Any MCP server can be added.", p: "qqr/tools/" },
      judge: { t: "LLM judge API", d: "Any OpenAI-compatible endpoint (DashScope, OpenAI, or a self-hosted sglang / vLLM server) used for pairwise judging, rubric grading, coaches and RTI inspectors.", p: "qqr/llms/openai.py · .env.example" },
    };
    const info = $("#arch-info");
    const show = (k) => {
      const n = NODES[k];
      info.innerHTML = `<div><h3>${esc(n.t)}</h3><p>${esc(n.d)}</p></div><code>${esc(n.p)}</code>`;
      $$(".arch .node").forEach((g) => g.classList.toggle("active", g.dataset.node === k));
      $$("#arch-mobile button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.node === k ? "true" : "false"));
    };
    $$(".arch .node").forEach((g) => {
      g.setAttribute("role", "button");
      g.setAttribute("aria-label", NODES[g.dataset.node].t);
      g.addEventListener("click", () => show(g.dataset.node));
      g.addEventListener("focus", () => show(g.dataset.node));
      g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); show(g.dataset.node); } });
    });
    const mob = $("#arch-mobile");
    const groups = [["slime (GPU cluster)", ["trainer", "sglang", "data"]], ["qqr", ["rollout", "mcp", "arena", "rti"]], ["External services", ["tools", "judge"]]];
    mob.innerHTML = groups.map(([g, ks]) => `<div role="listitem" style="margin-bottom:12px"><div class="muted" style="font-size:.85rem;font-weight:600;margin-bottom:6px">${g}</div><div class="seg">${ks.map((k) => `<button type="button" data-node="${k}" aria-pressed="false">${esc(NODES[k].t)}</button>`).join("")}</div></div>`).join("");
    mob.addEventListener("click", (e) => { const b = e.target.closest("button[data-node]"); if (b) show(b.dataset.node); });
    show("arena");
  })();

  // --------------------------------------------------------------- papers
  (function papers() {
    const P = [
      {
        y: "2026", v: "ICML 2026", t: "ArenaRL: Scaling RL for Open-Ended Agents via Tournament-based Relative Ranking",
        a: "Qiang Zhang, Boli Chen, Fanrui Zhang, Ruixue Ding, et al.",
        links: [["arXiv", "https://arxiv.org/abs/2601.06487"], ["Hugging Face", "https://huggingface.co/papers/2601.06487"], ["Blog", "https://tongyi-agent.github.io/blog/arenarl/"]],
        bib: "@misc{zhang2026arenarlscalingrlopenended,\n  title={ArenaRL: Scaling RL for Open-Ended Agents via Tournament-based Relative Ranking},\n  author={Qiang Zhang and Boli Chen and Fanrui Zhang and Ruixue Ding and Shihang Wang and Qiuchen Wang and Yinfeng Huang and Haonan Zhang and Rongxiang Zhu and Pengyong Wang and Ailin Ren and Xin Li and Pengjun Xie and Jiawei Liu and Ning Guo and Jingren Zhou and Zheng-Jun Zha},\n  year={2026},\n  eprint={2601.06487},\n  archivePrefix={arXiv},\n  primaryClass={cs.LG},\n  url={https://arxiv.org/abs/2601.06487},\n}",
      },
      {
        y: "2026", v: "arXiv", t: "ARISE-RL: Agentic Rubric-Grounded Iterative Self-Evolution with Reinforcement Learning",
        a: "Fanrui Zhang, Ruixue Ding, Qiang Zhang, Xi Chen, Boli Chen, et al.",
        links: [["arXiv", "https://arxiv.org/abs/2609.01058"]],
        bib: "@misc{zhang2026ariserl,\n  title={ARISE-RL: Agentic Rubric-Grounded Iterative Self-Evolution with Reinforcement Learning},\n  author={Zhang, Fanrui and Ding, Ruixue and Zhang, Qiang and Chen, Xi and Chen, Boli and Wang, Shihang and Wang, Qiuchen and Zhan, Hongmin and Bian, Jinxin and Li, Xingchao and Zheng, Peijin and Cheng, Hao and Xie, Pengjun and Zhang, Kaipeng and Liu, Jiawei and Zha, Zheng-Jun},\n  year={2026},\n  eprint={2609.01058},\n  archivePrefix={arXiv},\n  primaryClass={cs.AI}\n}",
      },
      {
        y: "2026", v: "arXiv", t: "Rollout-Time Intervention: Unlocking Agentic Reinforcement Learning Beyond Policy Limits",
        a: "Xi Chen, Ruixue Ding, Zhigaoyuan Wang, Fanrui Zhang, Qiang Zhang, Boli Chen, et al.",
        links: [["arXiv", "https://arxiv.org/abs/2610.13438"]],
        bib: "@misc{chen2026rollouttimeinterventionunlockingagentic,\n  title={Rollout-Time Intervention: Unlocking Agentic Reinforcement Learning Beyond Policy Limits},\n  author={Xi Chen and Ruixue Ding and Zhigaoyuan Wang and Fanrui Zhang and Qiang Zhang and Boli Chen and Shihang Wang and Tianfu Wang and Ailin Ren and Pengyong Wang and Pengjun Xie and Hui Xiong},\n  year={2026},\n  eprint={2610.13438},\n  archivePrefix={arXiv},\n  primaryClass={cs.AI},\n  url={https://arxiv.org/abs/2610.13438},\n}",
      },
      {
        y: "2026", v: "arXiv", t: "SecRespond: Benchmarking AI Agents for Real-World Post-Compromise Incident Response",
        a: "Lehan Wang, Boli Chen, Ruixue Ding, Pengjun Xie, et al.",
        links: [["arXiv", "https://arxiv.org/abs/2607.26791"], ["Dataset", "https://huggingface.co/datasets/Alibaba-NLP/SecRespond"]],
        bib: "@article{wang2026secrespond,\n  title={SecRespond: Benchmarking AI Agents for Real-World Post-Compromise Incident Response},\n  author={Wang, Lehan and Chen, Boli and Ding, Ruixue and Xie, Pengjun and Huang, Jinwei and Liu, Zhendong and Wang, Shuo and Lei, Tao and Ouyang, Xin and Li, Xiaomeng},\n  journal={arXiv preprint arXiv:2607.26791},\n  year={2026}\n}",
      },
    ];
    const host = $("#papers-list");
    host.innerHTML = P.map((p, i) => `<article class="paper"><div class="yr">${p.y}<small>${esc(p.v)}</small></div>
      <div><h3>${esc(p.t)}</h3><p>${esc(p.a)}</p></div>
      <div class="links">${p.links.map(([l, u]) => `<a class="btn btn-ghost" href="${u}">${esc(l)}</a>`).join("")}<button type="button" class="btn btn-ghost" data-bib="${i}">Copy BibTeX</button></div></article>`).join("");
    host.addEventListener("click", (e) => { const b = e.target.closest("button[data-bib]"); if (b) copyText(P[+b.dataset.bib].bib); });
  })();

  // ------------------------------------------------------- copy buttons
  $$(".code .copy").forEach((b) => b.addEventListener("click", () => copyText(b.nextElementSibling.innerText)));
})();
