using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>
/// メニュー CoGround > ルール表示の見本を作る (UI.unity)
/// UI.unity に、5 種類 (義務・禁止・判断できない・計画できない・許可) × 3 つの形
/// (物体の吹き出し・置き場所の看板・床の模様) を並べる。もう一度押すと作り直す。
/// 吹き出し・看板・床は Assets/Main/Resources/RuleTag の Prefab を置く (無ければ RuleTagPrefabBuilder で作る)。
/// </summary>
public static class RuleTagSampleSetup
{
    const string ScenePath = "Assets/Main/Scene/UI.unity";
    const string RootName = "Rule Tag Samples";

    struct Sample
    {
        public CoGroundRuleKind Kind;
        public string About;
        public string ObjName, ObjId, ObjText, ObjNote;
        public string PlaceName, PlaceId, PlaceText, PlaceNote;
        public string AreaId, AreaText, AreaNote;
    }

    static readonly Sample[] Samples =
    {
        new Sample { Kind = CoGroundRuleKind.Obligation, About = "しなければならない",
            ObjName = "皿", ObjId = "O1", ObjText = "使った皿は流しへ", ObjNote = "O1 に従って流しへ運ぶ",
            PlaceName = "流し", PlaceId = "O1", PlaceText = "皿はここへ", PlaceNote = "",
            AreaId = "O2", AreaText = "ロボットはここで待つ", AreaNote = "" },
        new Sample { Kind = CoGroundRuleKind.Prohibition, About = "してはいけない",
            ObjName = "財布", ObjId = "N1", ObjText = "触らない", ObjNote = "N1 に反するので残す",
            PlaceName = "本棚", PlaceId = "N2", PlaceText = "物を置かない", PlaceNote = "",
            AreaId = "N3", AreaText = "18時以降 立入禁止", AreaNote = "" },
        new Sample { Kind = CoGroundRuleKind.Undecided, About = "ルールだけでは決められない",
            ObjName = "ペン", ObjId = "U1", ObjText = "誰の物か分からない", ObjNote = "候補: O1 / N2",
            PlaceName = "机", PlaceId = "U2", PlaceText = "置き場所が 2 つある", PlaceNote = "",
            AreaId = "U3", AreaText = "範囲が決まっていない", AreaNote = "" },
        new Sample { Kind = CoGroundRuleKind.Infeasible, About = "ロボットが実行できない",
            ObjName = "鍋", ObjId = "P1", ObjText = "重くて持てない", ObjNote = "動かし方を計画できない",
            PlaceName = "高い棚", PlaceId = "P2", PlaceText = "腕が届かない", PlaceNote = "",
            AreaId = "P3", AreaText = "狭くて通れない", AreaNote = "" },
        new Sample { Kind = CoGroundRuleKind.Permission, About = "禁止の例外として、してよい",
            ObjName = "コップ", ObjId = "N1", ObjText = "洗い物なら運んでよい", ObjNote = "N1「触らない」の例外",
            PlaceName = "テレビ台", PlaceId = "N2", PlaceText = "一時置きはよい", PlaceNote = "N2「物を置かない」の例外",
            AreaId = "N3", AreaText = "掃除中は入ってよい", AreaNote = "N3「立入禁止」の例外" },
    };

    [MenuItem("CoGround/ルール表示の見本を作る (UI.unity)")]
    static void Build()
    {
        if (SceneManager.GetActiveScene().path != ScenePath)
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.OpenScene(ScenePath);
        }

        // Prefab が無ければ作る (あれば手で直したものをそのまま使う)
        RuleTagPrefabBuilder.EnsureStyleAsset();
        if (!RuleTagPrefabBuilder.Exists() && !RuleTagPrefabBuilder.BuildAll()) return;
        var bubble = AssetDatabase.LoadAssetAtPath<GameObject>(RuleTagPrefabBuilder.BubblePath);
        var sign = AssetDatabase.LoadAssetAtPath<GameObject>(RuleTagPrefabBuilder.SignPath);
        var floorArea = AssetDatabase.LoadAssetAtPath<GameObject>(RuleTagPrefabBuilder.FloorPath);

        var old = GameObject.Find(RootName);
        if (old != null) Undo.DestroyObjectImmediate(old);
        var root = new GameObject(RootName);
        Undo.RegisterCreatedObjectUndo(root, "ルール表示の見本");

