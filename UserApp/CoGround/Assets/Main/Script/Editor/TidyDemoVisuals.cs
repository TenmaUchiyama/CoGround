using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

/// <summary>
/// メニュー CoGround > 片付けデモの見た目を差し替え
/// 片付けデモ (TidyDemoSetup) の仮の箱を、好きな prefab / モデルに差し替える。
///
/// ■ 物体の作り (差し替え後もこの形を保つ)
///   table_1 など (スケール 1)
///     ├ BoxCollider          … 当たり判定 = MoveIt の衝突物体 (緑の箱) = 物体の bbox (サーバーに送る位置・大きさ) = つかむ箱
///     ├ MoveItCollisionBox / CoGroundSceneObject / (運ぶ物なら) MoveItPickable
///     ├ visual               … 見た目だけ。ここを prefab に入れ替える (コライダー・Rigidbody は外す)
///     └ place_zone           … 置く場所の範囲 (机・箱・ごみ箱だけ)。BoxCollider の上面の上に乗せる
///
/// ■ 差し替えると
///   1. visual を prefab に入れ替える。大きさは prefab のまま。底面の中心を前の箱の底面の中心に合わせる
///   2. BoxCollider を見た目の範囲 (子の有効な Renderer すべてを囲む箱。place_zone は除く) に合わせる
///   3. place_zone を新しい上面の上に置き直す (高さはそのまま、広さは上面に合わせる)
///   4. 机を差し替えたときは、机の上の物をすべて新しい上面の高さに載せ直す
///   visual を手で回したり大きさを変えたり、prefab を手で子に入れたりしたら「当たり判定を合わせる」を押す。
///   (place_zone は見た目や BoxCollider に追従しない。合わせるのはこのボタンか、place_zone を直接動かす)
/// </summary>
public class TidyDemoVisualsWindow : EditorWindow
{
    readonly Dictionary<int, GameObject> prefabs = new Dictionary<int, GameObject>();
    Vector2 scroll;

    [MenuItem("CoGround/片付けデモの見た目を差し替え")]
    static void Open() => GetWindow<TidyDemoVisualsWindow>("片付けデモの見た目");

    void OnGUI()
    {
        EditorGUILayout.HelpBox(
            "prefab を選んで「差し替え」。当たり判定 (BoxCollider = MoveIt の箱 = つかむ箱) と place_zone は見た目に合わせて作り直す。\n" +
            "運ぶ物は、水平方向の短いほうの幅が 0.09 m 未満でないとつかめない (グリッパーの開きが 0.1 m)。",
            MessageType.Info);

        var objects = new List<CoGroundSceneObject>(
            Object.FindObjectsByType<CoGroundSceneObject>(FindObjectsInactive.Exclude, FindObjectsSortMode.None));
        objects.Sort((a, b) =>
        {
            int k = Kind(a).CompareTo(Kind(b));
            return k != 0 ? k : string.CompareOrdinal(a.name, b.name);
        });

        scroll = EditorGUILayout.BeginScrollView(scroll);
        foreach (var o in objects)
        {
            int key = o.GetInstanceID();
            prefabs.TryGetValue(key, out var prefab);
            using (new EditorGUILayout.HorizontalScope())
            {
                EditorGUILayout.LabelField(KindLabel(o), GUILayout.Width(52));
                if (GUILayout.Button(o.name, EditorStyles.label, GUILayout.Width(110))) Selection.activeGameObject = o.gameObject;
                EditorGUILayout.LabelField(SizeLabel(o), GUILayout.Width(130));
                prefab = (GameObject)EditorGUILayout.ObjectField(prefab, typeof(GameObject), false);
                prefabs[key] = prefab;
                using (new EditorGUI.DisabledScope(prefab == null))
                {
                    if (GUILayout.Button("差し替え", GUILayout.Width(64))) TidyDemoVisuals.ReplaceVisual(o, prefab);
                }
                if (GUILayout.Button("当たり判定を合わせる", GUILayout.Width(120))) TidyDemoVisuals.FitCollider(o);
            }
        }
        EditorGUILayout.EndScrollView();

        EditorGUILayout.Space();
        if (GUILayout.Button("机の上の物を、机の上面の高さに載せ直す")) TidyDemoVisuals.SnapOntoTables();
    }

    void OnHierarchyChange() => Repaint();

    static int Kind(CoGroundSceneObject o) =>
        o.Category == CoGroundCategory.table || o.Category == CoGroundCategory.shelf ? 0 : o.IsPlace ? 1 : o.IsPickable ? 2 : 3;

    static string KindLabel(CoGroundSceneObject o) => new[] { "机", "置く場所", "運ぶ物", "その他" }[Kind(o)];

    static string SizeLabel(CoGroundSceneObject o)
    {
        var bc = o.GetComponent<BoxCollider>();
        if (bc == null) return "(BoxCollider 無し)";
        var s = Vector3.Scale(bc.size, o.transform.lossyScale);
        return $"{Mathf.Abs(s.x):0.00} x {Mathf.Abs(s.y):0.00} x {Mathf.Abs(s.z):0.00}";
    }
}

