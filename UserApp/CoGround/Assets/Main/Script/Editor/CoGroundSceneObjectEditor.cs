using UnityEditor;
using UnityEditor.IMGUI.Controls;
using UnityEngine;

/// <summary>
/// CoGroundSceneObject を選んでいるとき、Scene ビューの黄色の place_zone の枠を、面の点をドラッグして直接広げ・縮められるようにする。
/// 動くのは place_zone (子) の位置とスケールだけで、親 (BoxCollider) と見た目は変わらない。
///
/// 親を選んだまま Scale ツールを使うと、親ごと (見た目も place_zone も) 拡大されるので注意。
/// </summary>
[CustomEditor(typeof(CoGroundSceneObject))]
public class CoGroundSceneObjectEditor : Editor
{
    readonly BoxBoundsHandle handle = new BoxBoundsHandle();

    public override void OnInspectorGUI()
    {
        DrawDefaultInspector();
        var obj = (CoGroundSceneObject)target;
        if (obj.PlaceZone == null) return;

        EditorGUILayout.Space();
        var points = obj.ApproachPoints;
        EditorGUILayout.HelpBox(
            points.Length == 0
                ? "止まる位置がまだ無い。動作計画は、物体のまわりから自動で止まる位置を選ぶ。"
                : $"止まる位置: {points.Length} か所 (水色の円と矢印)。動作計画はまずここを試す。\n" +
                  "子の approach を動かして調整する。矢印 (+Z) を家具の方へ向け、台車の中心は家具の縁から 0.35〜0.4 m 離す。",
            MessageType.None);
        if (GUILayout.Button("止まる位置を追加"))
            Selection.activeGameObject = AddApproachPoint(obj).gameObject;

        EditorGUILayout.Space();
        var s = obj.PlaceZone.lossyScale;
        EditorGUILayout.HelpBox(
            $"place_zone: {Mathf.Abs(s.x):0.00} x {Mathf.Abs(s.y):0.00} x {Mathf.Abs(s.z):0.00} m\n" +
            "Scene ビューの黄色の枠の点をドラッグすると place_zone だけ広げ・縮められる。\n" +
            "親を Scale ツールで拡大すると見た目ごと大きくなるので使わない。",
            MessageType.None);
        if (obj.PlaceZone.childCount > 0)
            EditorGUILayout.HelpBox(
                $"place_zone の子に {obj.PlaceZone.GetChild(0).name} などが入っている。place_zone を拡大するとそれも拡大される。" +
                $"{obj.name} の直下へ移す (「片付けデモの見た目」の「当たり判定を合わせる」でも移る)。",
                MessageType.Error);
        if (obj.transform.localScale != Vector3.one)
        {
            EditorGUILayout.HelpBox(
                $"この物体のスケールが {obj.transform.localScale} で 1 ではない。place_zone や見た目まで一緒に拡大されている。\n" +
                "見た目の大きさは子 (prefab) のスケールで、置く範囲は place_zone のスケールで変える。",
                MessageType.Warning);
            if (GUILayout.Button("スケールを 1 に戻す (見た目・当たり判定・place_zone の大きさはそのまま)"))
                BakeScale(obj.transform);
        }
    }

