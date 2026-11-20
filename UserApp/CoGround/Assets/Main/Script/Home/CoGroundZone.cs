using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// 住人が決めた床の範囲 (進入禁止の範囲など) を、グラウンディングサーバーに zones.define で送る。
/// 家庭ルール R2「夕方 6 時以降は、リビングのこのあたりに入るな」の「このあたり」。
/// サーバー側は Backend/grounding_server/coground_server/handlers/home.py。
///
/// ■ 使い方
///   空の GameObject に付け、角になる Transform を子に 3 つ以上置く (Corners が空なら子を順に使う)。
///   高さは使わない (床に投影した多角形になる)。角は一周する順に並べる。
///   接続したときと、角を動かしたときに送り直す。
///
/// ■ 言葉で登録したルールの「このあたり」を、この範囲で確定する (Confirm Pending Rules)
///   norms.compile が「範囲が言葉だけでは決まらない」と返したルールは pending_rules に入る。
///   Confirm Pending Rules を入れておくと、範囲の参照が 1 つだけのルールを、この領域で rules.confirm する。
///   解除時刻が言われていないルールは、Confirm Until (HH:MM) か Keep Open を決めておかないと確定できない
///   (サーバーは勝手に補わない)。
///
/// ■ 表示
///   床に輪郭を描く。台車がいま避けている領域 (execution.monitor.keepout) は Keepout Color にする。
/// </summary>
public class CoGroundZone : MonoBehaviour
{
    [SerializeField] CoGroundServerClient client;
    [Tooltip("領域の ID。ルールの対象 (target.id) で使う。空なら GameObject の名前")]
    [SerializeField] string zoneId = "";
    [Tooltip("呼び名。例: リビングの遊び場")]
    [SerializeField] string label = "";
    [Tooltip("角 (一周する順)。空なら子の Transform を順に使う")]
    [SerializeField] List<Transform> corners = new List<Transform>();

    [Header("送信")]
    [Tooltip("角が動いたかを調べる間隔 [s]")]
    [SerializeField] float checkInterval = 0.5f;
    [Tooltip("これより大きく動いたら送り直す [m]")]
    [SerializeField] float moveThreshold = 0.01f;
    [Tooltip("無効にしたとき・消したときに zones.remove を送る")]
    [SerializeField] bool removeOnDisable = false;

    [Header("登録の途中のルールを確定する")]
    [SerializeField] bool confirmPendingRules = false;
    [Tooltip("解除時刻 (HH:MM)。解除時刻が言われていないルールに使う。空なら渡さない")]
    [SerializeField] string confirmUntil = "";
    [Tooltip("解除時刻を決めないままにする (その日のうちは効き続ける) と、住人が決めた")]
    [SerializeField] bool keepOpen = false;

    [Header("表示")]
    [SerializeField] bool showOutline = true;
    [SerializeField] Color color = new Color(1f, 0.6f, 0.1f, 0.9f);
    [Tooltip("台車がいま避けている領域")]
    [SerializeField] Color keepoutColor = new Color(1f, 0.25f, 0.2f, 0.95f);
    [SerializeField] float lineWidth = 0.015f;
    [Tooltip("輪郭を描く高さ (床から) [m]")]
    [SerializeField] float outlineHeight = 0.01f;

    public string Id => string.IsNullOrWhiteSpace(zoneId) ? name : zoneId.Trim();
    /// <summary>サーバーに届いているか (最後の zones.define が成功した)</summary>
    public bool Sent { get; private set; }
    /// <summary>台車がいまこの領域を避けている</summary>
    public bool IsKeepout { get; private set; }

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;
    CoGroundServerClient subscribed;
    readonly List<Vector3> sentPoints = new List<Vector3>();
    readonly List<Vector3> points = new List<Vector3>();
    readonly HashSet<string> confirmTried = new HashSet<string>();
    LineRenderer outline;
    Material outlineMaterial;
    float nextCheck;
    bool sending;
    string sentId;

