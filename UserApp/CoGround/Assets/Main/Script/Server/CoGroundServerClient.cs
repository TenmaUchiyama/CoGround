using System;
using System.Collections.Generic;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// グラウンディングサーバー (Backend/grounding_server, FastAPI) との WebSocket 接続。
/// プロトコルの詳細は Backend/grounding_server/README.md。
///
/// ■ 使い方
///   シーンに 1 つ置き、Server Url を設定する (Editor: ws://127.0.0.1:8000/ws、Quest: ws://<Windows の LAN IP>:8000/ws)。
///
///   // 要求→応答 (REST のような使い方)
///   JToken result = await CoGroundServerClient.Instance.RequestAsync("system.ping");
///
///   // 要求→途中経過 (stream) ×N→応答
///   await client.RequestAsync("debug.count", new { count = 5 }, onStream: d => Debug.Log(d));
///
///   // サーバーからの通知 (event)
///   client.StateUpdated += state => { ... };        // 全体状態 (state.updated)
///   client.On("some.event", data => { ... });
///
/// ■ スレッド
///   Unity の SynchronizationContext の上で動くので、コールバックも await の続きもメインスレッドで実行される。
///
/// ■ 接続が切れたとき
///   自動で再接続する。再接続するとサーバーが最新の全体状態 (state.updated) を送ってくるので、
///   StateUpdated だけ見ていれば取りこぼしは気にしなくてよい。処理中の要求は "disconnected" で失敗する。
///
/// ■ JSON
///   params は匿名型 (new { count = 5 }) か JObject で渡す。Vector3 / Quaternion は
///   そのままだと Newtonsoft で直列化できないので ToJson() で [x, y, z] / [x, y, z, w] にする。
/// </summary>
public class CoGroundServerClient : MonoBehaviour
{
    [Tooltip("Editor: ws://127.0.0.1:8000/ws / Quest: ws://<Windows の LAN IP>:8000/ws")]
    [SerializeField] private string serverUrl = "ws://127.0.0.1:8000/ws";
    [SerializeField] private bool connectOnStart = true;

    [Header("Reconnect")]
    [SerializeField] private float reconnectDelayMin = 1f;
    [SerializeField] private float reconnectDelayMax = 10f;

    [Header("Requests")]
    [Tooltip("応答を待つ既定の秒数 (0 以下なら待ち続ける)。長い処理は RequestAsync の timeout で個別に延ばす")]
    [SerializeField] private float defaultTimeoutSeconds = 30f;

    [Header("Debug")]
    [SerializeField] private bool logMessages = false;

    public static CoGroundServerClient Instance { get; private set; }

    public string ServerUrl { get => serverUrl; set => serverUrl = value; }
    public bool IsConnected => socket != null && socket.State == WebSocketState.Open;
    /// <summary>session.welcome で受け取ったセッション ID (未接続なら null)</summary>
    public string SessionId { get; private set; }
    /// <summary>最後に受け取った全体状態 (state.updated の data)</summary>
    public JObject LatestState { get; private set; }
    public long StateVersion { get; private set; } = -1;

    public event Action Connected;
    public event Action Disconnected;
    /// <summary>すべての event (name, data)</summary>
    public event Action<string, JToken> EventReceived;
    /// <summary>state.updated (全体状態)</summary>
    public event Action<JObject> StateUpdated;

    public static readonly JsonSerializer Serializer = JsonSerializer.CreateDefault();

    class Pending
    {
        public TaskCompletionSource<JToken> Tcs;
        public Action<JToken> OnStream;
    }

    readonly Dictionary<string, Pending> pending = new Dictionary<string, Pending>();
    readonly Dictionary<string, List<Action<JToken>>> eventHandlers = new Dictionary<string, List<Action<JToken>>>();
    readonly SemaphoreSlim sendLock = new SemaphoreSlim(1, 1);
    ClientWebSocket socket;
    CancellationTokenSource lifetime;
    int nextId;

    // ------------------------------------------------------------------ lifecycle

    void Awake()
    {
        if (Instance != null && Instance != this)
            Debug.LogWarning("[CoGroundServer] CoGroundServerClient が複数ある。後のものを Instance にする");
        Instance = this;
    }

    void Start()
    {
        if (connectOnStart) Connect();
    }

    void OnDestroy()
    {
        Disconnect();
        if (Instance == this) Instance = null;
    }

    public void Connect()
    {
        if (lifetime != null) return;
        lifetime = new CancellationTokenSource();
        _ = RunAsync(lifetime.Token);
    }

    public void Disconnect()
    {
        if (lifetime == null) return;
        lifetime.Cancel();
        lifetime.Dispose();
        lifetime = null;
        try { socket?.Abort(); } catch (Exception) { }
    }

