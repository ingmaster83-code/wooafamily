// 표 헤더 클릭 정렬 (data-s=n 인 열은 td의 data-v 숫자 기준)
document.querySelectorAll("table.sortable").forEach(function (t) {
  var dir = {};
  t.querySelectorAll("th[data-s]").forEach(function (th) {
    th.addEventListener("click", function () {
      var i = Array.prototype.indexOf.call(th.parentNode.children, th);
      var tb = t.tBodies[0];
      var rows = Array.prototype.slice.call(tb.rows);
      dir[i] = !dir[i];
      rows.sort(function (a, b) {
        var x = parseFloat(a.cells[i].dataset.v), y = parseFloat(b.cells[i].dataset.v);
        return dir[i] ? x - y : y - x;
      });
      rows.forEach(function (r) { tb.appendChild(r); });
    });
  });
});
