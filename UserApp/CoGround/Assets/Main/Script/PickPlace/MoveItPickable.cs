using System.Collections.Generic;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

/// <summary>
/// 運べる箱。MoveItCollisionBox と一緒に付ける (Planning Scene での名前は MoveItCollisionBox の名前)。
///
/// ■ 半透明のゴースト (置き場所の指定)
///   箱に半透明のゴーストを重ねて表示する。ゴーストを動かして離すと、そこへロボットが運ぶ。
///     - 空中で離しても、真下の面 (机など) に合わせて置き場所にする。向きは水平の回転 (yaw) だけ使う
///     - VR: MoveItGhostDistanceGrab を付けると、ゴーストを distance grab でつかめる。
///       つかんでいる間は HoldGhost()、離したら ReleaseGhost() (動かしていれば置いたとみなす)
///     - Editor: 再生中に Scene ビューでゴーストを動かし、止めると (Still Seconds 秒) 置いたとみなす
///       (つかんでいる間は止めても置いたとみなさない)
///     - 運んでいる間ゴーストは置き場所に残り、終わると箱に重なる。失敗したら箱の位置に戻る
///   ゴーストのコライダーは Planning Scene に入らない (MoveItCollisionBox を付けないため)。
///
/// ■ つかんでいる間
///   ROS の pick_place_server が「手にくっつけた」(/coground/pick_place/attached) 間は、
///   この箱を Fetch の gripper_link の子にして手に追従させる (Unity では物理でつかまないため)。
///   離したらもとの親に戻す。Rigidbody があれば、その間は isKinematic にする。
/// </summary>
[RequireComponent(typeof(MoveItCollisionBox))]
public class MoveItPickable : MonoBehaviour
{
    const string AttachedTopic = "/coground/pick_place/attached";
    static readonly List<MoveItPickable> all = new List<MoveItPickable>();

    /// <summary>シーン内の運べる箱 (有効なものだけ)</summary>
    public static IReadOnlyList<MoveItPickable> All => all;

    [Tooltip("箱をくっつけるリンク")]
    [SerializeField] string gripperLinkName = "gripper_link";

    [Header("ゴースト (置き場所の指定)")]
    [SerializeField] bool createGhost = true;
    [Tooltip("ゴーストの元 (1 m の立方体として作る。箱の大きさに拡大縮小する)。" +
             "VR でつかむためのコンポーネント (Grabbable など) を付けたものを指定する。未設定なら半透明の Cube を作る")]
    [SerializeField] GameObject ghostPrefab;
    [Tooltip("ゴーストの不透明度 (色は箱と同じ)。ghostPrefab を使うときは prefab のマテリアルのまま")]
    [SerializeField, Range(0f, 1f)] float ghostAlpha = 0.35f;
    [Tooltip("ゴーストを動かして止めたら置いたとみなす (Editor 用)。VR でつかんでいる間は無効")]
    [SerializeField] bool commitWhenStill = true;
    [SerializeField] float stillSeconds = 0.5f;

    enum GhostState { FollowBox, Moving, Waiting }

    MoveItCollisionBox box;
    BoxCollider col;
    Rigidbody rb;
    Transform originalParent;
    bool rbWasKinematic;
    bool attached;

    Transform ghost;
    GhostState ghostState = GhostState.FollowBox;
    Vector3 ghostSetPos;      // こちらで最後に置いたゴーストの位置・向き (ずれていたら人が動かしている)
    Quaternion ghostSetRot;
    Vector3 ghostLastPos;
    Quaternion ghostLastRot;
    float ghostStillSince;
    bool ghostHeld;
    int requestId;

    public string ObjectName => box.ObjectName;
    public Vector3 WorldSize => box.WorldSize;
    public bool IsAttached => attached;
    /// <summary>半透明のゴースト (VR でつかむ対象)。createGhost が false なら null</summary>
    public Transform Ghost => ghost;
    /// <summary>ゴーストで指定した運搬を待っている / 実行中</summary>
    public bool IsBusy => ghostState == GhostState.Waiting;

