// 홈 자급제폰 슬라이드: 한 개씩 보여주고 4초마다 옆으로 넘김. 마우스를 올리거나 터치 중이면 멈춘다.
(function () {
  var box = document.getElementById("pcar");
  if (!box) return;
  var track = box.querySelector(".pcar-track");
  var slides = track.children, n = slides.length;
  if (n < 2) return;
  var dots = box.querySelectorAll(".pcar-dot");
  var i = 0, timer = null, paused = false;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function go(k, smooth) {
    i = (k + n) % n;
    track.scrollTo({ left: slides[i].offsetLeft - track.offsetLeft, behavior: smooth === false ? "auto" : "smooth" });
    dots.forEach(function (d, j) { d.classList.toggle("on", j === i); });
  }
  // 사용자가 직접 넘기면(스와이프) 현재 위치를 반영
  var t;
  track.addEventListener("scroll", function () {
    clearTimeout(t);
    t = setTimeout(function () {
      var w = slides[0].offsetWidth || 1;
      var k = Math.round(track.scrollLeft / w);
      if (k !== i) { i = Math.min(Math.max(k, 0), n - 1); dots.forEach(function (d, j) { d.classList.toggle("on", j === i); }); }
    }, 80);
  });
  box.querySelector(".pcar-prev").addEventListener("click", function () { go(i - 1); });
  box.querySelector(".pcar-next").addEventListener("click", function () { go(i + 1); });
  dots.forEach(function (d, j) { d.addEventListener("click", function () { go(j); }); });
  ["mouseenter", "focusin", "touchstart"].forEach(function (ev) { box.addEventListener(ev, function () { paused = true; }, { passive: true }); });
  ["mouseleave", "focusout", "touchend"].forEach(function (ev) { box.addEventListener(ev, function () { paused = false; }, { passive: true }); });
  if (!reduce) timer = setInterval(function () { if (!paused && !document.hidden) go(i + 1); }, 4000);
})();
