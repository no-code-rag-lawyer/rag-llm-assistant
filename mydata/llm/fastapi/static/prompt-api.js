import { getGlobalConfig, updateGlobalConfig } from "./config.js";

let prompts = [];

export async function fetchPrompts() {
  try {
    const res = await fetch("/v1/chat/prompt/list");
    const json = await res.json();

    if (json.success && Array.isArray(json.data)) {
      return json.data.map(p => ({
        id: p.id,
        name: p.name || p.id
      }));
    }

    console.warn("不明なプロンプト一覧形式:", json);
    return [];
  } catch (err) {
    console.error("プロンプト一覧取得失敗:", err);
    return [];
  }
}

export async function initPromptSelect() {
  const select = document.getElementById("promptSelect");
  if (!select) return;

  prompts = await fetchPrompts();
  select.innerHTML = "";

  for (const prompt of prompts) {
    const option = document.createElement("option");
    option.value = prompt.id;
    option.textContent = prompt.name;
    select.appendChild(option);
  }

  // ✅ localStorage優先で初期値設定
  const currentConfig = getGlobalConfig();
  const savedId = currentConfig.prompt_id;

  if (savedId && prompts.some(p => p.id === savedId)) {
    select.value = savedId;
  } else {
    const defaultId = prompts[0]?.id ?? "rag_default";
    select.value = defaultId;
    updateGlobalConfig("prompt_id", defaultId);
  }

  select.addEventListener("change", () => {
    updateGlobalConfig("prompt_id", select.value);
  });
}
