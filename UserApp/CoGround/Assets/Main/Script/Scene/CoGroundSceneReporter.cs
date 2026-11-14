using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;

/// <summary>
/// シーンの物体を集めて、グラウンディングサーバーに scene.update で送る。
///
/// ■ 物体の出どころ
///   - Include Simulation Objects: シーン内の CoGroundSceneObject (シミュレーションの真値) をすべて送る
///   - Extra Sources: ICoGroundSceneSource を実装したコンポーネント (後で作る検出器など)
///   どちらも SceneObjectDto を出すので、サーバーから見ると同じ形で届く。
///
/// ■ 送るタイミング
///   接続したとき、Interval 秒ごと (中身が変わったときだけ)、ContextMenu の "Send Scene Now"。
/// </summary>
public class CoGroundSceneReporter : MonoBehaviour
{
    [SerializeField] CoGroundServerClient client;
    [SerializeField] bool includeSimulationObjects = true;
    [Tooltip("ICoGroundSceneSource を実装したコンポーネント")]
    [SerializeField] List<MonoBehaviour> extraSources = new List<MonoBehaviour>();
    [Tooltip("中身が変わったか確かめる間隔 [秒] (0 以下なら自動では送らない)")]
    [SerializeField] float interval = 0.5f;
    [Tooltip("この距離 [m] より小さい動きは変化とみなさない")]
    [SerializeField] float positionResolution = 0.005f;
    [SerializeField] bool logSends = false;

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;

    string lastSentKey;
    float nextCheck;
    bool sending;

    CoGroundServerClient subscribed;

    void Start()
    {
        // CoGroundServerClient.Instance は Awake で決まるので、Start で購読する
        subscribed = Client;
        if (subscribed != null) subscribed.Connected += OnConnected;
        else Debug.LogWarning("[CoGroundSceneReporter] CoGroundServerClient が見つからない", this);
    }

    void OnDestroy()
    {
        if (subscribed != null) subscribed.Connected -= OnConnected;
    }

    void OnConnected()
    {
        lastSentKey = null;
        Send();
    }

    void Update()
    {
        if (interval <= 0f || Time.time < nextCheck) return;
        nextCheck = Time.time + interval;
        Send();
    }

    public SceneSnapshotDto BuildSnapshot()
    {
        var snapshot = new SceneSnapshotDto { CapturedAt = Time.time };
        if (includeSimulationObjects)
            foreach (var o in CoGroundSceneObject.All) o.CollectObjects(snapshot.Objects);
        foreach (var s in extraSources)
        {
            if (s is ICoGroundSceneSource source && s.isActiveAndEnabled) source.CollectObjects(snapshot.Objects);
            else if (s != null && !(s is ICoGroundSceneSource))
                Debug.LogWarning($"[CoGroundSceneReporter] {s.name} は ICoGroundSceneSource を実装していない", s);
        }
        return snapshot;
    }

    [ContextMenu("Send Scene Now")]
    public void SendNow()
    {
        lastSentKey = null;
        Send();
    }

    async void Send()
    {
        var c = Client;
        if (sending || c == null || !c.IsConnected) return;

        var snapshot = BuildSnapshot();
        var key = ChangeKey(snapshot);
        if (key == lastSentKey) return;

        sending = true;
        try
        {
            var result = await c.RequestAsync("scene.update", snapshot);
            lastSentKey = key;
            if (logSends) Debug.Log($"[CoGroundSceneReporter] scene.update: {result}");
        }
        catch (CoGroundRpcException e)
        {
            Debug.LogWarning($"[CoGroundSceneReporter] scene.update failed: {e.Message} {e.Details}");
        }
        finally { sending = false; }
    }

    /// <summary>変化の判定用。時刻を除き、位置を positionResolution、回転を 0.001 で丸めた JSON</summary>
    string ChangeKey(SceneSnapshotDto snapshot)
    {
        var copy = JsonConvert.DeserializeObject<SceneSnapshotDto>(JsonConvert.SerializeObject(snapshot));
        copy.CapturedAt = null;
        foreach (var o in copy.Objects)
        {
            o.Observation.LastSeen = null;
            Round(o.Position, positionResolution);
            Round(o.Rotation, 0.001f);
            if (o.PlaceZone != null) Round(o.PlaceZone.Center, positionResolution);
        }
        return JsonConvert.SerializeObject(copy);
    }

    static void Round(float[] v, float step)
    {
        if (v == null || step <= 0f) return;
        for (int i = 0; i < v.Length; i++) v[i] = Mathf.Round(v[i] / step) * step;
    }
}
