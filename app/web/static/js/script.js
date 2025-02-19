// static/js/script.js

// ページ読み込み後に動作するサンプルコード
document.addEventListener("DOMContentLoaded", function() {
    console.log("ページが読み込まれました。");

    // 例: 設定フォームの送信イベントハンドラ
    const settingsForm = document.getElementById("settingsForm");
    if (settingsForm) {
        settingsForm.addEventListener("submit", function(event) {
            event.preventDefault();
            const newSetting = document.getElementById("newSetting").value;
            console.log("新しい設定値:", newSetting);
            // ここで AJAX リクエストを使い、API 経由で設定を更新する処理を追加可能
            alert("設定更新の処理は未実装です。");
        });
    }

    // 例: ログ更新ボタンのイベントハンドラ
    const refreshLogsButton = document.getElementById("refreshLogs");
    if (refreshLogsButton) {
        refreshLogsButton.addEventListener("click", function() {
            fetch("/api/logs")
                .then(response => response.json())
                .then(data => {
                    document.getElementById("logContent").textContent = data.logs || "ログがありません。";
                })
                .catch(error => {
                    console.error("ログ取得エラー:", error);
                    alert("ログの取得に失敗しました。");
                });
        });
    }
});