        var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.SetParent(root.transform, false);
        floor.transform.localScale = new Vector3(0.8f, 1f, 0.5f);
        floor.transform.localPosition = new Vector3(0f, 0f, 0.5f);
        floor.GetComponent<Renderer>().sharedMaterial = SolidMaterial("Rule Sample Floor", new Color(0.82f, 0.82f, 0.8f));

        const float spacing = 1.4f;
        for (int i = 0; i < Samples.Length; i++)
        {
            var s = Samples[i];
            var col = new GameObject($"{i + 1} {CoGroundRuleStyle.Label(s.Kind)}").transform;
            col.SetParent(root.transform, false);
            col.localPosition = new Vector3((i - (Samples.Length - 1) * 0.5f) * spacing, 0f, 0f);

            // 列の見出し (種類の名前と意味。置き場所の看板の上に浮かべる)
            AddTag(bubble, col, "見出し", new Vector3(0f, 1.45f, 0.9f), s.Kind, "", CoGroundRuleStyle.Label(s.Kind), s.About, false);

            // 床のエリア (いちばん手前)
            var area = AddTag(floorArea, col, "床のエリア", new Vector3(0f, 0f, -0.9f), s.Kind, s.AreaId, s.AreaText, s.AreaNote);
            area.SetAreaSize(new Vector2(1.1f, 0.7f));
            PrefabUtility.RecordPrefabInstancePropertyModifications(area);

            // 物体 + 吹き出し
            var obj = Box(col, s.ObjName, new Vector3(0f, 0.06f, 0f), new Vector3(0.2f, 0.12f, 0.2f), new Color(0.95f, 0.95f, 0.93f));
            AddTag(bubble, col, $"吹き出し {s.ObjName}", Top(obj) + Vector3.up * 0.04f - col.position, s.Kind, s.ObjId, s.ObjText, s.ObjNote);

            // 置き場所 + 看板
            var place = Box(col, s.PlaceName, new Vector3(0f, 0.3f, 0.9f), new Vector3(0.7f, 0.6f, 0.4f), new Color(0.55f, 0.42f, 0.3f));
            AddTag(sign, col, $"看板 {s.PlaceName}", Top(place) - col.position, s.Kind, s.PlaceId, s.PlaceText, s.PlaceNote);
        }

        // Game ビューで全体が見えるように
        var cam = Camera.main;
        if (cam != null)
        {
            Undo.RecordObject(cam.transform, "ルール表示の見本");
            cam.transform.position = new Vector3(0f, 2.4f, -4.4f);
            cam.transform.LookAt(new Vector3(0f, 0.5f, 0.2f));
        }

        EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
        Selection.activeGameObject = root;
        Debug.Log("[RuleTagSampleSetup] ルール表示の見本を作った。シーンを保存すること");
    }

    /// <summary>Prefab を置いて色と文字を入れる (Prefab とのつながりは保つ)</summary>
    static CoGroundRuleTag AddTag(GameObject prefab, Transform parent, string name, Vector3 localPos,
        CoGroundRuleKind kind, string id, string text, string note, bool showKind = true)
    {
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
        go.name = name;
        go.transform.localPosition = localPos;
        var tag = go.GetComponent<CoGroundRuleTag>();
        tag.Set(kind, id, text, note, showKind);
        PrefabUtility.RecordPrefabInstancePropertyModifications(tag);
        PrefabUtility.RecordPrefabInstancePropertyModifications(go.transform);
        return tag;
    }

    /// <summary>箱の上面の中心</summary>
    static Vector3 Top(Transform box)
    {
        var b = box.GetComponent<Renderer>().bounds;
        return new Vector3(b.center.x, b.max.y, b.center.z);
    }

    static Transform Box(Transform parent, string name, Vector3 pos, Vector3 size, Color color)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.localPosition = pos;
        go.transform.localScale = size;
        go.GetComponent<Renderer>().sharedMaterial = SolidMaterial($"Rule Sample {name}", color);
        return go.transform;
    }

    /// <summary>見本用の不透明マテリアル (シーンに埋め込まず Assets/Main/Material/RuleSample に保存)</summary>
    static Material SolidMaterial(string name, Color color)
    {
        const string dir = "Assets/Main/Material/RuleSample";
        if (!AssetDatabase.IsValidFolder(dir)) AssetDatabase.CreateFolder("Assets/Main/Material", "RuleSample");
        string path = $"{dir}/{name}.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            m = new Material(shader);
            AssetDatabase.CreateAsset(m, path);
        }
        if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", color);
        m.color = color;
        EditorUtility.SetDirty(m);
        return m;
    }
}
