using Meta.XR.MRUtilityKit;
using UnityEngine;

/// <summary>
/// 箱の位置の基準にする「部屋の基準」(MRUK の部屋の床のアンカー) と、箱の見た目の部品。
/// EnvironmentBoxPlacer (箱を置く) と EnvironmentBoxPlaces (箱を置き場所にする) が同じものを使う。
/// </summary>
public static class EnvironmentRoom
{
    /// <summary>MRUK の部屋が読み込まれているか</summary>
    public static bool HasRoom()
    {
        var mruk = MRUK.Instance;
        return mruk != null && mruk.IsInitialized && mruk.Rooms != null && mruk.Rooms.Count > 0;
    }

    /// <summary>部屋の基準 (床のアンカーの位置と、水平にした向き)。部屋が無ければ false</summary>
    /// <param name="preferUuid">この ID の部屋があれば、それを使う (保存したときの部屋)。
    /// 無ければ今いる部屋 (今いる部屋が無ければ最初の部屋)。
    /// 今いる部屋は歩くと変わるので、箱を置いたまま基準の部屋が入れ替わらないように ID を渡すこと</param>
    public static bool TryGetOrigin(out Vector3 position, out float yaw, out string uuid, string preferUuid = null)
    {
        position = Vector3.zero;
        yaw = 0f;
        uuid = "";
        if (!HasRoom()) return false;
        MRUKRoom room = null;
        if (!string.IsNullOrEmpty(preferUuid))
            foreach (var r in MRUK.Instance.Rooms)
                if (r != null && r.Anchor.Uuid.ToString() == preferUuid) { room = r; break; }
        if (room == null) room = MRUK.Instance.GetCurrentRoom() ?? MRUK.Instance.Rooms[0];
        if (room == null || room.FloorAnchors.Count == 0) return false;

        var floor = room.FloorAnchors[0].transform;
        // 床のアンカーは面の法線が前 (Z) を向くので、水平な軸 (上 = Y) から向きを決める
        var axis = Vector3.ProjectOnPlane(floor.up, Vector3.up);
        if (axis.sqrMagnitude < 0.01f) axis = Vector3.ProjectOnPlane(floor.forward, Vector3.up);
        if (axis.sqrMagnitude < 0.01f) return false;

        position = floor.position;
        yaw = Quaternion.LookRotation(axis, Vector3.up).eulerAngles.y;
        uuid = room.Anchor.Uuid.ToString();
        return true;
    }

    /// <summary>
    /// 部屋の基準が、箱を置き直すほど動いたか。
    /// World Lock がオフだと床のアンカーは細かく揺れるので、小さな揺れでは置き直さない (箱が震えないように)。
    /// </summary>
    public static bool OriginMoved(Vector3 oldPosition, float oldYaw, Vector3 newPosition, float newYaw)
    {
        const float distance = 0.01f; // [m]
        const float angle = 0.5f;     // [deg]
        return (newPosition - oldPosition).sqrMagnitude > distance * distance
            || Mathf.Abs(Mathf.DeltaAngle(oldYaw, newYaw)) > angle;
    }

    /// <summary>半透明の箱 (当たり判定は無い)。大きさは返り値の Transform のスケールで決める</summary>
    public static Transform MakeCube(string name, Transform parent, Material material)
    {
        var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        cube.name = name;
        Object.Destroy(cube.GetComponent<Collider>());
        cube.transform.SetParent(parent, false);
        var renderer = cube.GetComponent<MeshRenderer>();
        renderer.sharedMaterial = material;
        renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        renderer.receiveShadows = false;
        return cube.transform;
    }

    /// <summary>名前のラベル (1 行の高さがおよそ size [m])。向きは FaceLabel で毎フレーム合わせる</summary>
    public static TextMesh MakeLabel(Transform parent, float size)
    {
        var go = new GameObject("label");
        go.transform.SetParent(parent, false);
        var label = go.AddComponent<TextMesh>();
        var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        label.font = font;
        go.GetComponent<MeshRenderer>().sharedMaterial = font.material;
        label.fontSize = 64;
        label.characterSize = size * 10f / 64f;
        label.anchor = TextAnchor.LowerCenter;
        label.alignment = TextAlignment.Center;
        label.color = Color.white;
        return label;
    }

    /// <summary>ラベルを見ている人 (head) のほうへ向ける</summary>
    public static void FaceLabel(TextMesh label, Transform head)
    {
        if (label == null || head == null) return;
        var away = label.transform.position - head.position;
        if (away.sqrMagnitude > 1e-4f) label.transform.rotation = Quaternion.LookRotation(away, Vector3.up);
    }
}
