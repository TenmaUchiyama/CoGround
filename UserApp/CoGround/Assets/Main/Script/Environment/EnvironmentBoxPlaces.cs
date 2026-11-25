using System.Collections;
using System.Collections.Generic;
using Meta.XR.MRUtilityKit;
using UnityEngine;

/// <summary>
/// EnvironmentBoxLayout の名前を付けた箱を、置き場所 (place_zone を持つ CoGroundSceneObject) にする。
/// ルールを動かすシーンに置く。箱の名前がそのまま置き場所の ID になり、
/// ルールの行き先 (CoGroundRulesSender の Target Region) にその名前を書ける。
///
/// ■ やること (Play を始めたとき)
///   1. MRUK の部屋が出るのを待ち、部屋の基準から箱のワールド位置を求める (EnvironmentBoxLayout の説明を参照)
///   2. 名前のある箱ごとに GameObject を作る: 名前 = 箱の名前、箱全体が place_zone
///      名前の無い箱は作らない。同じ ID の物体がシーンにもうあれば作らない (もとからある方を残す)
///   3. CoGroundSceneReporter が真値を送らない設定 (MockSimulatedObjects が認識結果だけを送る) のときは、
///      このコンポーネントが置き場所を送る。真値を送る設定なら CoGroundSceneObject として送られる
///
/// ■ ロボットが止まる位置
///   CoGroundApproachPoint は付けないので、動作計画が箱のまわりから自動で選ぶ。
///
/// ■ 実行中は箱を動かさない
///   箱を置き直すのは EnvironmentGenerator のシーン (EnvironmentBoxPlacer) でやる。
/// </summary>
public class EnvironmentBoxPlaces : MonoBehaviour, ICoGroundSceneSource
{
    [SerializeField] EnvironmentBoxLayout layout;
    [Tooltip("MRUK の部屋が出るのを待つ時間 [s]")]
    [SerializeField] float roomTimeout = 5f;

    [Header("見た目")]
    [Tooltip("箱と名前を見せる")]
    [SerializeField] bool showBoxes = true;
    [SerializeField] Color boxColor = new Color(0.2f, 0.6f, 1f, 0.25f);
    [SerializeField] float labelSize = 0.05f;

    class Entry
    {
        public EnvironmentBoxLayout.Box box;
        public Transform root;
        public TextMesh label; // showBoxes が false なら null
    }

    readonly List<CoGroundSceneObject> places = new List<CoGroundSceneObject>();
    readonly List<Entry> entries = new List<Entry>();
    Vector3 originPosition;
    float originYaw;
    bool hasRoomOrigin;     // 今の基準が MRUK の部屋から取れたものか (false なら保存したときの仮の基準)
    string roomUuid = "";   // 基準にしている部屋
    CoGroundSceneReporter reporter;
    Material material;
    Transform head;

    /// <summary>作った置き場所</summary>
    public IReadOnlyList<CoGroundSceneObject> Places => places;

    IEnumerator Start()
    {
        if (layout == null)
        {
            Debug.LogWarning("[EnvironmentBoxPlaces] Layout が未設定", this);
            yield break;
        }
        layout.LoadDeviceCopy();

        float waited = 0f;
        while (MRUK.Instance != null && !EnvironmentRoom.HasRoom() && waited < roomTimeout)
        {
            waited += Time.unscaledDeltaTime;
            yield return null;
        }
        hasRoomOrigin = EnvironmentRoom.TryGetOrigin(out originPosition, out originYaw, out roomUuid, layout.roomUuid);
        if (!hasRoomOrigin)
        {
            originPosition = layout.originPosition;
            originYaw = layout.originYaw;
            Debug.LogWarning("[EnvironmentBoxPlaces] MRUK の部屋がまだ無い。仮に保存したときの基準で置き場所を作り、部屋が読み込まれたら置き直す", this);
        }
        else if (!string.IsNullOrEmpty(layout.roomUuid) && layout.roomUuid != roomUuid)
        {
            Debug.LogWarning($"[EnvironmentBoxPlaces] 保存したときと部屋が違う (保存: {layout.roomUuid}、今: {roomUuid})。置き場所がずれているかもしれない", this);
        }

        var rig = FindAnyObjectByType<OVRCameraRig>();
        head = rig != null ? rig.centerEyeAnchor : Camera.main != null ? Camera.main.transform : null;
        material = FetchGhost.MakeMaterial(boxColor);

        int unnamed = 0;
        foreach (var box in layout.boxes)
        {
            if (string.IsNullOrWhiteSpace(box.name)) { unnamed++; continue; }
            string id = box.name.Trim();
            if (CoGroundSceneObject.Find(id) != null)
            {
                Debug.LogWarning($"[EnvironmentBoxPlaces] {id}: 同じ ID の物体がシーンにもうあるので、この箱は置き場所にしない", this);
                continue;
            }
            Spawn(id, box);
        }

        reporter = FindAnyObjectByType<CoGroundSceneReporter>();
        if (reporter != null) reporter.AddSource(this);

        Debug.Log($"[EnvironmentBoxPlaces] 置き場所を {places.Count} 個作った" +
                  (unnamed > 0 ? $" (名前の無い箱 {unnamed} 個は使わない)" : ""), this);
    }

