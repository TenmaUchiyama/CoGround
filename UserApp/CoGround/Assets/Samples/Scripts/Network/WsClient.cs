using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

// ServerSideApp (Python) と WebSocket 1 本で通信するクライアント。
// プロトコルは ServerSideApp/README.md を参照。
//
//   var body = await ws.RequestAsync("/hello/quest");
//   var sub  = ws.Subscribe("/clock", null, data => ..., (status, err) => ...);
//   sub.Dispose();  // unsubscribe
//
// コールバックと await の続きはすべてメインスレッドで実行される。
public class WsClient : MonoBehaviour {
    [SerializeField] string url = "ws://192.168.1.152:8765";
    [SerializeField] bool connectOnStart = true;
    [SerializeField] float reconnectInterval = 3f;
    [SerializeField] float requestTimeout = 10f;

    public bool IsConnected => socket?.State == WebSocketState.Open;
    public event Action Connected;
    public event Action Disconnected;

    ClientWebSocket socket;
    CancellationTokenSource lifetime;
    readonly SemaphoreSlim sendLock = new(1, 1);
    readonly ConcurrentQueue<Action> mainThread = new();
    readonly Dictionary<string, TaskCompletionSource<JToken>> pending = new();
    readonly Dictionary<string, Subscription> subscriptions = new();
    readonly Dictionary<string, Action<JToken>> eventHandlers = new();
    int nextId;

    public string Url { get => url; set => url = value; }

    void Start() {
        if (connectOnStart) Connect();
    }

    void Update() {
        while (mainThread.TryDequeue(out var action)) {
            try { action(); } catch (Exception e) { Debug.LogException(e); }
        }
    }

    void OnDestroy() => Close();

    public void Connect() {
        Close();
        lifetime = new CancellationTokenSource();
        _ = ConnectLoop(lifetime.Token);
    }

    public void Close() {
        lifetime?.Cancel();
        lifetime = null;
        socket?.Dispose();
        socket = null;
    }

    // ---- リクエスト / レスポンス ----

    public async Task<JToken> RequestAsync(string path, object body = null) {
        var id = NewId();
        var tcs = new TaskCompletionSource<JToken>();
        pending[id] = tcs;
        try {
            await SendAsync(new { type = "request", id, path, body });
        } catch {
            pending.Remove(id);
            throw;
        }
        var timeout = Task.Delay(TimeSpan.FromSeconds(requestTimeout));
        if (await Task.WhenAny(tcs.Task, timeout) == timeout) {
            pending.Remove(id);
            throw new WsApiException(408, $"timeout: {path}");
        }
        return await tcs.Task;
    }

    public async Task<T> RequestAsync<T>(string path, object body = null) =>
        (await RequestAsync(path, body)).ToObject<T>();

    // ---- ストリーム ----

    public Subscription Subscribe(string path, object body, Action<JToken> onData, Action<int, string> onEnd = null) {
        var sub = new Subscription(this, NewId(), path, onData, onEnd);
        subscriptions[sub.Id] = sub;
        _ = SendAsync(new { type = "subscribe", id = sub.Id, path, body }).ContinueWith(t => {
            if (t.IsFaulted) mainThread.Enqueue(() => EndSubscription(sub.Id, 0, "send failed"));
        });
        return sub;
    }

    // ---- サーバーからの通知 (conn.push) ----

    public void On(string path, Action<JToken> handler) => eventHandlers[path] = handler;
    public void Off(string path) => eventHandlers.Remove(path);

    // ---- 内部 ----

    internal void Unsubscribe(string id) {
        if (subscriptions.ContainsKey(id) && IsConnected) _ = SendAsync(new { type = "unsubscribe", id });
    }

    string NewId() => (++nextId).ToString();

