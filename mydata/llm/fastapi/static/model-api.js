import { getGlobalConfig, updateGlobalConfig } from "./config.js";

let models = [];

export async function fetchModels() {
  try {
    const res = await fetch("/v1/model/list");
    const json = await res.json();

    if (json.success && Array.isArray(json.data)) {
      return json.data.map(m => {
        if (typeof m === "string") return { id: m, name: m };
        if (typeof m === "object" && m.id) return { id: m.id, name: m.name || m.id };
        return null;
      }).filter(Boolean);
    }

    console.warn("不明なモデル一覧形式:", json);
    return [];
  } catch (err) {
    console.error("モデル一覧取得失敗:", err);
    return [];
  }
}

export async function initModelSelect() {
  const select = document.getElementById("modelSelect");
  if (!select) return;

  models = await fetchModels();
  select.innerHTML = "";

  for (const model of models) {
    const option = document.createElement("option");
    option.value = model.id;
    option.textContent = model.name;
    select.appendChild(option);
  }

  // 現在の設定から初期値を反映
  const { model } = getGlobalConfig();
  if (model && models.some(m => m.id === model)) {
    select.value = model;
  } else {
    const defaultId = models[0]?.id ?? "";
    select.value = defaultId;
    updateGlobalConfig("model", defaultId); // ✅ 修正
  }

  // 選択変更時、model ID 文字列を即時送信
  select.addEventListener("change", () => {
    updateGlobalConfig("model", select.value); // ✅ 修正
  });
}