    void Awake()
    {
        box = GetComponent<MoveItCollisionBox>();
        col = GetComponent<BoxCollider>();
        rb = GetComponent<Rigidbody>();
    }

    void OnEnable()
    {
        all.Add(this);
        if (ghost != null) ghost.gameObject.SetActive(true);
    }

    void OnDisable()
    {
        all.Remove(this);
        if (ghost != null) ghost.gameObject.SetActive(false);
    }

    void OnDestroy()
    {
        if (ghost != null) Destroy(ghost.gameObject);
    }

    void Start()
    {
        ROSConnection.GetOrCreateInstance().Subscribe<StringMsg>(AttachedTopic, OnAttached);
        if (createGhost) CreateGhost();
    }

    // ---- ゴースト ----

    void CreateGhost()
    {
        GameObject go;
        if (ghostPrefab != null)
        {
            go = Instantiate(ghostPrefab);
        }
        else
        {
            go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var c = go.GetComponent<BoxCollider>();
            c.isTrigger = true; // ロボットや箱と物理で押し合わない (レイキャストでは当たる)
            var r = go.GetComponent<MeshRenderer>();
            var own = GetComponent<Renderer>();
            Color color = own != null && own.sharedMaterial != null ? own.sharedMaterial.color : Color.white;
            color.a = ghostAlpha;
            r.sharedMaterial = FetchGhost.MakeMaterial(color);
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }
        go.name = $"{name} (ghost)";
        ghost = go.transform;
        // 箱と同じ大きさだと面がちらつくので少し大きく
        ghost.localScale = WorldSize * 1.02f;
        SetGhost(BoxCenter(), transform.rotation);
    }

    Vector3 BoxCenter() => transform.TransformPoint(col.center);

    void SetGhost(Vector3 pos, Quaternion rot)
    {
        var grb = ghost.GetComponent<Rigidbody>();
        if (grb != null && !grb.isKinematic)
        {
            grb.linearVelocity = Vector3.zero;
            grb.angularVelocity = Vector3.zero;
        }
        ghost.SetPositionAndRotation(pos, rot);
        ghostSetPos = ghostLastPos = pos;
        ghostSetRot = ghostLastRot = rot;
    }

    bool GhostMovedFrom(Vector3 pos, Quaternion rot) =>
        Vector3.Distance(ghost.position, pos) > 0.003f || Quaternion.Angle(ghost.rotation, rot) > 1f;

    void Update()
    {
        if (ghost == null) return;

        bool movedByUser = GhostMovedFrom(ghostSetPos, ghostSetRot);
        switch (ghostState)
        {
            case GhostState.FollowBox:
                if (movedByUser) StartMoving();
                else SetGhost(BoxCenter(), transform.rotation);
                break;

            case GhostState.Waiting:
                if (movedByUser) StartMoving(); // 運んでいる途中でも、また動かせば次の指令になる
                break;

            case GhostState.Moving:
                if (GhostMovedFrom(ghostLastPos, ghostLastRot))
                {
                    ghostLastPos = ghost.position;
                    ghostLastRot = ghost.rotation;
                    ghostStillSince = Time.time;
                }
                else if (commitWhenStill && !ghostHeld && Time.time - ghostStillSince > stillSeconds)
                {
                    CommitGhost();
                }
                break;
        }
    }

    void StartMoving()
    {
        ghostState = GhostState.Moving;
        ghostLastPos = ghost.position;
        ghostLastRot = ghost.rotation;
        ghostStillSince = Time.time;
    }

    /// <summary>ゴーストを VR でつかんだ (離すまで置いたとみなさない)</summary>
    public void HoldGhost() => ghostHeld = true;

    /// <summary>ゴーストを VR で離した。つかんでいる間に動かしていれば、そこへ運ばせる</summary>
    public void ReleaseGhost()
    {
        ghostHeld = false;
        if (ghostState == GhostState.Moving) CommitGhost();
    }