    void Start()
    {
        subscribed = Client;
        if (subscribed == null) { Debug.LogWarning("[CoGroundZone] CoGroundServerClient が見つからない", this); return; }
        subscribed.Connected += OnConnected;
        subscribed.StateUpdated += OnStateUpdated;
        if (subscribed.IsConnected) OnConnected();
        if (subscribed.LatestState != null) OnStateUpdated(subscribed.LatestState);
    }

    void OnDestroy()
    {
        if (subscribed != null)
        {
            subscribed.Connected -= OnConnected;
            subscribed.StateUpdated -= OnStateUpdated;
        }
        if (outlineMaterial != null) Destroy(outlineMaterial);
    }

    void OnEnable()
    {
        if (outline != null) outline.enabled = showOutline;
    }

    void OnDisable()
    {
        if (outline != null) outline.enabled = false;
        if (removeOnDisable) Remove();
    }

    void OnConnected()
    {
        // サーバーを立ち上げ直したあとは領域が消えているので、必ず送り直す
        Sent = false;
        sentPoints.Clear();
        confirmTried.Clear();
        nextCheck = 0f;
    }

    void Update()
    {
        CollectPoints(points);
        DrawOutline();
        if (Time.unscaledTime < nextCheck) return;
        nextCheck = Time.unscaledTime + checkInterval;
        if (sending || subscribed == null || !subscribed.IsConnected || points.Count < 3) return;
        if (!Sent || sentId != Id || Moved()) Send();
    }

    /// <summary>角を床に投影した点 (Unity ワールド座標、y = 0)。</summary>
    public void CollectPoints(List<Vector3> into)
    {
        into.Clear();
        if (corners.Count > 0)
        {
            foreach (var c in corners)
                if (c != null) into.Add(Flat(c.position));
        }
        else
        {
            for (int i = 0; i < transform.childCount; i++)
            {
                var c = transform.GetChild(i);
                if (c.gameObject.activeSelf && c.GetComponent<LineRenderer>() == null) into.Add(Flat(c.position));
            }
        }
    }

    static Vector3 Flat(Vector3 p) => new Vector3(p.x, 0f, p.z);

    bool Moved()
    {
        if (sentPoints.Count != points.Count) return true;
        for (int i = 0; i < points.Count; i++)
            if ((sentPoints[i] - points[i]).sqrMagnitude > moveThreshold * moveThreshold) return true;
        return false;
    }

    /// <summary>いまの範囲を zones.define で送る (同じ ID があれば置き換わる)。</summary>
    [ContextMenu("Send Zone")]
    public async void Send()
    {
        var c = Client;
        if (c == null || sending) return;
        CollectPoints(points);
        if (points.Count < 3) { Debug.LogWarning($"[CoGroundZone] {Id}: 角が 3 つ以上要る", this); return; }

        var id = Id;
        var snapshot = new List<Vector3>(points);
        var polygon = new JArray();
        foreach (var p in snapshot) polygon.Add(CoGroundServerClient.ToJson(p));
        var args = new JObject { ["id"] = id, ["label"] = string.IsNullOrWhiteSpace(label) ? id : label, ["polygon"] = polygon };

        sending = true;
        try
        {
            // ID を変えたときは、前の ID の領域を消す
            if (Sent && sentId != null && sentId != id)
            {
                try { await c.RequestAsync("zones.remove", new JObject { ["id"] = sentId }); }
                catch (CoGroundRpcException) { }
            }
            var result = await c.RequestAsync("zones.define", args);
            Sent = true;
            sentId = id;
            sentPoints.Clear();
            sentPoints.AddRange(snapshot);
            if (confirmPendingRules) ConfirmPending(result["pending_rules"] as JArray);
        }
        catch (CoGroundRpcException e)
        {
            Debug.LogWarning($"[CoGroundZone] zones.define {id} failed: {e.Message} {e.Details}", this);
        }
        finally { sending = false; }
    }