    async Task SendAsync(object msg) {
        var ws = socket;
        if (ws == null || ws.State != WebSocketState.Open) throw new WsApiException(0, "not connected");
        var bytes = Encoding.UTF8.GetBytes(JsonConvert.SerializeObject(msg));
        await sendLock.WaitAsync();
        try {
            await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);
        } finally {
            sendLock.Release();
        }
    }

    async Task ConnectLoop(CancellationToken ct) {
        while (!ct.IsCancellationRequested) {
            var ws = new ClientWebSocket();
            socket = ws;
            try {
                await ws.ConnectAsync(new Uri(url), ct);
                mainThread.Enqueue(() => { Debug.Log($"[WsClient] connected: {url}"); Connected?.Invoke(); });
                await ReceiveLoop(ws, ct);
            } catch (OperationCanceledException) {
                return;
            } catch (Exception e) {
                mainThread.Enqueue(() => Debug.LogWarning($"[WsClient] {url}: {e.Message}"));
            }
            mainThread.Enqueue(OnSocketClosed);
            try { await Task.Delay(TimeSpan.FromSeconds(reconnectInterval), ct); } catch (OperationCanceledException) { return; }
        }
    }

    async Task ReceiveLoop(ClientWebSocket ws, CancellationToken ct) {
        var buffer = new byte[64 * 1024];
        var message = new List<byte>();
        while (ws.State == WebSocketState.Open) {
            var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), ct);
            if (result.MessageType == WebSocketMessageType.Close) return;
            message.AddRange(new ArraySegment<byte>(buffer, 0, result.Count));
            if (!result.EndOfMessage) continue;
            var text = Encoding.UTF8.GetString(message.ToArray());
            message.Clear();
            mainThread.Enqueue(() => Dispatch(text));
        }
    }

    void Dispatch(string text) {
        var msg = JObject.Parse(text);
        var type = (string)msg["type"];
        var id = (string)msg["id"];
        var status = (int?)msg["status"] ?? 0;
        var error = (string)msg["error"] ?? (string)msg["message"];

        switch (type) {
            case "response":
                if (id != null && pending.Remove(id, out var tcs)) {
                    if (status == 200) tcs.TrySetResult(msg["body"]);
                    else tcs.TrySetException(new WsApiException(status, error));
                }
                break;
            case "stream":
                if (id != null && subscriptions.TryGetValue(id, out var sub)) sub.OnData?.Invoke(msg["body"]);
                break;
            case "stream_end":
                EndSubscription(id, status, error);
                break;
            case "event":
                if (eventHandlers.TryGetValue((string)msg["path"] ?? "", out var handler)) handler(msg["body"]);
                break;
            case "error":
                Debug.LogWarning($"[WsClient] server error {status}: {error}");
                if (id != null && pending.Remove(id, out var t)) t.TrySetException(new WsApiException(status, error));
                break;
        }
    }

    void EndSubscription(string id, int status, string error) {
        if (id != null && subscriptions.Remove(id, out var sub)) sub.OnEnd?.Invoke(status, error);
    }

    void OnSocketClosed() {
        foreach (var tcs in pending.Values) tcs.TrySetException(new WsApiException(0, "disconnected"));
        pending.Clear();
        var subs = new List<Subscription>(subscriptions.Values);
        subscriptions.Clear();
        foreach (var s in subs) s.OnEnd?.Invoke(0, "disconnected");
        Disconnected?.Invoke();
    }

    public sealed class Subscription : IDisposable {
        public string Id { get; }
        public string Path { get; }
        internal Action<JToken> OnData { get; }
        internal Action<int, string> OnEnd { get; }
        readonly WsClient client;

        internal Subscription(WsClient client, string id, string path, Action<JToken> onData, Action<int, string> onEnd) {
            this.client = client;
            Id = id;
            Path = path;
            OnData = onData;
            OnEnd = onEnd;
        }

        public void Dispose() => client.Unsubscribe(Id);
    }
}

public class WsApiException : Exception {
    // 0: 未接続・切断, 408: タイムアウト, それ以外はサーバーの status
    public int Status { get; }
    public WsApiException(int status, string message) : base($"{status}: {message}") => Status = status;
}