    /// <summary>
    /// ゴーストの今の場所を置き場所として、ロボットに運ばせる。
    /// ゴーストの真下の面 (机など) に合わせ、向きは水平の回転だけ使う。面が無ければ取り消してゴーストを戻す。
    /// </summary>
    public void CommitGhost()
    {
        if (ghost == null) return;
        if (!FindSurfaceBelow(ghost.position, out Vector3 surface))
        {
            Debug.LogWarning($"[MoveItPickable] {ObjectName}: ゴーストの下に置ける面が無いので取り消し");
            ResetGhost();
            return;
        }

        Vector3 fwd = Vector3.ProjectOnPlane(ghost.forward, Vector3.up);
        if (fwd.sqrMagnitude < 1e-4f) fwd = Vector3.ProjectOnPlane(ghost.up, Vector3.up); // 横倒しのとき
        Quaternion rot = Quaternion.LookRotation(fwd.normalized, Vector3.up);

        SetGhost(surface + Vector3.up * (WorldSize.y / 2f), rot);
        ghostState = GhostState.Waiting;
        int id = ++requestId;
        MoveItPickPlaceQueue.Instance.Enqueue(this, surface, rot, (ok, status) =>
        {
            if (id != requestId) return; // その後また動かされた
            if (!ok) Debug.LogWarning($"[MoveItPickable] {ObjectName}: {status}");
            ghostState = GhostState.FollowBox; // 成功なら箱がここに来ている / 失敗なら箱の位置へ戻る
        });
    }

    /// <summary>ゴーストを箱の位置に戻す (まだ送っていない指令は残る)</summary>
    public void ResetGhost()
    {
        if (ghost == null) return;
        requestId++;
        ghostState = GhostState.FollowBox;
        SetGhost(BoxCenter(), transform.rotation);
    }

    bool FindSurfaceBelow(Vector3 from, out Vector3 point)
    {
        // 少し上から真下へ。ロボット・運べる箱・ゴースト自身・トリガーは面として扱わない
        var hits = Physics.RaycastAll(from + Vector3.up * 0.05f, Vector3.down, 3f, ~0, QueryTriggerInteraction.Ignore);
        System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
        foreach (var h in hits)
        {
            if (h.collider.GetComponentInParent<ArticulationBody>() != null) continue;
            if (h.collider.GetComponentInParent<MoveItPickable>() != null) continue;
            if (h.transform.IsChildOf(ghost)) continue;
            point = h.point;
            return true;
        }
        point = default;
        return false;
    }

    // ---- 手にくっつける ----

    void OnAttached(StringMsg msg)
    {
        bool shouldAttach = msg.data == ObjectName;
        if (shouldAttach && !attached) Attach();
        else if (!shouldAttach && attached) Detach();
    }

    void Attach()
    {
        var gripper = FindGripperLink();
        if (gripper == null)
        {
            Debug.LogError($"[MoveItPickable] {gripperLinkName} が見つからない (RosJointToFetch が付いた fetch が必要)");
            return;
        }
        originalParent = transform.parent;
        transform.SetParent(gripper, true);
        // 指 (ArticulationBody) と押し合わないようにコライダーを切る
        col.enabled = false;
        if (rb != null)
        {
            rbWasKinematic = rb.isKinematic;
            rb.isKinematic = true;
        }
        attached = true;
        Debug.Log($"[MoveItPickable] {ObjectName} をつかんだ");
    }

    void Detach()
    {
        transform.SetParent(originalParent, true);
        col.enabled = true;
        if (rb != null) rb.isKinematic = rbWasKinematic;
        attached = false;
        Debug.Log($"[MoveItPickable] {ObjectName} を離した");
    }

    Transform FindGripperLink()
    {
        // 計画結果のゴースト (MoveItTrajectoryPreview の複製) にも gripper_link があるので、
        // RosJointToFetch が付いている本体から探す
        foreach (var robot in FindObjectsByType<RosJointToFetch>(FindObjectsSortMode.None))
        {
            foreach (var t in robot.GetComponentsInChildren<Transform>())
            {
                if (t.name == gripperLinkName) return t;
            }
        }
        return null;
    }
}