public static class TidyDemoVisuals
{
    const string VisualName = "visual";
    const string ZoneName = "place_zone";

    /// <summary>visual を prefab に入れ替え、当たり判定と place_zone を合わせる</summary>
    public static void ReplaceVisual(CoGroundSceneObject obj, GameObject prefab)
    {
        var go = obj.gameObject;
        var bc = go.GetComponent<BoxCollider>();
        if (bc == null) { Debug.LogError($"[TidyDemoVisuals] {go.name}: BoxCollider が無い"); return; }

        Undo.SetCurrentGroupName($"{go.name} の見た目を差し替え");
        int group = Undo.GetCurrentGroup();

        Normalize(go);
        // いまの箱の底面の中心 (ローカル)。新しい見た目もここに立たせる
        Vector3 oldBottom = bc.center - Vector3.up * (bc.size.y / 2f);

        var old = go.transform.Find(VisualName);
        if (old != null) Undo.DestroyObjectImmediate(old.gameObject);

        var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, go.transform);
        Undo.RegisterCreatedObjectUndo(inst, "見た目を追加");
        inst.name = VisualName;
        inst.transform.localPosition = Vector3.zero;
        inst.transform.localRotation = Quaternion.identity;
        inst.transform.SetSiblingIndex(0);
        StripPhysics(inst);

        if (!TryVisualBounds(go.transform, out var b))
        {
            Debug.LogError($"[TidyDemoVisuals] {go.name}: {prefab.name} に Renderer が無い");
            return;
        }
        inst.transform.localPosition += oldBottom - new Vector3(b.center.x, b.min.y, b.center.z);

        FitCollider(obj);
        if (obj.Category == CoGroundCategory.table || obj.Category == CoGroundCategory.shelf) SnapOntoTables();

