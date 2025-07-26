let currentRoomId = null;

export function getCurrentRoomId() {
  return currentRoomId;
}

// ✅ モデル名整形関数を追加
function extractModelName(modelId) {
  if (!modelId) return "";
  const parts = modelId.split("/");
  const filename = parts[parts.length - 1];
  return filename.replace(/\.gguf$/, "");
}

export async function initRoomList() {
  const listEl = document.getElementById("room-list");
  listEl.innerHTML = "";

  try {
    const res = await fetch("/v1/chat/rooms");
    const result = await res.json();

    const rooms = Array.isArray(result?.data) ? result.data : [];
    if (!Array.isArray(rooms)) throw new Error("ルーム一覧が不正な形式です");

    rooms.forEach((room) => {
      const wrapper = document.createElement("div");
      wrapper.className = "room-item-wrapper";

      const btn = document.createElement("button");
      btn.textContent = room.name;

      btn.className = "sidebar-button";
      btn.dataset.roomId = room.id;

      if (room.id === currentRoomId) {
        btn.classList.add("selected");
      }

      btn.onclick = () => selectRoom(room.id);
      wrapper.appendChild(btn);
      listEl.appendChild(wrapper);
    });

    if (!currentRoomId && rooms.length > 0) {
      selectRoom(rooms[0].id);
    }
  } catch (e) {
    console.error("ルーム一覧取得失敗:", e);
  }
}

export async function selectRoom(roomId) {
  currentRoomId = roomId;
  const buttons = document.querySelectorAll(".room-button, .sidebar-button");
  buttons.forEach((btn) => {
    btn.classList.toggle("selected", btn.dataset.roomId === roomId);
  });

  await loadMessages(roomId);
}

export async function createRoom() {
  const name = prompt("新しいルーム名を入力してください");
  if (!name) return;

  try {
    const res = await fetch("/v1/chat/rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    const result = await res.json();
    const roomId = result?.data?.room_id;
    if (!roomId) throw new Error("ルームID取得失敗");

    await initRoomList();
    await selectRoom(roomId);
  } catch (e) {
    console.error("ルーム作成失敗:", e);
  }
}

export async function renameRoom() {
  const roomId = getCurrentRoomId();
  if (!roomId) {
    alert("ルームが選択されていません");
    return;
  }

  const newName = prompt("新しいルーム名を入力してください");
  if (!newName) return;

  try {
    const res = await fetch("/v1/chat/rooms/rename", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room_id: roomId, new_name: newName }),
    });
    const result = await res.json();
    if (!result?.success) throw new Error("ルーム名変更失敗");

    await initRoomList();
  } catch (e) {
    console.error("ルーム名変更失敗:", e);
  }
}

export async function deleteRoom() {
  const roomId = getCurrentRoomId();
  if (!roomId || !confirm("このルームを削除しますか？")) return;

  try {
    const res = await fetch(`/v1/chat/rooms/${roomId}`, {
      method: "DELETE",
    });
    const result = await res.json();
    if (!result?.success) throw new Error("ルーム削除失敗");

    currentRoomId = null;
    await initRoomList();
  } catch (e) {
    console.error("ルーム削除失敗:", e);
  }
}

export async function loadMessages(roomId) {
  const container = document.getElementById("chat-messages");
  container.innerHTML = "";

  try {
    const res = await fetch(`/v1/chat/messages/${roomId}`);
    if (!res.ok) throw new Error(`status=${res.status}`);
    const result = await res.json();
    const messages = Array.isArray(result?.data) ? result.data : [];

    messages.forEach((msg) => {
      const wrapper = document.createElement("div");
      wrapper.className = msg.role;

      const bubble = document.createElement("div");
      bubble.className = "bubble";

      if (msg.role === "assistant" && msg.model) {
        const modelTag = document.createElement("div");
        modelTag.className = "model-name";
        modelTag.textContent = extractModelName(msg.model); // ✅ 修正点
        bubble.appendChild(modelTag);
      }

      const text = document.createElement("div");
      text.className = "message-text";
      text.textContent = msg.content;
      bubble.appendChild(text);

      wrapper.appendChild(bubble);
      container.appendChild(wrapper);
    });

    container.scrollTop = container.scrollHeight;
  } catch (e) {
    console.warn("メッセージ取得失敗:", e);
  }
}



















