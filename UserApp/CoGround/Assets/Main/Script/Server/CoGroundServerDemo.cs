using System;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// CoGroundServerClient の動作確認用。接続したら system.ping を送り、state.updated をログに出す。
/// インスペクタの右上メニュー (⋮) から各操作を試せる。
/// </summary>
public class CoGroundServerDemo : MonoBehaviour
{
    [SerializeField] private CoGroundServerClient client;
    [SerializeField] private bool pingOnConnect = true;

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;

    void OnEnable()
    {
        if (Client == null) { Debug.LogWarning("[CoGroundServerDemo] CoGroundServerClient が無い"); return; }
        Client.Connected += OnConnected;
        Client.StateUpdated += OnStateUpdated;
    }

    void OnDisable()
    {
        if (Client == null) return;
        Client.Connected -= OnConnected;
        Client.StateUpdated -= OnStateUpdated;
    }

    void OnConnected()
    {
        if (pingOnConnect) Ping();
    }

    void OnStateUpdated(JObject state)
    {
        var objects = state["scene"]?["objects"] as JArray;
        Debug.Log($"[CoGroundServerDemo] state v{state["version"]}: objects={objects?.Count ?? 0}");
    }

    [ContextMenu("Ping")]
    public async void Ping()
    {
        try
        {
            var result = await Client.RequestAsync("system.ping");
            Debug.Log($"[CoGroundServerDemo] pong: {result}");
        }
        catch (Exception e) { Debug.LogWarning($"[CoGroundServerDemo] ping failed: {e.Message}"); }
    }

    [ContextMenu("Count (stream)")]
    public async void Count()
    {
        try
        {
            var result = await Client.RequestAsync(
                "debug.count", new { count = 5, interval = 0.3 },
                onStream: data => Debug.Log($"[CoGroundServerDemo] stream: {data["i"]}/{data["of"]}"));
            Debug.Log($"[CoGroundServerDemo] count done: {result}");
        }
        catch (Exception e) { Debug.LogWarning($"[CoGroundServerDemo] count failed: {e.Message}"); }
    }

    [ContextMenu("Send Test Scene (this transform)")]
    public async void SendTestScene()
    {
        var scene = new JObject
        {
            ["objects"] = new JArray
            {
                new JObject
                {
                    ["id"] = name,
                    ["category"] = "cup",
                    ["position"] = CoGroundServerClient.ToJson(transform.position),
                    ["rotation"] = CoGroundServerClient.ToJson(transform.rotation),
                    ["size"] = CoGroundServerClient.ToJson(transform.lossyScale),
                },
            },
        };
        try
        {
            var result = await Client.RequestAsync("scene.update", scene);
            Debug.Log($"[CoGroundServerDemo] scene.update: {result}");
        }
        catch (CoGroundRpcException e) { Debug.LogWarning($"[CoGroundServerDemo] scene.update failed: {e.Message} {e.Details}"); }
    }

    [ContextMenu("Send Log Event")]
    public async void SendLog()
    {
        await Client.SendEventAsync("client.log", new { level = "info", message = $"hello from {SystemInfo.deviceModel}" });
    }
}