        Undo.CollapseUndoOperations(group);
        Debug.Log($"[TidyDemoVisuals] {go.name} を {prefab.name} に差し替えた (大きさ {SizeText(go)})");
    }

    /// <summary>BoxCollider を見た目 (visual) の範囲に合わせ、place_zone を上面の上に置き直す</summary>
    public static void FitCollider(CoGroundSceneObject obj)
    {
        var go = obj.gameObject;
        var bc = go.GetComponent<BoxCollider>();
        if (bc == null) return;
        Normalize(go);
        MoveOutOfZone(go.transform);
        if (!TryVisualBounds(go.transform, out var b))
        {
            Debug.LogWarning($"[TidyDemoVisuals] {go.name}: 見た目 (Renderer) が無いので合わせられない");
            return;
        }

        Undo.RecordObject(bc, "当たり判定を合わせる");
        bc.center = b.center;
        bc.size = b.size;

        var zone = go.transform.Find(ZoneName);
        if (zone != null)
        {
            Undo.RecordObject(zone, "place_zone を合わせる");
            float h = Mathf.Abs(zone.localScale.y);
            zone.localRotation = Quaternion.identity;
            zone.localPosition = new Vector3(b.center.x, b.max.y + h / 2f, b.center.z);
            zone.localScale = new Vector3(b.size.x, h, b.size.z);
        }

        if (obj.IsPickable)
        {
            float narrow = Mathf.Min(b.size.x, b.size.z);
            if (narrow >= 0.09f)
                Debug.LogWarning($"[TidyDemoVisuals] {go.name}: 水平の短いほうの幅 {narrow:0.000} m。グリッパー (0.1 m) でつかめない");
        }
        EditorUtility.SetDirty(go);
    }

    /// <summary>机 (table / shelf) の上面の範囲に入っている物を、その上面に載せる</summary>
    public static void SnapOntoTables()
    {
        var all = Object.FindObjectsByType<CoGroundSceneObject>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
        int moved = 0;
        foreach (var table in all)
        {
            if (table.Category != CoGroundCategory.table && table.Category != CoGroundCategory.shelf) continue;
            var tbc = table.GetComponent<BoxCollider>();
            if (tbc == null) continue;
            float top = table.transform.TransformPoint(tbc.center + Vector3.up * (tbc.size.y / 2f)).y;

            foreach (var o in all)
            {
                if (o == table) continue;
                var bc = o.GetComponent<BoxCollider>();
                if (bc == null) continue;
                Vector3 center = o.transform.TransformPoint(bc.center);
                Vector3 local = table.transform.InverseTransformPoint(center) - tbc.center;
                if (Mathf.Abs(local.x) > tbc.size.x / 2f || Mathf.Abs(local.z) > tbc.size.z / 2f) continue;

                float bottom = o.transform.TransformPoint(bc.center - Vector3.up * (bc.size.y / 2f)).y;
                float dy = top - bottom;
                if (Mathf.Abs(dy) < 1e-4f) continue;
                Undo.RecordObject(o.transform, "机の上に載せ直す");
                o.transform.position += Vector3.up * dy;
                moved++;
            }
            Debug.Log($"[TidyDemoVisuals] {table.name} の上面 y = {top:0.000} m");
        }
        Debug.Log($"[TidyDemoVisuals] {moved} 個を机の上面に載せ直した");
    }

    /// <summary>
    /// 古い作り (自分自身が拡大縮小した Cube。TidyDemoSetup の運ぶ物) を、
    /// スケール 1 + BoxCollider + visual の子 に直す。すでにその形なら何もしない。
    /// </summary>
    static void Normalize(GameObject go)
    {
        var mf = go.GetComponent<MeshFilter>();
        var mr = go.GetComponent<MeshRenderer>();
        var bc = go.GetComponent<BoxCollider>();
        if (mf == null || mr == null || bc == null) return;

        Vector3 s = go.transform.localScale;
        var visual = new GameObject(VisualName);
        visual.transform.SetParent(go.transform, false);
        visual.transform.SetSiblingIndex(0);
        visual.transform.localScale = s;
        visual.AddComponent<MeshFilter>().sharedMesh = mf.sharedMesh;
        visual.AddComponent<MeshRenderer>().sharedMaterials = mr.sharedMaterials;
        Undo.RegisterCreatedObjectUndo(visual, "visual を作る");

        Undo.DestroyObjectImmediate(mr);
        Undo.DestroyObjectImmediate(mf);

        // 子 (visual 以外) はワールドでの位置・大きさを保つ
        var children = new List<Transform>();
        foreach (Transform c in go.transform) if (c != visual.transform) children.Add(c);
        foreach (var c in children) Undo.SetTransformParent(c, null, "子を一時的に外す");

        Undo.RecordObject(go.transform, "スケールを 1 に");
        go.transform.localScale = Vector3.one;
        Undo.RecordObject(bc, "当たり判定");
        bc.center = Vector3.Scale(bc.center, s);
        bc.size = Abs(Vector3.Scale(bc.size, s));

        foreach (var c in children) Undo.SetTransformParent(c, go.transform, "子を戻す");
    }

    /// <summary>
    /// place_zone の子に入っている物 (見た目の prefab を place_zone に落としてしまった場合など) を、
    /// ワールドの位置・大きさを保ったまま物体の直下へ出す。place_zone の子にあると、place_zone を拡大したとき一緒に拡大される
    /// </summary>
    static void MoveOutOfZone(Transform root)
    {
        var zone = root.Find(ZoneName);
        if (zone == null || zone.childCount == 0) return;
        var children = new List<Transform>();
        foreach (Transform c in zone) children.Add(c);
        foreach (var c in children)
        {
            Undo.SetTransformParent(c, root, "place_zone の外へ出す");
            c.SetSiblingIndex(0);
            Debug.LogWarning($"[TidyDemoVisuals] {root.name}: {c.name} が place_zone の子だったので、{root.name} の直下へ移した");
        }
    }

    static void StripPhysics(GameObject root)
    {
        foreach (var j in root.GetComponentsInChildren<Joint>(true)) Undo.DestroyObjectImmediate(j);
        foreach (var c in root.GetComponentsInChildren<Collider>(true)) Undo.DestroyObjectImmediate(c);
        foreach (var r in root.GetComponentsInChildren<Rigidbody>(true)) Undo.DestroyObjectImmediate(r);
    }

    /// <summary>
    /// 子の Renderer (place_zone の中を除く、有効なものすべて) を囲む箱 (root のローカル座標)。
    /// 名前が visual でなくても、手で子に入れた prefab も含める。古い仮の箱を消し忘れていると、それも含まれる
    /// </summary>
    static bool TryVisualBounds(Transform root, out Bounds bounds)
    {
        bounds = default;
        bool any = false;
        var renderers = root.GetComponentsInChildren<Renderer>();
        var zone = root.Find(ZoneName);
        var toRoot = root.worldToLocalMatrix;
        foreach (var r in renderers)
        {
            if (!r.enabled || r is ParticleSystemRenderer || r is LineRenderer || r is TrailRenderer) continue;
            if (zone != null && r.transform.IsChildOf(zone)) continue;

            Bounds local;
            Matrix4x4 m;
            if (r.TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh != null)
            {
                local = mf.sharedMesh.bounds;
                m = toRoot * r.transform.localToWorldMatrix;
            }
            else
            {
                local = r.bounds; // SkinnedMeshRenderer など: ワールドの範囲
                m = toRoot;
            }
            for (int i = 0; i < 8; i++)
            {
                var corner = local.center + Vector3.Scale(local.extents,
                    new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                var p = m.MultiplyPoint3x4(corner);
                if (!any) { bounds = new Bounds(p, Vector3.zero); any = true; }
                else bounds.Encapsulate(p);
            }
        }
        return any;
    }

    static string SizeText(GameObject go)
    {
        var bc = go.GetComponent<BoxCollider>();
        var s = Abs(Vector3.Scale(bc.size, go.transform.lossyScale));
        return $"{s.x:0.000} x {s.y:0.000} x {s.z:0.000} m";
    }

    static Vector3 Abs(Vector3 v) => new Vector3(Mathf.Abs(v.x), Mathf.Abs(v.y), Mathf.Abs(v.z));
}
