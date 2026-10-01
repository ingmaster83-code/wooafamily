// 페이지 공유 버튼: 모바일은 기기 공유창(카카오톡 등), PC는 링크 복사·페이스북·X·네이버 메뉴.
(function () {
  var canon = document.querySelector('link[rel="canonical"]');
  var url = canon ? canon.href : location.href;
  var og = document.querySelector('meta[property="og:title"]');
  var title = og ? og.content : document.title;
  var text = (document.querySelector('meta[name="description"]') || {}).content || "";

  var wrap = document.createElement("div");
  wrap.className = "share";
  wrap.innerHTML =
    '<button type="button" class="share-b" aria-haspopup="true" aria-expanded="false"><span class="share-ic">⤴</span> 공유</button>' +
    '<div class="share-m" role="menu" hidden>' +
    '<button type="button" role="menuitem" data-a="copy">🔗 링크 복사</button>' +
    '<a role="menuitem" data-a="nv" target="_blank" rel="noopener">네이버 공유</a>' +
    '<a role="menuitem" data-a="fb" target="_blank" rel="noopener">페이스북</a>' +
    '<a role="menuitem" data-a="x" target="_blank" rel="noopener">X(트위터)</a>' +
    '</div><span class="share-toast" hidden>링크를 복사했어요</span>';

  var u = encodeURIComponent(url), t = encodeURIComponent(title);
  wrap.querySelector('[data-a="nv"]').href = "https://share.naver.com/web/shareView?url=" + u + "&title=" + t;
  wrap.querySelector('[data-a="fb"]').href = "https://www.facebook.com/sharer/sharer.php?u=" + u;
  wrap.querySelector('[data-a="x"]').href = "https://twitter.com/intent/tweet?url=" + u + "&text=" + t;

  // 경로 표시 줄이 있으면 그 오른쪽, 없으면 화면 오른쪽 아래에 고정
  var crumbs = document.querySelector(".crumbs");
  if (crumbs) {
    var row = document.createElement("div");
    row.className = "crumbs-row";
    crumbs.parentNode.insertBefore(row, crumbs);
    row.appendChild(crumbs);
    row.appendChild(wrap);
  } else {
    wrap.classList.add("share-fab");
    document.body.appendChild(wrap);
  }

  var btn = wrap.querySelector(".share-b"), menu = wrap.querySelector(".share-m"), toast = wrap.querySelector(".share-toast");
  function close() { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); }
  function say(msg) { toast.textContent = msg; toast.hidden = false; setTimeout(function () { toast.hidden = true; }, 1800); }
  function copy() {
    function fallback() {
      var ta = document.createElement("textarea"); ta.value = url; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); say("링크를 복사했어요"); } catch (e) { say("복사하지 못했어요"); }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(function () { say("링크를 복사했어요"); }, fallback);
    else fallback();
  }

  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    // 모바일: 기기 기본 공유창(카카오톡·메시지 등)
    if (navigator.share && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
      navigator.share({ title: title, text: text.slice(0, 80), url: url }).catch(function () {});
      return;
    }
    var open = menu.hidden;
    menu.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
  });
  menu.addEventListener("click", function (e) {
    var a = e.target.closest("[data-a]");
    if (!a) return;
    if (a.dataset.a === "copy") copy();
    close();
  });
  document.addEventListener("click", function (e) { if (!wrap.contains(e.target)) close(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
})();