    void Spawn(string id, EnvironmentBoxLayout.Box box)
    {
        // 箱そのもの (メッシュの範囲 = 物体の位置と大きさとして送られる)。当たり判定は無い
        var root = EnvironmentRoom.MakeCube(id, transform, material);
        root.localScale = box.size;
        root.GetComponent<MeshRenderer>().enabled = showBoxes;

        // 箱全体を置く範囲にする (親のスケール = 箱の大きさなので、子のスケールは 1)
        var zone = new GameObject("place_zone").transform;
        zone.SetParent(root, false);

        var place = root.gameObject.AddComponent<CoGroundSceneObject>();
        place.Configure(id, box.category, zone);
        places.Add(place);

        var entry = new Entry { box = box, root = root };
        if (showBoxes)
        {
            // ラベルは箱の子にしない (箱のスケールで文字がゆがむため)
            entry.label = EnvironmentRoom.MakeLabel(transform, labelSize);
            entry.label.name = id + " label";
            entry.label.text = id;
        }
        entries.Add(entry);
        Place(entry);
    }

    /// <summary>箱とラベルを、今の部屋の基準で置く</summary>
    void Place(Entry e)
    {
        EnvironmentBoxLayout.ToWorld(originPosition, originYaw, e.box.position, e.box.yaw, out var position, out var rotation);
        e.root.SetPositionAndRotation(position, rotation);
        if (e.label != null) e.label.transform.position = position + Vector3.up * (e.box.size.y / 2f + 0.02f);
    }

    void LateUpdate()
    {
        FollowRoom();
        foreach (var e in entries) EnvironmentRoom.FaceLabel(e.label, head);
    }

    /// <summary>
    /// 部屋の基準が変わったら (部屋が後から読み込まれた・World Lock オフで床のアンカーが動いた)、置き場所を部屋について動かす
    /// </summary>
    void FollowRoom()
    {
        // 一度決めた部屋を使い続ける (今いる部屋で選ぶと、歩いて部屋をまたいだときに全部の置き場所が飛ぶ)
        if (entries.Count == 0 || !EnvironmentRoom.TryGetOrigin(out var p, out var y, out var uuid, hasRoomOrigin ? roomUuid : layout.roomUuid)) return;
        if (hasRoomOrigin && uuid != roomUuid) return;
        if (hasRoomOrigin && !EnvironmentRoom.OriginMoved(originPosition, originYaw, p, y)) return;

        if (!hasRoomOrigin)
        {
            Debug.Log("[EnvironmentBoxPlaces] MRUK の部屋が読み込まれたので、置き場所を部屋の基準で置き直した", this);
            if (!string.IsNullOrEmpty(layout.roomUuid) && layout.roomUuid != uuid)
                Debug.LogWarning($"[EnvironmentBoxPlaces] 保存したときと部屋が違う (保存: {layout.roomUuid}、今: {uuid})。置き場所がずれているかもしれない", this);
        }
        originPosition = p;
        originYaw = y;
        roomUuid = uuid;
        hasRoomOrigin = true;
        foreach (var e in entries) Place(e);
    }

    public void CollectObjects(List<SceneObjectDto> into)
    {
        // 真値を送る設定のときは CoGroundSceneObject として送られているので、ここでは出さない (二重にしない)
        if (reporter == null || reporter.IncludeSimulationObjects) return;
        foreach (var p in places)
            if (p != null && p.isActiveAndEnabled) into.Add(p.ToDto());
    }

    void OnDestroy()
    {
        if (material != null) Destroy(material);
    }
}
