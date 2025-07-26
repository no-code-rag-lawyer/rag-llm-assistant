document.addEventListener("DOMContentLoaded", () => {
  const uploadForm = document.getElementById("uploadForm");
  const fileInput = document.getElementById("audioFile");
  const resultDiv = document.getElementById("result");

  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (fileInput.files.length === 0) {
      resultDiv.textContent = "音声ファイルを選択してください。";
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    resultDiv.textContent = "文字起こし中...";

    try {
      const response = await fetch("/v1/audio/transcribe", {
        method: "POST",
        body: formData
      });

      if (!response.ok) throw new Error("サーバーエラー");

      const data = await response.json();

      if (data.success) {
        resultDiv.textContent = `文字起こし結果:\n${data.text}`;
      } else {
        resultDiv.textContent = `エラー: ${data.error}`;
      }
    } catch (err) {
      resultDiv.textContent = `通信エラー: ${err.message}`;
    }
  });
});