    /// <summary>この領域をサーバーから消す。</summary>
    [ContextMenu("Remove Zone")]
    public async void Remove()
    {
        var c = Client;
        if (c == null || !c.IsConnected || !Sent) return;
        var id = sentId ?? Id;
        Sent = false;
        sentPoints.Clear();
        try { await c.RequestAsync("zones.remove", new JObject { ["id"] = id }); }
        catch (CoGroundRpcException e) { Debug.LogWarning($"[CoGroundZone] zones.remove {id} failed: {e.Message}", this); }
    }

    void OnStateUpdated(JObject state)
    {
        var keepout = false;
        if (state["execution"]?["monitor"]?["keepout"] is JArray ids)
            foreach (var z in ids)
                if ((string)z == Id) keepout = true;
        IsKeepout = keepout;

        // 領域を送ったあとで言葉のルールが登録されたときも、ここで確定する
        if (confirmPendingRules && Sent) ConfirmPending(state["pending_rules"] as JArray);
    }

    /// <summary>
    /// 範囲の参照が 1 つだけの「登録の途中のルール」を、この領域で確定する。
    /// 同じルールには 1 回だけ試す (足りないものがあればサーバーが断るので、警告を出して終わり)。
    /// </summary>
    async void ConfirmPending(JArray pending)
    {
        var c = Client;
        if (pending == null || c == null) return;
        foreach (var p in pending)
        {
            var ruleId = (string)p["rule"]?["id"];
            var refs = p["pending_refs"] as JArray;
            if (ruleId == null || refs == null || refs.Count != 1) continue;
            if (!confirmTried.Add(ruleId)) continue;

            var args = new JObject
            {
                ["rule_id"] = ruleId,
                ["refs"] = new JObject { [(string)refs[0]["ref"]] = Id },
            };
            if (!string.IsNullOrWhiteSpace(confirmUntil)) args["until"] = confirmUntil.Trim();
            if (keepOpen) args["keep_open"] = true;
            try
            {
                var result = await c.RequestAsync("rules.confirm", args);
                Debug.Log($"[CoGroundZone] {Id}: ルール {ruleId} を確定した: {result["rule"]?["original_text"]}", this);
            }
            catch (CoGroundRpcException e)
            {
                Debug.LogWarning($"[CoGroundZone] rules.confirm {ruleId} failed: {e.Message} (解除時刻が要るなら Confirm Until か Keep Open を決める)", this);
            }
        }
    }

    void DrawOutline()
    {
        if (!showOutline || points.Count < 3)
        {
            if (outline != null) outline.enabled = false;
            return;
        }
        if (outline == null)
        {
            var go = new GameObject("Zone Outline");
            go.transform.SetParent(transform, false);
            outline = go.AddComponent<LineRenderer>();
            outline.useWorldSpace = true;
            outline.loop = true;
            outline.numCornerVertices = 2;
            outline.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            outline.receiveShadows = false;
            outlineMaterial = FetchGhost.MakeMaterial(color);
            outline.sharedMaterial = outlineMaterial;
        }
        outline.enabled = true;
        outline.startWidth = outline.endWidth = lineWidth;
        outlineMaterial.color = IsKeepout ? keepoutColor : color;
        outline.positionCount = points.Count;
        for (int i = 0; i < points.Count; i++)
            outline.SetPosition(i, points[i] + Vector3.up * outlineHeight);
    }

#if UNITY_EDITOR
    void OnDrawGizmos()
    {
        var pts = new List<Vector3>();
        CollectPoints(pts);
        if (pts.Count < 2) return;
        Gizmos.color = Application.isPlaying && IsKeepout ? keepoutColor : color;
        for (int i = 0; i < pts.Count; i++)
            Gizmos.DrawLine(pts[i], pts[(i + 1) % pts.Count]);
        UnityEditor.Handles.Label(pts[0] + Vector3.up * 0.05f, Id);
    }
#endif
}
