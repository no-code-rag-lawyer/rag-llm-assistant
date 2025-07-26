let globalConfig = {
  model: "",
  speaker_uuid: "",
  style_id: 0,
  prompt_id: "rag_default"
};

// ✅ localStorageから復元
const savedConfig = localStorage.getItem("globalConfig");
if (savedConfig) {
  try {
    const parsed = JSON.parse(savedConfig);
    globalConfig = { ...globalConfig, ...parsed };
  } catch (e) {
    console.warn("グローバル設定の復元失敗:", e);
  }
}

export function getGlobalConfig() {
  return { ...globalConfig };
}

export async function updateGlobalConfig(key, value) {
  if (!globalConfig.hasOwnProperty(key)) {
    console.warn(`無効なキーです: ${key}`);
    return;
  }

  globalConfig[key] = value;
  localStorage.setItem("globalConfig", JSON.stringify(globalConfig));

  try {
    console.log("送信する設定:", globalConfig); // ✅ デバッグ用
    await fetch("/v1/config/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(globalConfig),
    });
  } catch (err) {
    console.error("設定保存失敗:", err);
  }
}

export async function loadGlobalConfig() {
  try {
    const res = await fetch("/v1/config/");
    const data = await res.json();

    if (!data.success || typeof data.data !== "object") {
      throw new Error("設定の取得に失敗しました");
    }

    globalConfig = { ...globalConfig, ...data.data };
    localStorage.setItem("globalConfig", JSON.stringify(globalConfig));
  } catch (err) {
    console.error("設定読み込み失敗:", err);
  }
}




