using TMPro;
using UnityEngine;

// WsClient の使い方サンプル。接続したら /hello を呼び、/clock を購読してラベルに出す。
public class WsDemo : MonoBehaviour {
    [SerializeField] WsClient client;
    [SerializeField] TMP_Text label;

    WsClient.Subscription clock;
    string hello = "-";

    void OnEnable()  => client.Connected += OnConnected;
    void OnDisable() {
        client.Connected -= OnConnected;
        clock?.Dispose();
    }

    async void OnConnected() {
        try {
            var res = await client.RequestAsync("/hello/quest");
            hello = (string)res["message"];
        } catch (WsApiException e) {
            hello = $"error {e.Message}";
        }

        clock = client.Subscribe("/clock", new { interval = 0.5 },
            data => Show($"{hello}\nclock #{data["n"]}"),
            (status, error) => Show($"{hello}\nclock ended ({status} {error})"));
    }

    void Show(string text) {
        Debug.Log($"[WsDemo] {text}");
        if (label != null) label.text = text;
    }
}
