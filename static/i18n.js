// UI 翻译字典 + 全局 t() 函数。在 index.html 主脚本之前加载。
// 用法:t("refresh") → "Pull latest" / "获取最新" / "最新を取得"
// 带参数:t("loadMore", 12) → 模板函数被调用,返回字符串
// 缺 key 时 fallback 到英文,再缺就返回 key 本身,保证不崩。

window.TRANSLATIONS = {
  en: {
    pageTitle: "Loop.",
    loading: "Loading…",
    refresh: "Pull latest",
    refreshing: "Pulling…",
    heroHeadline: "Don't be the last one to know.",
    heroSub: "AI-curated news with talking points ready for tonight's dinner.",
    langSwitcherAria: "Language",

    filterAll: "Everything",
    topicGeopolitics: "Geopolitics",
    topicBusiness: "Business",
    topicTech: "Tech",
    topicChina: "China",
    topicJapan: "Japan",
    topicScience: "Science",
    topicOther: "Other",

    importanceMustRead: "Must Read",
    importanceWorthKnowing: "Worth Knowing",
    importanceIfTime: "If Time",

    biasLeft: "Left",
    biasLeanLeft: "Lean Left",
    biasCenter: "Center",
    biasLeanRight: "Lean Right",
    biasRight: "Right",
    biasTooltip: "Political lean rating based on AllSides Media Bias Chart.",

    translate: "Translate",
    translating: "Translating…",
    showOriginal: "Show original",
    pickChinese: "中文",
    pickJapanese: "日本語",

    talkingPoints: "💬 Talking points",
    hideTalkingPoints: "💬 Hide",

    headerStats: (count, time) =>
      `${count} stor${count === 1 ? "y" : "ies"} · past 24h · Updated ${time}`,
    headerNever: "Pull latest to load your first batch of stories",

    justNow: "just now",
    timeAgo: (n, unit) => `${n}${unit} ago`,

    emptyFiltered: "Nothing here yet. Try another filter.",
    emptyNoData: "No stories yet — pull latest to fetch.",

    loadMore: (n) => `Load more (${n} remaining)`,

    briefTitle: "TODAY'S BRIEF",
    briefDate: () => {
      const d = new Date();
      const m = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"][d.getMonth()];
      return `· ${m} ${d.getDate()}`;
    },
    briefEmpty: "Pull latest to generate today's brief",

    toastAddedNew: (n) => `+${n} new stor${n === 1 ? "y" : "ies"}`,
    toastNoNew: "All caught up",
    toastRefreshed: "Refreshed",
    toastPartialFail: (srcs) => `Refreshed with partial data: ${srcs} failed`,
    toastRefreshFailed: (msg) => `Refresh failed: ${msg}`,
    toastLoadFailed: (msg) => `Load failed: ${msg}`,
    toastRateLimited: "Rate limited. Slow down.",
    toastTranslateFailed: (msg) => `Translation failed: ${msg}`,
  },

  zh: {
    pageTitle: "Loop.",
    loading: "加载中…",
    refresh: "获取最新",
    refreshing: "获取中…",
    heroHeadline: "别成为最后一个知道的人。",
    heroSub: "AI 精选今日要闻,附上今晚饭桌就能用的谈资。",
    langSwitcherAria: "语言",

    filterAll: "全部内容",
    topicGeopolitics: "地缘政治",
    topicBusiness: "商业",
    topicTech: "科技",
    topicChina: "中国",
    topicJapan: "日本",
    topicScience: "科学",
    topicOther: "其他",

    importanceMustRead: "必读",
    importanceWorthKnowing: "值得关注",
    importanceIfTime: "有空再看",

    biasLeft: "左翼",
    biasLeanLeft: "偏左",
    biasCenter: "中立",
    biasLeanRight: "偏右",
    biasRight: "右翼",
    biasTooltip: "政治倾向评级,基于 AllSides 媒体偏向图表。",

    translate: "翻译",
    translating: "翻译中…",
    showOriginal: "显示原文",
    pickChinese: "中文",
    pickJapanese: "日本語",

    talkingPoints: "💬 谈资",
    hideTalkingPoints: "💬 收起",

    headerStats: (count, time) =>
      `显示过去 24 小时内的 ${count} 条新闻 · 最后更新于 ${time}`,
    headerNever: "尚未加载 — 点击「获取最新」加载新闻",

    justNow: "刚刚",
    timeAgo: (n, unit) => {
      const units = { m: "分钟前", h: "小时前", d: "天前" };
      return `${n} ${units[unit] || ""}`;
    },

    emptyFiltered: "暂无内容。试试其他筛选。",
    emptyNoData: "暂无数据 — 点击「获取最新」加载新闻。",

    loadMore: (n) => `加载更多(还剩 ${n} 条)`,

    briefTitle: "今日简报",
    briefDate: () => {
      const d = new Date();
      return `· ${d.getMonth()+1}月${d.getDate()}日`;
    },
    briefEmpty: "获取最新以生成今日简报",

    toastAddedNew: (n) => `+${n} 条新内容`,
    toastNoNew: "已是最新",
    toastRefreshed: "已刷新",
    toastPartialFail: (srcs) => `部分数据缺失:${srcs} 抓取失败`,
    toastRefreshFailed: (msg) => `刷新失败:${msg}`,
    toastLoadFailed: (msg) => `加载失败:${msg}`,
    toastRateLimited: "请求过于频繁,请稍后再试。",
    toastTranslateFailed: (msg) => `翻译失败:${msg}`,
  },

  ja: {
    pageTitle: "Loop.",
    loading: "読み込み中…",
    refresh: "最新を取得",
    refreshing: "取得中…",
    heroHeadline: "最後に知る人にならない。",
    heroSub: "AI が厳選した今日のニュース。今夜の会話で使える話のネタ付き。",
    langSwitcherAria: "言語",

    filterAll: "すべて",
    topicGeopolitics: "地政学",
    topicBusiness: "ビジネス",
    topicTech: "テクノロジー",
    topicChina: "中国",
    topicJapan: "日本",
    topicScience: "科学",
    topicOther: "その他",

    importanceMustRead: "必読",
    importanceWorthKnowing: "重要",
    importanceIfTime: "余裕があれば",

    biasLeft: "左派",
    biasLeanLeft: "やや左派",
    biasCenter: "中立",
    biasLeanRight: "やや右派",
    biasRight: "右派",
    biasTooltip: "AllSides メディアバイアスチャートに基づく政治傾向評価。",

    translate: "翻訳",
    translating: "翻訳中…",
    showOriginal: "原文を表示",
    pickChinese: "中文",
    pickJapanese: "日本語",

    talkingPoints: "💬 話のネタ",
    hideTalkingPoints: "💬 閉じる",

    headerStats: (count, time) =>
      `過去24時間の${count}件のニュースを表示 · 最終更新 ${time}`,
    headerNever: "「最新を取得」をクリックしてニュースを読み込み",

    justNow: "たった今",
    timeAgo: (n, unit) => {
      const units = { m: "分前", h: "時間前", d: "日前" };
      return `${n}${units[unit] || ""}`;
    },

    emptyFiltered: "該当なし。他のフィルターをお試しください。",
    emptyNoData: "データなし — 「最新を取得」をクリックして読み込み。",

    loadMore: (n) => `もっと見る(残り ${n} 件)`,

    briefTitle: "本日のブリーフ",
    briefDate: () => {
      const d = new Date();
      return `· ${d.getMonth()+1}月${d.getDate()}日`;
    },
    briefEmpty: "最新を取得して今日のブリーフを生成",

    toastAddedNew: (n) => `+${n}件の新着`,
    toastNoNew: "最新の状態です",
    toastRefreshed: "更新しました",
    toastPartialFail: (srcs) => `一部データなし:${srcs} の取得失敗`,
    toastRefreshFailed: (msg) => `更新失敗:${msg}`,
    toastLoadFailed: (msg) => `読み込み失敗:${msg}`,
    toastRateLimited: "リクエストが多すぎます。少々お待ちください。",
    toastTranslateFailed: (msg) => `翻訳失敗:${msg}`,
  },
};

window.getUiLang = function () {
  return localStorage.getItem("ui_lang") || "en";
};

window.setUiLang = function (lang) {
  localStorage.setItem("ui_lang", lang);
};

// 全局 t():带模板函数支持 + 英文兜底
window.t = function (key, ...args) {
  const lang = window.getUiLang();
  const dict = window.TRANSLATIONS[lang] || window.TRANSLATIONS.en;
  let val = dict[key];
  if (val === undefined) val = window.TRANSLATIONS.en[key];
  if (val === undefined) return key;
  return typeof val === "function" ? val(...args) : val;
};
