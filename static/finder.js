// 요금제 찾기: 서버가 만든 .row 목록을 data-* 속성으로 필터/정렬 (JS 없이도 전체 목록이 보임)
(function () {
  var list = document.getElementById("list");
  if (!list) return;
  var rows = Array.prototype.slice.call(list.querySelectorAll(".row"));
  var cnt = document.getElementById("cnt");
  var moreBtn = document.getElementById("more");
  var empty = document.getElementById("empty");
  var PAGE = 30, shown = PAGE;
  var st = { net: "", qos: "", data: "", price: "", disc: "", car: {}, tog: {}, sort: "eff" };

  function num(r, k) { var v = parseFloat(r.dataset[k]); return isNaN(v) ? 0 : v; }
  function match(r) {
    if (st.net && r.dataset.net !== st.net) return false;
    if (st.disc && r.dataset.disc !== st.disc) return false;
    if (st.data === "unlimited") { if (r.dataset.unl !== "1") return false; }
    else if (st.data && r.dataset.data !== st.data) return false;
    if (st.price && r.dataset.price !== st.price) return false;
    if (st.qos) {
      var q = num(r, "qos");
      if (st.qos === "5" && q < 5000) return false;
      if (st.qos === "3" && !(q >= 3000 && q < 5000)) return false;
      if (st.qos === "1" && !(q > 0 && q < 3000)) return false;
      if (st.qos === "0" && q !== 0) return false;
    }
    var cs = Object.keys(st.car).filter(function (k) { return st.car[k]; });
    if (cs.length && cs.indexOf(r.dataset.car) < 0) return false;
    if (st.tog.voice && r.dataset.voice !== "u") return false;
    if (st.tog.g5 && r.dataset.gen !== "5G") return false;
    if (st.tog.life && r.dataset.disc !== "lifetime") return false;
    if (st.tog.share && r.dataset.share !== "1") return false;
    return true;
  }
  var sorters = {
    eff: function (a, b) { return num(a, "eff") - num(b, "eff"); },
    now: function (a, b) { return num(a, "now") - num(b, "now"); },
    gb: function (a, b) { return num(b, "gb") - num(a, "gb") || num(a, "eff") - num(b, "eff"); }
  };
  function apply(resetPage) {
    if (resetPage) shown = PAGE;
    var vis = rows.filter(match).sort(sorters[st.sort]);
    rows.forEach(function (r) { r.hidden = true; });
    vis.forEach(function (r, i) { list.appendChild(r); r.hidden = i >= shown; });
    cnt.textContent = vis.length;
    if (empty) empty.hidden = vis.length > 0;
    if (moreBtn) { moreBtn.hidden = vis.length <= shown; moreBtn.textContent = "더 보기 (" + (vis.length - shown) + ")"; }
    var fc = document.getElementById("fcnt");
    if (fc) fc.textContent = vis.length;
  }
  // 구분 선택(세그먼트)
  document.querySelectorAll(".seg").forEach(function (seg) {
    seg.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      seg.querySelectorAll("button").forEach(function (x) { x.classList.toggle("on", x === b); });
      st[seg.dataset.k] = b.dataset.v; apply(true);
      syncMirror(seg.dataset.k, b.dataset.v);
    });
  });
  // 토글 칩
  document.querySelectorAll(".tgl").forEach(function (b) {
    b.addEventListener("click", function () {
      b.classList.toggle("on"); st.tog[b.dataset.k] = b.classList.contains("on"); apply(true);
    });
  });
  // 통신사 체크
  document.querySelectorAll(".carchk input").forEach(function (c) {
    c.addEventListener("change", function () { st.car[c.value] = c.checked; apply(true); });
  });
  // 정렬
  document.querySelectorAll(".sortb").forEach(function (b) {
    b.addEventListener("click", function () {
      document.querySelectorAll(".sortb").forEach(function (x) { x.classList.toggle("on", x === b); });
      st.sort = b.dataset.s; apply(true);
    });
  });
  if (moreBtn) moreBtn.addEventListener("click", function () { shown += PAGE; apply(false); });
  // 모바일 필터 시트
  var sheet = document.getElementById("filters");
  var openB = document.getElementById("openf");
  var closeBs = document.querySelectorAll(".closef");
  if (openB) openB.addEventListener("click", function () { sheet.classList.add("open"); document.body.classList.add("lock"); });
  function close() { sheet.classList.remove("open"); document.body.classList.remove("lock"); }
  closeBs.forEach(function (b) { b.addEventListener("click", close); });
  var resetB = document.getElementById("resetf");
  if (resetB) resetB.addEventListener("click", function () {
    st = { net: "", qos: "", data: "", price: "", disc: "", car: {}, tog: {}, sort: st.sort };
    document.querySelectorAll(".seg").forEach(function (s) { s.querySelectorAll("button").forEach(function (x, i) { x.classList.toggle("on", i === 0); }); });
    document.querySelectorAll(".tgl.on").forEach(function (x) { x.classList.remove("on"); });
    document.querySelectorAll(".carchk input").forEach(function (x) { x.checked = false; });
    apply(true);
  });
  // 모바일 상단 빠른 통신망 바와 사이드바 통신망 세그먼트 동기화
  function syncMirror(k, v) {
    document.querySelectorAll('.seg[data-k="' + k + '"]').forEach(function (s) {
      s.querySelectorAll("button").forEach(function (x) { x.classList.toggle("on", x.dataset.v === v); });
    });
  }
  apply(true);
})();
