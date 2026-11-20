using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// シーンの CoGroundPerson の位置を、グラウンディングサーバーに people.update で送る (既定で 0.2 秒ごと)。
///
/// サーバーは、最後の people.update から 2 秒 (COGROUND_PEOPLE_TIMEOUT) 経つと「人の位置が観測できていない」
/// とみなし、子供の近くで止まるルール (R4) があれば台車を止める。だから、人がいなくても送り続ける
/// (空のリスト = 「誰もいない」)。このコンポーネントを無効にすると送らなくなり、サーバーは観測なしとして扱う。
///
/// ■ 使い方
///   CoGroundServerClient と同じシーンの、どれかの GameObject に 1 つ付ける。
///   応答の held (台車を止めているか) は Held で読める。
/// </summary>
public class CoGroundPeopleReporter : MonoBehaviour
{
    [SerializeField] CoGroundServerClient client;
    [Tooltip("送る間隔 [s]。サーバーの観測の有効時間 (既定 2 秒) より十分短くする")]
    [SerializeField] float interval = 0.2f;
    [Tooltip("この観測を有効とみなす秒数。0 以下ならサーバーの既定 (2 秒) を使う")]
    [SerializeField] float validFor = 0f;
    [Tooltip("CoGroundPerson が 1 つも無いときも、空のリスト (誰もいない) を送る。切ると、人がいない間は「観測なし」になる")]
    [SerializeField] bool sendWhenEmpty = true;

    /// <summary>最後の応答で、サーバーが台車を止めていたか</summary>
    public bool Held { get; private set; }
    /// <summary>最後に送った人数 (まだ送っていなければ -1)</summary>
    public int LastSentCount { get; private set; } = -1;

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;
    float nextSend;
    bool sending;
    bool warned;

    void Update()
    {
        if (Time.unscaledTime < nextSend || sending) return;
        nextSend = Time.unscaledTime + Mathf.Max(0.05f, interval);
        var c = Client;
        if (c == null || !c.IsConnected) return;
        if (CoGroundPerson.All.Count == 0 && !sendWhenEmpty) return;
        Send(c);
    }

    async void Send(CoGroundServerClient c)
    {
        var people = new JArray();
        var seen = new HashSet<string>();
        foreach (var p in CoGroundPerson.All)
        {
            if (p == null) continue;
            if (!seen.Add(p.Id))
            {
                if (!warned) Debug.LogWarning($"[CoGroundPeopleReporter] 人の ID が重複している: {p.Id} (2 つ目は送らない)", p);
                warned = true;
                continue;
            }
            people.Add(new JObject
            {
                ["id"] = p.Id,
                ["kind"] = p.KindName,
                ["position"] = CoGroundServerClient.ToJson(p.transform.position),
            });
        }
        var args = new JObject { ["people"] = people };
        if (validFor > 0f) args["valid_for"] = validFor;

        sending = true;
        try
        {
            var result = await c.RequestAsync("people.update", args);
            Held = (bool?)result["held"] ?? false;
            LastSentCount = people.Count;
        }
        catch (CoGroundRpcException e)
        {
            // 切断中の失敗は毎回出さない (再接続したらまた送る)
            if (e.Code != "not_connected" && e.Code != "disconnected" && e.Code != "timeout")
                Debug.LogWarning($"[CoGroundPeopleReporter] people.update failed: {e.Message} {e.Details}", this);
        }
        finally { sending = false; }
    }
}
