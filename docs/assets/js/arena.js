/*
 * ArenaRL tournament logic for the browser.
 *
 * A line-by-line JavaScript port of qqr/reward_models/arena/*.py so the
 * website simulator runs the same ranking rules as the Python package.
 * tests/test_web_parity.py runs this file under Node and checks that, for the
 * deterministic methods (anchor, round-robin, single elimination), it produces
 * the same rewards as Python for the same judge outcomes; Swiss and double
 * elimination draw random pairings, so they are checked on invariants.
 *
 * The judge here is synthetic (hidden quality + optional seeded noise). It is
 * not a language model and nothing in this file trains or evaluates a model.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Arena = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const EPS = 1e-6;
  const METHODS = ["anchor", "round_robin", "swiss", "double_elimination", "single_elimination"];
  const LABELS = {
    anchor: "Anchor-based",
    round_robin: "Round-robin",
    swiss: "Swiss system",
    double_elimination: "Double elimination",
    single_elimination: "Seeded single elimination",
  };

  // ---------------------------------------------------------------- RNG
  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function shuffleInPlace(arr, rand) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }
  function gauss(rand) {
    let u = 0;
    while (u === 0) u = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand());
  }

  // ------------------------------------------------------- shared helpers
  const mean = (xs) => xs.reduce((s, v) => s + v, 0) / xs.length;

  function rankMinDescending(values) {
    return values.map((v) => 1 + values.filter((o) => o > v).length);
  }
  function rankBasedRewards(ranks) {
    if (!ranks.length) return [];
    const maxRank = Math.max(...ranks);
    if (maxRank === 1) return ranks.map(() => 0);
    return ranks.map((r) => (maxRank - r) / (maxRank - 1));
  }
  function positionRewards(rankedIdx, n) {
    const out = new Array(n).fill(0);
    if (n < 2) return out;
    rankedIdx.forEach((p, k) => (out[p] = 1 - k / (n - 1)));
    return out;
  }
  function normalize(rewards) {
    const n = rewards.length;
    if (n < 2) return rewards.map(() => 0);
    const m = mean(rewards);
    const sd = Math.sqrt(rewards.reduce((s, v) => s + (v - m) ** 2, 0) / (n - 1));
    return rewards.map((v) => (v - m) / (sd + EPS));
  }
  function stableSortDesc(arr, key) {
    // Array.prototype.sort is stable (ES2019), matching Python's sorted().
    return arr.sort((a, b) => key(b) - key(a));
  }

  // --------------------------------------------------------------- judge
  /**
   * Synthetic pairwise judge. ``qualities[i]`` is rollout i's hidden quality;
   * each call returns {prediction, reference} like qqr's LLM judges.
   */
  function makeJudge(qualities, opts = {}) {
    const noise = opts.noise || 0;
    const rand = mulberry32(opts.seed == null ? 1 : opts.seed + 7919);
    const judge = function (i, j) {
      judge.calls += 1;
      const a = qualities[i] + (noise ? noise * gauss(rand) : 0);
      const b = qualities[j] + (noise ? noise * gauss(rand) : 0);
      return { prediction: a, reference: b };
    };
    judge.calls = 0;
    return judge;
  }

  function match(judge, i, j, round, stage) {
    const r = judge(i, j);
    const sa = Number(r.prediction);
    const sb = Number(r.reference);
    return { a: i, b: j, sa, sb, round, stage: stage || "" };
  }

  // ------------------------------------------------------------- anchor
  function anchor(n, judge) {
    const trace = [];
    if (n < 2) return { rewards: new Array(n).fill(0), trace, standings: [] };
    const pivotScores = new Array(n).fill(5.0);
    const otherScores = new Array(n).fill(5.0);
    for (let idx = 1; idx < n; idx++) {
      const m = match(judge, idx, 0, 1, "vs anchor");
      m.winner = m.sa > m.sb ? m.a : m.sb > m.sa ? m.b : null;
      trace.push(m);
      otherScores[idx] = m.sa;
      pivotScores[idx] = m.sb;
    }
    const scores = [mean(pivotScores.slice(1))].concat(otherScores.slice(1));
    const ranks = rankMinDescending(scores);
    const raw = rankBasedRewards(ranks);
    return {
      rewards: normalize(raw),
      raw,
      trace,
      standings: scores.map((s, i) => ({ idx: i, score: s, rank: ranks[i] })),
    };
  }

  // -------------------------------------------------------- round robin
  function roundRobin(n, judge) {
    const trace = [];
    if (n < 2) return { rewards: new Array(n).fill(0), trace, standings: [] };
    const wins = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const m = match(judge, i, j, 1, "round robin");
        if (m.sa > m.sb) { wins[i] += 1; m.winner = i; }
        else if (m.sb > m.sa) { wins[j] += 1; m.winner = j; }
        else { wins[i] += 0.5; wins[j] += 0.5; m.winner = null; }
        trace.push(m);
      }
    }
    const ranks = rankMinDescending(wins);
    const raw = rankBasedRewards(ranks);
    return {
      rewards: normalize(raw),
      raw,
      trace,
      standings: wins.map((w, i) => ({ idx: i, score: w, rank: ranks[i] })),
    };
  }

  // -------------------------------------------------------------- swiss
  function swiss(n, judge, opts = {}) {
    const trace = [];
    if (n < 2) return { rewards: new Array(n).fill(0), trace, standings: [] };
    const rand = mulberry32(opts.seed == null ? 1 : opts.seed);
    let rounds = opts.maxRounds > 0 ? opts.maxRounds : Math.ceil(Math.log2(n));
    rounds = Math.min(rounds, n - 1);
    const players = Array.from({ length: n }, (_, i) => ({ idx: i, points: 0, opponents: new Set(), buchholz: 0 }));
    for (let r = 1; r <= rounds; r++) {
      const shuffled = shuffleInPlace(players.slice(), rand);
      const sorted = stableSortDesc(shuffled, (p) => p.points);
      const unpaired = sorted.slice();
      let bye = null;
      if (unpaired.length % 2 !== 0) bye = unpaired.pop().idx;
      const processed = new Array(unpaired.length).fill(false);
      const pairings = [];
      for (let i = 0; i < unpaired.length; i++) {
        if (processed[i]) continue;
        const p1 = unpaired[i];
        let found = false;
        for (let j = i + 1; j < unpaired.length; j++) {
          if (!processed[j] && !p1.opponents.has(unpaired[j].idx)) {
            pairings.push([p1.idx, unpaired[j].idx]);
            processed[i] = processed[j] = true;
            found = true;
            break;
          }
        }
        if (!found) {
          for (let j = i + 1; j < unpaired.length; j++) {
            if (!processed[j]) {
              pairings.push([p1.idx, unpaired[j].idx]);
              processed[i] = processed[j] = true;
              break;
            }
          }
        }
      }
      for (const [i, j] of pairings) {
        const m = match(judge, i, j, r, "round " + r);
        if (m.sa > m.sb) { players[i].points += 1; m.winner = i; }
        else if (m.sb > m.sa) { players[j].points += 1; m.winner = j; }
        else { players[i].points += 0.5; players[j].points += 0.5; m.winner = null; }
        players[i].opponents.add(j);
        players[j].opponents.add(i);
        trace.push(m);
      }
      if (bye !== null) {
        players[bye].points += 1;
        trace.push({ a: bye, b: null, round: r, stage: "round " + r, bye: true, winner: bye });
      }
    }
    for (const p of players) {
      p.buchholz = [...p.opponents].reduce((s, o) => s + players[o].points, 0);
    }
    const ranked = stableSortDesc(players.slice(), (p) => p.points * 1e6 + p.buchholz);
    const raw = new Array(n).fill(0);
    let i = 0;
    while (i < n) {
      let j = i;
      while (j + 1 < n && ranked[j + 1].points === ranked[i].points && ranked[j + 1].buchholz === ranked[i].buchholz) j++;
      let sum = 0;
      for (let k = i; k <= j; k++) sum += (n - (k + 1)) / (n - 1);
      for (let k = i; k <= j; k++) raw[ranked[k].idx] = sum / (j - i + 1);
      i = j + 1;
    }
    return {
      rewards: normalize(raw),
      raw,
      trace,
      rounds,
      standings: players.map((p) => ({ idx: p.idx, score: p.points, buchholz: p.buchholz })),
    };
  }

  // -------------------------------------------- elimination shared bits
  const newPlayer = (i) => ({ idx: i, points: [] });
  const avg = (p) => (p.points.length ? mean(p.points) : 0);

  // -------------------------------------------------- single elimination
  function singleElimination(n, judge) {
    const trace = [];
    if (n < 2) return { rewards: new Array(n).fill(0), trace, standings: [] };
    const players = Array.from({ length: n }, (_, i) => newPlayer(i));
    // seeding: anchor pass against rollout 0
    const pivotScores = [];
    for (let idx = 1; idx < n; idx++) {
      const m = match(judge, idx, 0, 0, "seeding");
      m.winner = m.sa > m.sb ? m.a : m.sb > m.sa ? m.b : null;
      trace.push(m);
      players[idx].points.push(m.sa);
      pivotScores.push(m.sb);
    }
    players[0].points.push(mean(pivotScores));
    const sortedPlayers = stableSortDesc(players.slice(), avg);
    let power = 1;
    while (power < n) power *= 2;
    let bracketIdx = [0];
    let count = 1;
    while (count < power) {
      const next = [];
      for (const i of bracketIdx) { next.push(i); next.push(2 * count - 1 - i); }
      bracketIdx = next;
      count *= 2;
    }
    const seeds = sortedPlayers.map((p) => p.idx);
    let active = bracketIdx.filter((i) => i < n).map((i) => sortedPlayers[i]);
    const history = [];
    let round = 0;
    while (active.length > 1) {
      round += 1;
      const nextRound = [];
      const losers = [];
      const pairings = [];
      let i = 0;
      while (i < active.length) {
        if (i + 1 < active.length) { pairings.push([active[i], active[i + 1]]); i += 2; }
        else {
          nextRound.push(active[i]);
          trace.push({ a: active[i].idx, b: null, round, stage: "bracket", bye: true, winner: active[i].idx });
          i += 1;
        }
      }
      for (const [p1, p2] of pairings) {
        const m = match(judge, p1.idx, p2.idx, round, "bracket");
        p1.points.push(m.sa);
        p2.points.push(m.sb);
        if (m.sa >= m.sb) { nextRound.push(p1); losers.push(p2); m.winner = p1.idx; }
        else { nextRound.push(p2); losers.push(p1); m.winner = p2.idx; }
        trace.push(m);
      }
      if (losers.length) history.push(losers);
      active = nextRound;
    }
    const champion = active[0] || null;
    const ranked = champion ? [champion] : [];
    for (let h = history.length - 1; h >= 0; h--) ranked.push(...stableSortDesc(history[h], avg));
    const raw = positionRewards(ranked.map((p) => p.idx), n);
    return {
      rewards: normalize(raw),
      raw,
      trace,
      seeds,
      order: ranked.map((p) => p.idx),
      standings: ranked.map((p, k) => ({ idx: p.idx, score: avg(p), rank: k + 1 })),
    };
  }

  // -------------------------------------------------- double elimination
  function doubleElimination(n, judge, opts = {}) {
    const trace = [];
    if (n < 2) return { rewards: new Array(n).fill(0), trace, standings: [] };
    const rand = mulberry32(opts.seed == null ? 1 : opts.seed);
    const players = Array.from({ length: n }, (_, i) => newPlayer(i));
    let roundNo = 0;

    function playRound(list, stage) {
      roundNo += 1;
      const pool = shuffleInPlace(list.slice(), rand);
      const pairings = [];
      while (pool.length >= 2) pairings.push([pool.pop(), pool.pop()]);
      const winners = pool.slice();
      for (const b of pool) trace.push({ a: b.idx, b: null, round: roundNo, stage, bye: true, winner: b.idx });
      const losers = [];
      for (const [p1, p2] of pairings) {
        const m = match(judge, p1.idx, p2.idx, roundNo, stage);
        p1.points.push(m.sa);
        p2.points.push(m.sb);
        if (m.sa >= m.sb) { winners.push(p1); losers.push(p2); m.winner = p1.idx; }
        else { winners.push(p2); losers.push(p1); m.winner = p2.idx; }
        trace.push(m);
      }
      return [winners, losers];
    }

    // winners' bracket
    let active = players.slice();
    const drops = [];
    while (active.length > 1) {
      const [w, l] = playRound(active, "winners");
      active = w;
      if (l.length) drops.push(l);
    }
    const wbChamp = active[0] || null;

    // losers' bracket
    let lb = [];
    const elim = [];
    for (const dropped of drops) {
      lb.push(...dropped);
      if (lb.length >= 2) {
        const [w, l] = playRound(lb, "losers");
        lb = w;
        if (l.length) elim.push(l);
      }
    }
    while (lb.length > 1) {
      const [w, l] = playRound(lb, "losers");
      lb = w;
      if (l.length) elim.push(l);
    }
    const lbChamp = lb[0] || null;

    // grand final
    let grandWinner = wbChamp;
    let grandLoser = lbChamp;
    if (wbChamp && lbChamp && wbChamp.idx !== lbChamp.idx) {
      const [w, l] = playRound([wbChamp, lbChamp], "grand final");
      grandWinner = w[0] || null;
      grandLoser = l[0] || null;
    }

    const ranked = [];
    if (grandWinner) ranked.push(grandWinner);
    if (grandLoser) ranked.push(grandLoser);
    for (let h = elim.length - 1; h >= 0; h--) ranked.push(...stableSortDesc(elim[h], avg));
    const seen = new Set(ranked.map((p) => p.idx));
    ranked.push(...stableSortDesc(players.filter((p) => !seen.has(p.idx)), avg));
    const raw = positionRewards(ranked.map((p) => p.idx), n);
    return {
      rewards: normalize(raw),
      raw,
      trace,
      order: ranked.map((p) => p.idx),
      standings: ranked.map((p, k) => ({ idx: p.idx, score: avg(p), rank: k + 1 })),
    };
  }

  // ------------------------------------------------------------ dispatch
  function run(method, qualities, opts = {}) {
    const judge = opts.judge || makeJudge(qualities, opts);
    const n = qualities.length;
    let out;
    switch (method) {
      case "anchor": out = anchor(n, judge); break;
      case "round_robin": out = roundRobin(n, judge); break;
      case "swiss": out = swiss(n, judge, opts); break;
      case "double_elimination": out = doubleElimination(n, judge, opts); break;
      case "single_elimination": out = singleElimination(n, judge); break;
      default: throw new Error("Unknown tournament method: " + method + ". Expected one of " + METHODS.join(", "));
    }
    out.method = method;
    out.calls = judge.calls;
    return out;
  }

  /** Kendall's tau-b between two numeric arrays (ties handled). */
  function kendallTau(x, y) {
    let c = 0, d = 0, tx = 0, ty = 0;
    for (let i = 0; i < x.length; i++) {
      for (let j = i + 1; j < x.length; j++) {
        const sx = Math.sign(x[i] - x[j]);
        const sy = Math.sign(y[i] - y[j]);
        if (sx === 0 && sy === 0) continue;
        if (sx === 0) tx++;
        else if (sy === 0) ty++;
        else if (sx === sy) c++;
        else d++;
      }
    }
    const denom = Math.sqrt((c + d + tx) * (c + d + ty));
    return denom ? (c - d) / denom : 0;
  }

  /** Cost of a method for a group of size n (judge calls), analytically. */
  function expectedCalls(method, n) {
    if (n < 2) return 0;
    switch (method) {
      case "anchor": return n - 1;
      case "round_robin": return (n * (n - 1)) / 2;
      case "swiss": return Math.min(Math.ceil(Math.log2(n)), n - 1) * Math.floor(n / 2);
      case "single_elimination": return 2 * (n - 1);
      case "double_elimination": return null; // 2n-3 .. 2n-1 depending on byes / grand final
      default: return null;
    }
  }

  return {
    METHODS, LABELS, run, makeJudge, kendallTau, expectedCalls, mulberry32, gauss, normalize,
    _internals: { rankMinDescending, rankBasedRewards, positionRewards },
  };
});
