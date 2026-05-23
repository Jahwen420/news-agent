// UI 翻译字典 + 全局 t() 函数。在 index.html 主脚本之前加载。
// 用法:t("refresh") → "Refresh" / "刷新" / "更新"
// 带参数:t("loadMore", 12) → 模板函数被调用,返回字符串
// 缺 key 时 fallback 到英文,再缺就返回 key 本身,保证不崩。

window.TRANSLATIONS = {
  en: {
    pageTitle: "Today's Headlines",
    loading: "Loading…",
    refresh: "Refresh",
    refreshing: "Refreshing…",

    filterAll: "All",
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

    headerStats: (count, time) =>
      `Showing ${count} stor${count === 1 ? "y" : "ies"} from the past 24 hours · Last refreshed ${time}`,
    headerNever: "Last refreshed: never — click Refresh to load news",

    justNow: "just now",
    timeAgo: (n, unit) => `${n}${unit} ago`,

    emptyFiltered: "No articles match this filter.",
    emptyNoData: "No data yet — click Refresh to fetch.",

    loadMore: (n) => `Load more (${n} remaining)`,

    toastAddedNew: (n) => `Added ${n} new article${n === 1 ? "" : "s"}`,
    toastNoNew: "No new articles since last refresh",
    toastRefreshed: "Refreshed",
    toastPartialFail: (srcs) => `Refreshed with partial data: ${srcs} failed`,
    toastRefreshFailed: (msg) => `Refresh failed: ${msg}`,
    toastLoadFailed: (msg) => `Load failed: ${msg}`,
    toastRateLimited: "Rate limited. Slow down.",
    toastTranslateFailed: (msg) => `Translation failed: ${msg}`,
  },

  zh: {
    pageTitle: "今日新闻",
    loading: "加载中…",
    refresh: "刷新",
    refreshing: "刷新中…",

    filterAll: "全部",
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

    headerStats: (count, time) =>
      `显示过去 24 小时内的 ${count} 条新闻 · 最后更新于 ${time}`,
    headerNever: "尚未刷新 — 点击「刷新」加载新闻",

    justNow: "刚刚",
    timeAgo: (n, unit) => {
      const units = { m: "分钟前", h: "小时前", d: "天前" };
      return `${n} ${units[unit] || ""}`;
    },

    emptyFiltered: "没有匹配此筛选的新闻。",
    emptyNoData: "暂无数据 — 点击「刷新」获取新闻。",

    loadMore: (n) => `加载更多(还剩 ${n} 条)`,

    toastAddedNew: (n) => `新增 ${n} 条新闻`,
    toastNoNew: "暂无新内容",
    toastRefreshed: "已刷新",
    toastPartialFail: (srcs) => `部分数据缺失:${srcs} 抓取失败`,
    toastRefreshFailed: (msg) => `刷新失败:${msg}`,
    toastLoadFailed: (msg) => `加载失败:${msg}`,
    toastRateLimited: "请求过于频繁,请稍后再试。",
    toastTranslateFailed: (msg) => `翻译失败:${msg}`,
  },

  ja: {
    pageTitle: "本日のニュース",
    loading: "読み込み中…",
    refresh: "更新",
    refreshing: "更新中…",

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

    headerStats: (count, time) =>
      `過去24時間の${count}件のニュースを表示 · 最終更新 ${time}`,
    headerNever: "未更新 — 「更新」をクリックしてニュースを読み込み",

    justNow: "たった今",
    timeAgo: (n, unit) => {
      const units = { m: "分前", h: "時間前", d: "日前" };
      return `${n}${units[unit] || ""}`;
    },

    emptyFiltered: "このフィルターに一致する記事はありません。",
    emptyNoData: "データなし — 「更新」をクリックして読み込み。",

    loadMore: (n) => `もっと見る(残り ${n} 件)`,

    toastAddedNew: (n) => `${n}件の新着ニュース`,
    toastNoNew: "新しいニュースはありません",
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