    /// <summary>
    /// 止まる位置を 1 つ足す。家具の手前 (いちばん近い Fetch の側) の、縁から 0.38 m 離れた床の上に、家具の方を向けて置く
    /// </summary>
    public static CoGroundApproachPoint AddApproachPoint(CoGroundSceneObject obj)
    {
        var dto = obj.ToDto();
        var center = new Vector3(dto.Position[0], 0f, dto.Position[2]);
        var size = dto.Size != null ? new Vector3(dto.Size[0], dto.Size[1], dto.Size[2]) : Vector3.one * 0.5f;
        var robot = Object.FindAnyObjectByType<RosJointToFetch>();
        var toRobot = robot != null ? Vector3.ProjectOnPlane(robot.transform.position - center, Vector3.up) : -Vector3.forward;
        if (toRobot.sqrMagnitude < 1e-4f) toRobot = -Vector3.forward;
        // 家具のローカル軸のうち、ロボットの方にいちばん近い面の手前に置く
        var rot = obj.transform.rotation;
        Vector3 best = Vector3.zero; float bestDot = -2f, half = 0f;
        foreach (var (axis, h) in new[] { (Vector3.forward, size.z), (Vector3.back, size.z), (Vector3.right, size.x), (Vector3.left, size.x) })
        {
            var dir = Vector3.ProjectOnPlane(rot * axis, Vector3.up).normalized;
            float d = Vector3.Dot(dir, toRobot.normalized);
            if (d > bestDot) { bestDot = d; best = dir; half = h / 2f; }
        }
        int n = obj.ApproachPoints.Length;
        var go = new GameObject(n == 0 ? "approach" : $"approach_{n + 1}");
        Undo.RegisterCreatedObjectUndo(go, "止まる位置を追加");
        go.transform.SetParent(obj.transform, false);
        go.transform.SetPositionAndRotation(center + best * (half + 0.38f), Quaternion.LookRotation(-best, Vector3.up));
        Undo.AddComponent<CoGroundApproachPoint>(go);
        return go.GetComponent<CoGroundApproachPoint>();
    }

    [MenuItem("CoGround/止まる位置を追加 (置く場所すべて、まだ無いものだけ)")]
    static void AddApproachPointsToAll()
    {
        int added = 0;
        foreach (var o in Object.FindObjectsByType<CoGroundSceneObject>(FindObjectsSortMode.None))
        {
            if (!o.IsPlace || o.ApproachPoints.Length > 0) continue;
            AddApproachPoint(o);
            added++;
        }
        Debug.Log($"[CoGround] 止まる位置を {added} か所に追加した (子の approach を動かして調整する)");
    }

    /// <summary>親のスケールを子と BoxCollider に移して、親を 1 にする (ワールドでの見た目は変わらない)</summary>
    static void BakeScale(Transform root)
    {
        Vector3 s = root.localScale;
        Undo.SetCurrentGroupName($"{root.name} のスケールを 1 に戻す");
        int group = Undo.GetCurrentGroup();

        foreach (Transform c in root)
        {
            Undo.RecordObject(c, "スケールを子へ移す");
            c.localPosition = Vector3.Scale(c.localPosition, s);
            c.localScale = Vector3.Scale(c.localScale, s);
        }
        if (root.TryGetComponent<BoxCollider>(out var bc))
        {
            Undo.RecordObject(bc, "スケールを当たり判定へ移す");
            bc.center = Vector3.Scale(bc.center, s);
            bc.size = Vector3.Scale(bc.size, s);
        }
        Undo.RecordObject(root, "スケールを 1 に");
        root.localScale = Vector3.one;
        Undo.CollapseUndoOperations(group);
    }

    void OnSceneGUI()
    {
        var obj = (CoGroundSceneObject)target;
        var zone = obj.PlaceZone;
        if (zone == null) return;

        var parentScale = zone.parent != null ? zone.parent.lossyScale : Vector3.one;
        var size = Abs(zone.lossyScale);

        using (new Handles.DrawingScope(new Color(1f, 0.85f, 0.1f, 1f),
                                        Matrix4x4.TRS(zone.position, zone.rotation, Vector3.one)))
        {
            handle.center = Vector3.zero;
            handle.size = size;
            EditorGUI.BeginChangeCheck();
            handle.DrawHandle();
            if (!EditorGUI.EndChangeCheck()) return;

            Undo.RecordObject(zone, "place_zone の大きさを変える");
            zone.position = Handles.matrix.MultiplyPoint3x4(handle.center);
            var newSize = Abs(handle.size);
            zone.localScale = new Vector3(
                newSize.x / SafeAbs(parentScale.x),
                newSize.y / SafeAbs(parentScale.y),
                newSize.z / SafeAbs(parentScale.z));
        }
    }

    static Vector3 Abs(Vector3 v) => new Vector3(Mathf.Abs(v.x), Mathf.Abs(v.y), Mathf.Abs(v.z));
    static float SafeAbs(float f) => Mathf.Max(Mathf.Abs(f), 1e-6f);
}
