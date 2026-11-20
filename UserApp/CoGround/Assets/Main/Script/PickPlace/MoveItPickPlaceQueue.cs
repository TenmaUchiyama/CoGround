using System;
using System.Collections.Generic;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using UnityEngine;

/// <summary>
/// Pick &amp; Place の指令を順番に ROS (pick_place_server) へ送る。
/// pick_place_server は 1 度に 1 つしか受けないので、終わる (succeeded / failed / rejected) のを待って次を送る。
/// 同じ箱の指令がまだ送られずに待っているときは、新しい置き場所で上書きする。
///
/// シーンに置く必要はない (MoveItPickPlaceQueue.Instance で自動で作られる)。
/// </summary>
public class MoveItPickPlaceQueue : MonoBehaviour
{
    const string CommandTopic = "/coground/pick_place/command";
    const string StatusTopic = "/coground/pick_place/status";

    class Request
    {
        public MoveItPickable obj;
        public Vector3 bottomCenter;
        public Quaternion rotation;
        public Action<bool, string> done;
    }

    static MoveItPickPlaceQueue instance;

    public static MoveItPickPlaceQueue Instance
    {
        get
        {
            if (instance == null)
            {
                instance = FindAnyObjectByType<MoveItPickPlaceQueue>();
                if (instance == null) instance = new GameObject("MoveItPickPlaceQueue").AddComponent<MoveItPickPlaceQueue>();
            }
            return instance;
        }
    }

    readonly List<Request> pending = new List<Request>();
    Request current;
    bool started;   // current の指令に対する最初の状態を受け取ったか
    ROSConnection ros;

    /// <summary>pick_place_server の最新の状態</summary>
    public string Status { get; private set; } = "(Waiting for pick_place_server status)";
    /// <summary>実行中の箱 (なければ null)</summary>
    public MoveItPickable Current => current?.obj;
    public int PendingCount => pending.Count;

    void Awake()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<StringMsg>(CommandTopic);
        ros.Subscribe<StringMsg>(StatusTopic, OnStatus);
    }

    /// <summary>
    /// 箱を運ぶ指令を順番待ちに入れる。
    /// bottomCenter = 置いたときの箱の底面の中心 (Unity の World)、rotation = 置いたときの箱の向き。
    /// done(成功したか, 最後の状態) は終わったときに呼ばれる (上書きされた指令は false, "replaced")。
    /// </summary>
    public void Enqueue(MoveItPickable obj, Vector3 bottomCenter, Quaternion rotation, Action<bool, string> done = null)
    {
        for (int i = pending.Count - 1; i >= 0; i--)
        {
            if (pending[i].obj == obj)
            {
                pending[i].done?.Invoke(false, "replaced");
                pending.RemoveAt(i);
            }
        }
        pending.Add(new Request { obj = obj, bottomCenter = bottomCenter, rotation = rotation, done = done });
        if (current == null) SendNext();
    }

    /// <summary>まだ送っていない指令を捨てる (実行中のものは Stop で止める)</summary>
    public void ClearPending()
    {
        foreach (var r in pending) r.done?.Invoke(false, "cleared");
        pending.Clear();
    }

    void SendNext()
    {
        while (pending.Count > 0)
        {
            current = pending[0];
            pending.RemoveAt(0);
            if (current.obj != null) break;   // 削除された箱は飛ばす
            current = null;
        }
        if (current == null) return;

        // 置き場所 = 底面の中心 + 上へ高さの半分 (ROS には箱の中心を送る)
        Vector3 center = current.bottomCenter + current.rotation * Vector3.up * (current.obj.WorldSize.y / 2f);
        var p = center.To<FLU>();
        var q = current.rotation.To<FLU>();
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        string json = string.Format(ci,
            "{{\"object\": \"{0}\", \"frame_id\": \"world\", \"place\": {{\"position\": [{1}, {2}, {3}], \"orientation\": [{4}, {5}, {6}, {7}]}}}}",
            current.obj.ObjectName, p.x, p.y, p.z, q.x, q.y, q.z, q.w);
        started = false;
        ros.Publish(CommandTopic, new StringMsg(json));
        Debug.Log($"[MoveItPickPlaceQueue] 送信: {json}");
    }

    void OnStatus(StringMsg msg)
    {
        Status = msg.data;
        if (current == null) return;

        string state = msg.data.Split(':')[0];
        bool terminal = state == "succeeded" || state == "failed" || state == "rejected";
        if (!started)
        {
            // 送った指令が受け付けられると accepted が来る。それより前の状態は前の指令の残り (latch) なので無視する
            // (rejected だけは受け付けられなかった返事なので、この指令の終わりとして扱う)
            if (state == "accepted") { started = true; return; }
            if (state != "rejected") return;
        }
        if (!terminal) return;

        var finished = current;
        current = null;
        finished.done?.Invoke(state == "succeeded", msg.data);
        SendNext();
    }
}
