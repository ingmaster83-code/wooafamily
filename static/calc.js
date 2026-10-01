// 알뜰폰 갈아타기 절약 계산기: /phone/calculator/data.json 의 요금제 중 조건에 맞는 것을 찾아 월·연 절약액을 계산한다.
(function () {
  var form = document.getElementById("calc");
  if (!form) return;
  var out = document.getElementById("calc-out"), sum = document.getElementById("calc-sum");
  var plans = null;
  function won(v) { return v == null ? "-" : Math.round(v).toLocaleString("ko-KR") + "원"; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function val(id) { return form.querySelector("#" + id).value; }

  // 첫 12개월 총 납부액 (기간 할인은 할인 개월 수만큼만 적용)
  function year(p) {
    var m = p.t === "lifetime" ? 12 : Math.min(p.m || 0, 12);
    var after = p.a != null ? p.a : p.p;
    return p.p * m + after * (12 - m);
  }
  function run() {
    if (!plans) return;
    var cur = parseInt(val("c-fee"), 10) || 0;
    var need = val("c-data"), voiceNeed = parseInt(val("c-voice"), 10), net = val("c-net");
    var g5 = form.querySelector("#c-5g").checked, longOnly = form.querySelector("#c-long").checked, withTarget = form.querySelector("#c-target").checked;
    var list = plans.filter(function (p) {
      if (net && p.w !== net) return false;
      if (g5 && p.g !== "5G") return false;
      if (p.r && !withTarget) return false;
      if (longOnly && p.t === "period") return false;
      if (need === "unl") { if (!p.l) return false; }
      else if (p.d < parseFloat(need)) return false;
      if (p.v < voiceNeed) return false;
      return p.p != null;
    });
    list.forEach(function (p) { p._y = year(p); p._save = cur * 12 - p._y; p._long = cur - (p.a != null ? p.a : p.p); });
    list.sort(function (a, b) { return a._y - b._y; });
    var good = list.filter(function (p) { return p._save > 0; });
    var top = (cur > 0 ? good : list).slice(0, 10);
    if (!list.length) {
      sum.innerHTML = '<b>조건에 맞는 요금제가 없어요.</b><span>데이터·통화 조건을 조금 낮추거나 통신망 선택을 풀어 보세요.</span>';
      out.innerHTML = ""; return;
    }
    var best = list[0];
    if (cur > 0 && best._save > 0) {
      sum.innerHTML = '<b>연 최대 ' + won(best._save) + ' 절약</b><span>지금 월 ' + won(cur) + ' → ' + esc(best.c) + ' ' + esc(best.n) + ' (첫 1년 월평균 ' + won(best._y / 12) + ')</span>';
    } else if (cur > 0) {
      sum.innerHTML = '<b>이 조건에선 지금 요금이 이미 저렴해요</b><span>조건에 맞는 알뜰폰은 ' + list.length + '개지만 첫 1년 총액이 지금보다 낮은 요금제는 없어요.</span>';
    } else {
      sum.innerHTML = '<b>조건에 맞는 알뜰폰 ' + list.length + '개</b><span>지금 내는 월 요금을 넣으면 절약액을 계산해 드려요.</span>';
    }
    out.innerHTML = '<div class="list static">' + top.map(function (p) {
      var after = p.t === "period" && p.m && p.a != null ? '<span class="af warn">' + p.m + '개월 후 ' + won(p.a) + '</span>' : (p.t === "lifetime" ? '<span class="af good">평생 유지</span>' : '<span class="af">정가</span>');
      var save = cur > 0 ? '<span class="cs ' + (p._save > 0 ? "plus" : "") + '">연 ' + (p._save > 0 ? "-" + won(p._save) : "절약 없음") + '</span>' : "";
      return '<a class="row" href="' + esc(p.u) + '"><div class="r-main"><div class="r-top"><span class="net ' + ({ SKT: "skt", KT: "kt", "LGU+": "lgu" }[p.w] || "") + '">' + esc(p.w) + '</span><span class="car">' + esc(p.c) + '</span></div><b class="r-name">' + esc(p.n) + '</b>' +
        '<div class="r-spec"><span class="r-data">' + (p.l && p.d >= 9999 ? "무제한" : (p.d >= 1 ? +p.d.toFixed(1) + "GB" : Math.round(p.d * 1024) + "MB")) + '</span><span class="r-sub">통화 ' + (p.v >= 9999 ? "무제한" : p.v + "분") + (p.l && p.d < 9999 ? " · 소진 후 무제한" : "") + '</span></div></div>' +
        '<div class="r-price"><b>' + won(p.p) + '</b>' + after + save + '</div><span class="chev">›</span></a>';
    }).join("") + "</div>";
  }
  form.addEventListener("input", run);
  form.addEventListener("change", run);
  form.addEventListener("submit", function (e) { e.preventDefault(); run(); });
  form.querySelectorAll(".fee-chip").forEach(function (b) {
    b.addEventListener("click", function () { form.querySelector("#c-fee").value = b.dataset.v; run(); });
  });
  fetch("/phone/calculator/data.json").then(function (r) { return r.json(); }).then(function (j) { plans = j; run(); });
})();
