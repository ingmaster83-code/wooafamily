// 행사 목록: /deal/data.json 전체를 불러와 검색·필터·정렬 (HTML에는 상위 목록이 이미 들어 있어 JS 없이도 보임)
(function () {
  var box = document.getElementById("dctl"), list = document.getElementById("dlist");
  if (!box || !list) return;
  var st = { q: "", store: box.dataset.store || "", group: box.dataset.group || "", sort: "rec" };
  var data = null, shown = 40, STEP = 40;
  var ST = { cu: "CU", seven: "세븐일레븐", emart24: "이마트24", homeplus: "홈플러스" };
  var GL = { "1plus1": "1+1", "2plus1": "2+1", "3plus1": "3+1", sale: "세일·할인", card: "카드할인", flyer: "전단 특가", pick: "골라담기" };
  function won(v) { return v == null ? "-" : v.toLocaleString("ko-KR") + "원"; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function row(d) {
    var img = d.i ? '<img class="d-img" loading="lazy" referrerpolicy="no-referrer" src="' + esc(d.i) + '" alt="">' : '<span class="d-img ph"></span>';
    var price;
    if (d.p === "1+1" || d.p === "2+1" || d.p === "3+1") price = '<span class="d-list">정가 ' + won(d.l) + '</span><b class="d-unit">개당 ' + won(d.u) + '</b><span class="d-rate">' + d.r + '%↓</span>';
    else if (d.u != null && d.l && d.u < d.l && d.g !== "flyer") price = '<span class="d-list">정가 ' + won(d.l) + '</span><b class="d-unit">' + won(d.u) + '</b><span class="d-rate">' + d.r + '%↓</span>';
    else if (d.g === "pick") price = '<b class="d-unit">' + won(d.l) + '</b><span class="d-note">골라담기 가격·조건은 매장 확인</span>';
    else price = '<b class="d-unit">' + won(d.u != null ? d.u : d.l) + '</b>';
    var extra = d.z ? '<span class="d-note">' + esc(d.z) + '</span>' : "";
    var buy = d.b ? '<a class="d-buy" href="' + esc(d.b) + '" rel="nofollow sponsored noopener" target="_blank">온라인 가격비교 ↗</a>' : "";
    return '<div class="drow">' + img + '<div class="d-main"><div class="d-top"><span class="stb ' + d.s + '">' + ST[d.s] + '</span><span class="tag">' + (GL[d.g] || d.p) + '</span></div><b class="d-name">' + esc(d.n) + '</b></div><div class="d-price">' + price + extra + buy + '</div></div>';
  }
  var PRI = { "1plus1": 0, "2plus1": 1, "3plus1": 2 };
  var sorters = {
    rec: function (a, b) {
      var pa = PRI[a.g] == null ? 3 : PRI[a.g], pb = PRI[b.g] == null ? 3 : PRI[b.g];
      return pa - pb || b.r - a.r || (a.u == null ? 1e9 : a.u) - (b.u == null ? 1e9 : b.u);
    },
    rate: function (a, b) { return b.r - a.r || (a.u == null) - (b.u == null) || (a.u || 0) - (b.u || 0); },
    unit: function (a, b) { return (a.u == null ? 1e9 : a.u) - (b.u == null ? 1e9 : b.u); },
    list: function (a, b) { return (a.l || 1e9) - (b.l || 1e9); }
  };
  function render(reset) {
    if (!data) return;
    if (reset) shown = STEP;
    var q = st.q.trim().toLowerCase();
    var vis = data.filter(function (d) {
      return (!st.store || d.s === st.store) && (!st.group || d.g === st.group) && (!q || d.n.toLowerCase().indexOf(q) >= 0);
    }).sort(sorters[st.sort]);
    list.innerHTML = vis.slice(0, shown).map(row).join("");
    document.getElementById("dcnt").textContent = vis.length;
    document.getElementById("dempty").hidden = vis.length > 0;
    var more = document.getElementById("dmore");
    more.hidden = vis.length <= shown; more.textContent = "더 보기 (" + (vis.length - shown) + ")";
  }
  // 컨트롤 초기 상태를 페이지 프리셋에 맞춤
  function sync() {
    box.querySelectorAll(".seg").forEach(function (seg) {
      var k = seg.dataset.k === "dstore" ? st.store : st.group;
      seg.querySelectorAll("button").forEach(function (b) { b.classList.toggle("on", b.dataset.v === k); });
    });
  }
  box.querySelectorAll(".seg").forEach(function (seg) {
    seg.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      if (seg.dataset.k === "dstore") st.store = b.dataset.v; else st.group = b.dataset.v;
      sync(); render(true);
    });
  });
  box.querySelectorAll(".sortb").forEach(function (b) {
    b.addEventListener("click", function () {
      box.querySelectorAll(".sortb").forEach(function (x) { x.classList.toggle("on", x === b); });
      st.sort = b.dataset.s; render(true);
    });
  });
  var t; document.getElementById("dq").addEventListener("input", function (e) { clearTimeout(t); t = setTimeout(function () { st.q = e.target.value; render(true); }, 150); });
  document.getElementById("dmore").addEventListener("click", function () { shown += STEP; render(false); });
  sync();
  fetch("/deal/data.json").then(function (r) { return r.json(); }).then(function (j) { data = j; render(true); });
})();
