import { loadGlobalConfig, updateGlobalConfig } from "./config.js";
import { initModelSelect } from "./model-api.js";
import { initVoiceSettings } from "./voice-api.js";
import {
  initRoomList,
  createRoom,
  renameRoom,
  deleteRoom,
} from "./room-api.js";
import { initChatEvents } from "./chat-events.js";
import { initPromptSelect } from "./prompt-api.js";

window.addEventListener("DOMContentLoaded", async () => {
  console.log("✅ DOMContentLoaded 開始");

  await loadGlobalConfig();
  console.log("✅ config 読込完了");

  await initModelSelect();
  console.log("✅ モデル初期化完了");

  await initPromptSelect();
  console.log("✅ プロンプト初期化完了");

  await initVoiceSettings();
  console.log("✅ 話者初期化完了");

  await initRoomList();
  console.log("✅ ルーム初期化完了");

  document.getElementById("new-room-btn").onclick = createRoom;
  document.getElementById("rename-room-btn").onclick = renameRoom;
  document.getElementById("delete-room-btn").onclick = deleteRoom;

  initChatEvents();
  console.log("✅ チャットイベント登録完了");

  // ✅ モデル変更時にkey, value形式で即時反映
  const modelSelect = document.getElementById("modelSelect");
  if (modelSelect) {
    modelSelect.addEventListener("change", () => {
      updateGlobalConfig("model", modelSelect.value);
    });
  }

  setTimeout(() => {
    console.log("ストリーミング表示準備完了");
  }, 1000);
});