    async Task RunAsync(CancellationToken ct)
    {
        float delay = reconnectDelayMin;
        while (!ct.IsCancellationRequested)
        {
            bool opened = false;
            using (var ws = new ClientWebSocket())
            {
                socket = ws;
                try
                {
                    await ws.ConnectAsync(new Uri(serverUrl), ct);
                    opened = true;
                    delay = reconnectDelayMin;
                    Debug.Log($"[CoGroundServer] connected: {serverUrl}");
                    SafeInvoke(Connected);
                    await ReceiveLoopAsync(ws, ct);
                }
                catch (OperationCanceledException) when (ct.IsCancellationRequested) { }
                catch (Exception e)
                {
                    if (opened) Debug.LogWarning($"[CoGroundServer] connection lost: {e.Message}");
                    else Debug.LogWarning($"[CoGroundServer] cannot connect to {serverUrl}: {e.Message} (retry in {delay:0.#}s)");
                }
                finally
                {
                    if (socket == ws) socket = null;
                    SessionId = null;
                    FailAllPending("disconnected", "Connection to the server was lost");
                    if (opened)
                    {
                        Debug.Log("[CoGroundServer] disconnected");
                        SafeInvoke(Disconnected);
                    }
                }
            }

            if (ct.IsCancellationRequested) break;
            try { await Task.Delay(TimeSpan.FromSeconds(delay), ct); }
            catch (OperationCanceledException) { break; }
            delay = Mathf.Min(delay * 2f, reconnectDelayMax);
        }
    }

    async Task ReceiveLoopAsync(ClientWebSocket ws, CancellationToken ct)
    {
        var buffer = new byte[16 * 1024];
        using (var message = new MemoryStream())
        {
            while (ws.State == WebSocketState.Open && !ct.IsCancellationRequested)
            {
                message.SetLength(0);
                WebSocketReceiveResult r;
                do
                {
                    r = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), ct);
                    if (r.MessageType == WebSocketMessageType.Close)
                    {
                        try { await ws.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "", CancellationToken.None); }
                        catch (Exception) { }
                        return;
                    }
                    message.Write(buffer, 0, r.Count);
                } while (!r.EndOfMessage);

