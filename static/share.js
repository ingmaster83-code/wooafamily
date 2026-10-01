// 공유: 상단 '공유하기' 버튼(초록) + 페이지 하단 공유 카드. 카카오톡은 카카오 JS 키가 있으면 SDK로, 없으면 모바일 기기 공유창/링크 복사로 처리.
(function () {
  var canon = document.querySelector('link[rel="canonical"]');
  var url = canon ? canon.href : location.href;
  var og = document.querySelector('meta[property="og:title"]');
  var title = og ? og.content : document.title;
  var text = (document.querySelector('meta[name="description"]') || {}).content || "";
  var imgMeta = document.querySelector('meta[property="og:image"]');
  var image = imgMeta ? imgMeta.content : "";
  var KEY = window.WOOA_KAKAO_KEY || "";
  var isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  var u = encodeURIComponent(url), t = encodeURIComponent(title);
  var links = {
    nv: "https://share.naver.com/web/shareView?url=" + u + "&title=" + t,
    fb: "https://www.facebook.com/sharer/sharer.php?u=" + u,
    x: "https://twitter.com/intent/tweet?url=" + u + "&text=" + t
  };

  var toastEl = document.createElement("div");
  toastEl.className = "share-toast-g"; toastEl.hidden = true;
  document.body.appendChild(toastEl);
  function say(msg) { toastEl.textContent = msg; toastEl.hidden = false; clearTimeout(say._t); say._t = setTimeout(function () { toastEl.hidden = true; }, 2200); }

  function copy(msg) {
    function fallback() {
      var ta = document.createElement("textarea"); ta.value = url; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); say(msg || "링크를 복사했어요"); } catch (e) { say("복사하지 못했어요"); }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(function () { say(msg || "링크를 복사했어요"); }, fallback);
    else fallback();
  }
  function nativeShare() {
    if (navigator.share) { navigator.share({ title: title, text: text.slice(0, 80), url: url }).catch(function () {}); return true; }
    return false;
  }
  // 카카오톡: SDK(키 있음) -> 모바일 기기 공유창 -> 링크 복사 안내
  var kakaoReady = null;
  function loadKakao(cb) {
    if (window.Kakao && Kakao.isInitialized && Kakao.isInitialized()) return cb(true);
    if (kakaoReady === false) return cb(false);
    var s = document.createElement("script");
    s.src = "https://t1.kakaocdn.net/kakao_js_sdk/2.7.4/kakao.min.js"; s.crossOrigin = "anonymous";
    s.onload = function () { try { Kakao.init(KEY); kakaoReady = true; cb(true); } catch (e) { kakaoReady = false; cb(false); } };
    s.onerror = function () { kakaoReady = false; cb(false); };
    document.head.appendChild(s);
  }
  function kakao() {
    function fallback() { if (!(isMobile && nativeShare())) copy("링크를 복사했어요. 카카오톡에 붙여넣어 보내세요"); }
    if (!KEY) return fallback();
    loadKakao(function (ok) {
      if (!ok) return fallback();
      try {
        Kakao.Share.sendDefault({
          objectType: "feed",
          content: { title: title, description: text.slice(0, 70), imageUrl: image, link: { mobileWebUrl: url, webUrl: url } },
          buttons: [{ title: "자세히 보기", link: { mobileWebUrl: url, webUrl: url } }]
        });
      } catch (e) { fallback(); }
    });
  }
  function act(a) {
    if (a === "kakao") kakao();
    else if (a === "copy") copy();
    else if (a === "native") { if (!nativeShare()) copy(); }
  }
  function actions(prefix) {
    return '<button type="button" class="sb kakao" data-a="kakao"><span class="kk">💬</span> 카카오톡</button>' +
      '<button type="button" class="sb" data-a="copy">🔗 링크 복사</button>' +
      '<a class="sb" href="' + links.nv + '" target="_blank" rel="noopener">네이버</a>' +
      '<a class="sb" href="' + links.fb + '" target="_blank" rel="noopener">페이스북</a>' +
      '<a class="sb" href="' + links.x + '" target="_blank" rel="noopener">X</a>';
  }
  function bind(root) {
    root.addEventListener("click", function (e) {
      var b = e.target.closest("[data-a]");
      if (b) act(b.dataset.a);
    });
  }

  // 1) 상단 공유하기 버튼 (경로 표시 줄 오른쪽, 없으면 화면 오른쪽 아래)
  var wrap = document.createElement("div");
  wrap.className = "share";
  wrap.innerHTML = '<button type="button" class="share-b share-primary" aria-haspopup="true" aria-expanded="false"><span class="share-ic">⤴</span> 공유하기</button>' +
    '<div class="share-m" role="menu" hidden>' + actions() + '</div>';
  var crumbs = document.querySelector(".crumbs");
  if (crumbs) {
    var row = document.createElement("div");
    row.className = "crumbs-row";
    crumbs.parentNode.insertBefore(row, crumbs);
    row.appendChild(crumbs); row.appendChild(wrap);
  } else {
    wrap.classList.add("share-fab");
    document.body.appendChild(wrap);
  }
  var btn = wrap.querySelector(".share-b"), menu = wrap.querySelector(".share-m");
  function close() { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); }
  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    if (isMobile && navigator.share) { nativeShare(); return; }  // 모바일: 기기 공유창(카카오톡 등)
    var open = menu.hidden; menu.hidden = !open; btn.setAttribute("aria-expanded", String(open));
  });
  menu.addEventListener("click", function () { setTimeout(close, 50); });
  bind(menu);
  document.addEventListener("click", function (e) { if (!wrap.contains(e.target)) close(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });

  // 2) 페이지 하단 공유 카드 (광고·추천 블록 앞에 배치)
  var main = document.querySelector("main");
  if (main) {
    var card = document.createElement("section");
    card.className = "share-card";
    card.innerHTML = '<div class="share-card-t"><b>도움이 됐다면 공유해 주세요</b><span>가족·친구에게 알려 주면 함께 절약할 수 있어요</span></div>' +
      '<div class="share-row">' + actions() + '</div>';
    // main 바로 아래 자식 중 광고·추천 블록 앞에 두고, 없으면(요금제 상세처럼 사이드에 있는 경우) 본문 맨 아래에 붙인다
    var anchor = Array.prototype.filter.call(main.children, function (el) { return el.matches(".coupang, .gold, .phones"); })[0];
    if (anchor) main.insertBefore(card, anchor); else main.appendChild(card);
    bind(card);
  }
})();