                HandleMessage(Encoding.UTF8.GetString(message.GetBuffer(), 0, (int)message.Length));
            }
        }
    }

    // ------------------------------------------------------------------ receive

    void HandleMessage(string text)
    {
        if (logMessages) Debug.Log($"[CoGroundServer] <= {text}");

        JObject msg;
        try { msg = JObject.Parse(text); }
        catch (JsonException e)
        {
            Debug.LogWarning($"[CoGroundServer] JSON として読めない: {e.Message}");
            return;
        }

        switch ((string)msg["type"])
        {
            case "response":
            {
                var id = (string)msg["id"];
                if (id == null || !pending.TryGetValue(id, out var p)) return; // タイムアウト済みなど
                pending.Remove(id);
                if ((bool?)msg["ok"] == true)
                {
                    p.Tcs.TrySetResult(msg["result"]);
                }
                else
                {
                    var err = msg["error"] as JObject;
                    p.Tcs.TrySetException(new CoGroundRpcException(
                        (string)err?["code"] ?? "unknown", (string)err?["message"] ?? "", err?["details"]));
                }
                break;
            }
            case "stream":
            {
                var id = (string)msg["id"];
                if (id != null && pending.TryGetValue(id, out var p) && p.OnStream != null)
                {
                    try { p.OnStream(msg["data"]); }
                    catch (Exception e) { Debug.LogException(e); }
                }
                break;
            }
            case "event":
                HandleEvent((string)msg["event"], msg["data"]);
                break;
            default:
                Debug.LogWarning($"[CoGroundServer] 知らない type: {msg["type"]}");
                break;
        }
    }

    void HandleEvent(string name, JToken data)
    {
        if (name == null) return;

        if (name == "session.welcome")
        {
            SessionId = (string)data?["session_id"];
            Debug.Log($"[CoGroundServer] session {SessionId} (server {data?["server_version"]}, protocol {data?["protocol_version"]})");
        }
        else if (name == "session.error")
        {
            Debug.LogWarning($"[CoGroundServer] server error: {data}");
        }
        else if (name == "state.updated" && data is JObject state)
        {
            LatestState = state;
            StateVersion = (long?)state["version"] ?? -1;
            try { StateUpdated?.Invoke(state); }
            catch (Exception e) { Debug.LogException(e); }
        }

        try { EventReceived?.Invoke(name, data); }
        catch (Exception e) { Debug.LogException(e); }

        if (eventHandlers.TryGetValue(name, out var handlers))
        {
            foreach (var h in handlers.ToArray())
            {
                try { h(data); }
                catch (Exception e) { Debug.LogException(e); }
            }
        }
    }

    // ------------------------------------------------------------------ public API

    /// <summary>
    /// 要求を送り、応答の result を返す。失敗は CoGroundRpcException (Code で分岐する)。
    /// onStream には response より前に届く途中経過 (stream) が渡される。
    /// cancellationToken をキャンセルするとサーバーに cancel を送り、"cancelled" で失敗する。
    /// </summary>
    public async Task<JToken> RequestAsync(
        string method,
        object parameters = null,
        Action<JToken> onStream = null,
        TimeSpan? timeout = null,
        CancellationToken cancellationToken = default)
    {
        var ws = socket;
        if (ws == null || ws.State != WebSocketState.Open)
            throw new CoGroundRpcException("not_connected", "サーバーに接続していない");

        var id = "u-" + (++nextId);
        var p = new Pending { Tcs = new TaskCompletionSource<JToken>(), OnStream = onStream };
        pending[id] = p;

        var msg = new JObject
        {
            ["type"] = "request",
            ["id"] = id,
            ["method"] = method,
            ["params"] = parameters == null ? new JObject() : JToken.FromObject(parameters, Serializer),
        };
        try { await SendAsync(ws, msg); }
        catch (Exception)
        {
            pending.Remove(id);
            throw;
        }

        var limit = timeout ?? (defaultTimeoutSeconds > 0 ? TimeSpan.FromSeconds(defaultTimeoutSeconds) : Timeout.InfiniteTimeSpan);
        using (var timer = new CancellationTokenSource())
        using (cancellationToken.Register(() => _ = SendCancelAsync(id)))
        {
            var finished = await Task.WhenAny(p.Tcs.Task, Task.Delay(limit, timer.Token));
            if (finished != p.Tcs.Task)
            {
                pending.Remove(id);
                _ = SendCancelAsync(id);
                throw new CoGroundRpcException("timeout", $"{method} の応答が {limit.TotalSeconds:0.#} 秒以内に来なかった");
            }
            timer.Cancel();
            return await p.Tcs.Task;
        }
    }

    public async Task<T> RequestAsync<T>(
        string method,
        object parameters = null,
        Action<JToken> onStream = null,
        TimeSpan? timeout = null,
        CancellationToken cancellationToken = default)
    {
        var result = await RequestAsync(method, parameters, onStream, timeout, cancellationToken);
        return result == null || result.Type == JTokenType.Null ? default : result.ToObject<T>(Serializer);
    }

    /// <summary>応答のいらない通知を送る (例: client.log)。未接続なら false。</summary>
    public async Task<bool> SendEventAsync(string name, object data = null)
    {
        var ws = socket;
        if (ws == null || ws.State != WebSocketState.Open) return false;
        var msg = new JObject
        {
            ["type"] = "event",
            ["event"] = name,
            ["data"] = data == null ? new JObject() : JToken.FromObject(data, Serializer),
        };
        await SendAsync(ws, msg);
        return true;
    }

    public void On(string eventName, Action<JToken> handler)
    {
        if (!eventHandlers.TryGetValue(eventName, out var list))
            eventHandlers[eventName] = list = new List<Action<JToken>>();
        list.Add(handler);
    }

    public void Off(string eventName, Action<JToken> handler)
    {
        if (eventHandlers.TryGetValue(eventName, out var list)) list.Remove(handler);
    }

    // ------------------------------------------------------------------ JSON helpers

    public static JArray ToJson(Vector3 v) => new JArray(v.x, v.y, v.z);
    public static JArray ToJson(Quaternion q) => new JArray(q.x, q.y, q.z, q.w);

    public static Vector3 ToVector3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
    public static Quaternion ToQuaternion(JToken t) => new Quaternion((float)t[0], (float)t[1], (float)t[2], (float)t[3]);

    // ------------------------------------------------------------------ send

    async Task SendAsync(ClientWebSocket ws, JObject msg)
    {
        var text = msg.ToString(Formatting.None);
        if (logMessages) Debug.Log($"[CoGroundServer] => {text}");
        var bytes = Encoding.UTF8.GetBytes(text);
        await sendLock.WaitAsync();
        try
        {
            await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);
        }
        finally
        {
            sendLock.Release();
        }
    }

    async Task SendCancelAsync(string id)
    {
        var ws = socket;
        if (ws == null || ws.State != WebSocketState.Open) return;
        try { await SendAsync(ws, new JObject { ["type"] = "cancel", ["id"] = id }); }
        catch (Exception e) { Debug.LogWarning($"[CoGroundServer] cancel を送れない: {e.Message}"); }
    }

    void FailAllPending(string code, string message)
    {
        if (pending.Count == 0) return;
        var list = new List<Pending>(pending.Values);
        pending.Clear();
        foreach (var p in list) p.Tcs.TrySetException(new CoGroundRpcException(code, message));
    }

    static void SafeInvoke(Action action)
    {
        try { action?.Invoke(); }
        catch (Exception e) { Debug.LogException(e); }
    }
}

/// <summary>サーバーが返した error (または not_connected / timeout / disconnected)。</summary>
public class CoGroundRpcException : Exception
{
    public string Code { get; }
    public JToken Details { get; }

    public CoGroundRpcException(string code, string message, JToken details = null)
        : base($"[{code}] {message}")
    {
        Code = code;
        Details = details;
    }
}
