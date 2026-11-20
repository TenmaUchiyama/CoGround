using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

/// <summary>
/// メニュー CoGround > 片付けデモを配置
/// Fetch の正面に、机・片付ける物 7 つ・置く場所 3 つを仮の箱で置く (見た目は後で差し替える)。
///
///   片付ける物 (前 0.60 m に 1 列。左から)
///     pet_bottle  ペットボトル        通常
///     water_bottle 水筒               通常
///     can         空き缶              ゴミ (trash = true)
///     tissue      丸めたティッシュ    ゴミ (trash = true)
///     small_box   小さな箱            通常
///     mug         マグカップ          Fragile (fragile = true)
///     plate       皿                  Fragile (fragile = true)
///   置く場所 (前 0.78 m。左から)
///     box_1 / trash_bin / box_2  (place_zone 付き。region_id はこの ID)
///   机: table_1 (上面全体が place_zone。最初は物がここにある)
///
/// 片付ける物は CoGroundSceneObject + MoveItCollisionBox + MoveItPickable。
/// どれもスケール 1 の親 + BoxCollider + 見た目の子 visual (Solid)。見た目は TidyDemoVisuals で差し替える。
/// 置く場所と机は CoGroundSceneObject + MoveItCollisionBox (ロボットは避ける)。
/// GameObject の名前 = ID = MoveIt の Planning Scene の名前。
/// コードからは CoGroundSceneObject.Find("mug") / Items / Places で取れる。
/// </summary>
public static class TidyDemoSetup
{
    const float DeskTop = 0.70f;
    const float DeskThickness = 0.05f;
    const float ItemRow = 0.60f;   // 片付ける物の列 (base_link から前へ)
    const float PlaceRow = 0.78f;  // 置く場所の列 (上からつかめるのは前 0.8 m 程度まで)

    struct Item
    {
        public string id; public CoGroundCategory category; public float left; public Vector3 size; public Color color;
        public bool fragile, trash;
    }

    struct Place
    {
        public string id; public CoGroundCategory category; public float left; public Vector3 size; public Color color;
    }

    static readonly Color Normal = new Color(0.25f, 0.5f, 0.95f);
    static readonly Color Trash = new Color(0.55f, 0.5f, 0.4f);
    static readonly Color Fragile = new Color(0.95f, 0.35f, 0.25f);

    // size = (左右, 高さ, 前後) [m]。つかむのは上から、グリッパーの開きは 0.1 m 弱
    static readonly Item[] Items =
    {
        new Item { id = "pet_bottle",   category = CoGroundCategory.plastic_bottle, left =  0.33f, size = new Vector3(0.05f, 0.10f, 0.05f), color = Normal },
        new Item { id = "water_bottle", category = CoGroundCategory.water_bottle,   left =  0.22f, size = new Vector3(0.06f, 0.10f, 0.06f), color = Normal },
        new Item { id = "can",          category = CoGroundCategory.can,            left =  0.11f, size = new Vector3(0.05f, 0.07f, 0.05f), color = Trash, trash = true },
        new Item { id = "tissue",       category = CoGroundCategory.tissue,         left =  0.00f, size = new Vector3(0.05f, 0.04f, 0.05f), color = Trash, trash = true },
        new Item { id = "small_box",    category = CoGroundCategory.small_box,      left = -0.11f, size = new Vector3(0.06f, 0.05f, 0.06f), color = Normal },
        new Item { id = "mug",          category = CoGroundCategory.mug,            left = -0.22f, size = new Vector3(0.06f, 0.07f, 0.06f), color = Fragile, fragile = true },
        new Item { id = "plate",        category = CoGroundCategory.plate,          left = -0.34f, size = new Vector3(0.12f, 0.02f, 0.12f), color = Fragile, fragile = true },
    };

    static readonly Place[] Places =
    {
        new Place { id = "box_1",     category = CoGroundCategory.storage_box, left =  0.25f, size = new Vector3(0.16f, 0.03f, 0.14f), color = new Color(0.4f, 0.75f, 1f) },
        new Place { id = "trash_bin", category = CoGroundCategory.trash_bin,   left =  0.00f, size = new Vector3(0.16f, 0.03f, 0.14f), color = new Color(0.3f, 0.3f, 0.3f) },
        new Place { id = "box_2",     category = CoGroundCategory.storage_box, left = -0.25f, size = new Vector3(0.16f, 0.03f, 0.14f), color = new Color(0.4f, 0.9f, 0.5f) },
    };

    [MenuItem("CoGround/片付けデモを配置")]
    static void Create()
    {
        Transform baseLink = FindBaseLink();
        if (baseLink == null)
        {
            EditorUtility.DisplayDialog("片付けデモ", "RosJointToFetch が付いた fetch (base_link) が見つかりません。", "OK");
            return;
        }

        Vector3 origin = baseLink.position;
        Vector3 forward = Vector3.ProjectOnPlane(baseLink.forward, Vector3.up).normalized; // ROS の +x
        Vector3 left = Vector3.Cross(forward, Vector3.up);                                  // ROS の +y
        Quaternion yaw = Quaternion.LookRotation(forward, Vector3.up);
        Vector3 At(float x, float y, float z) => origin + forward * x + left * y + Vector3.up * z;

        var root = new GameObject("TidyDemo");
        Undo.RegisterCreatedObjectUndo(root, "片付けデモを配置");

        // 机: 上面の上 20 cm を place_zone (table_1)
        var deskSize = new Vector3(1.0f, DeskThickness, 0.6f);
        Solid("table_1", CoGroundCategory.table, root.transform, At(0.80f, 0f, DeskTop - DeskThickness / 2f), yaw,
              deskSize, new Color(0.55f, 0.4f, 0.3f), new Vector3(deskSize.x, 0.20f, deskSize.z));

        foreach (var p in Places)
        {
            Solid(p.id, p.category, root.transform, At(PlaceRow, p.left, DeskTop + p.size.y / 2f), yaw,
                  p.size, p.color, new Vector3(p.size.x, 0.12f, p.size.z));
        }

        foreach (var it in Items)
        {
            var attrs = new List<(string, string)>
            {
                (AttributeKey.Fragile, it.fragile ? "true" : "false"),
                (AttributeKey.Trash, it.trash ? "true" : "false"),
            };
            var go = Solid(it.id, it.category, root.transform, At(ItemRow, it.left, DeskTop + it.size.y / 2f), yaw,
                           it.size, it.color, null, attrs);
            go.AddComponent<MoveItPickable>();
        }

        if (Object.FindAnyObjectByType<CoGroundSceneReporter>() == null)
            Debug.LogWarning("[TidyDemoSetup] CoGroundSceneReporter がシーンに無いので scene.update は送られない (コードからの参照はできる)");

        Selection.activeGameObject = root;
        Debug.Log("[TidyDemoSetup] 机・片付ける物 7 つ・置く場所 3 つを配置した。シーンを保存してから Play する");
    }

    static Transform FindBaseLink()
    {
        foreach (var robot in Object.FindObjectsByType<RosJointToFetch>(FindObjectsSortMode.None))
        {
            foreach (var t in robot.GetComponentsInChildren<Transform>())
            {
                if (t.name == "base_link") return t;
            }
        }
        return null;
    }

    static Material MakeMaterial(Color color)
    {
        var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
        return new Material(shader) { color = color };
    }

    /// <summary>
    /// どの物も同じ作り: スケール 1 の親 (BoxCollider で形を持つ) + 見た目の子 visual + (置く場所なら) place_zone の子。
    /// 親を拡大縮小すると place_zone の大きさまで変わるうえ、見た目を prefab に差し替えにくいので、こうしている。
    /// 見た目の差し替えは CoGround > 片付けデモの見た目を差し替え (TidyDemoVisuals)。
    /// </summary>
    static GameObject Solid(string id, CoGroundCategory category, Transform parent, Vector3 position, Quaternion rotation,
                            Vector3 size, Color color, Vector3? zoneSize, List<(string, string)> attributes = null)
    {
        var go = new GameObject(id);
        go.transform.SetParent(parent, false);
        go.transform.SetPositionAndRotation(position, rotation);
        go.AddComponent<BoxCollider>().size = size;
        go.AddComponent<MoveItCollisionBox>();

        var visual = GameObject.CreatePrimitive(PrimitiveType.Cube);
        visual.name = "visual";
        Object.DestroyImmediate(visual.GetComponent<Collider>());
        visual.transform.SetParent(go.transform, false);
        visual.transform.localScale = size;
        visual.GetComponent<MeshRenderer>().sharedMaterial = MakeMaterial(color);

        Transform zone = null;
        if (zoneSize is Vector3 zs)
        {
            zone = new GameObject("place_zone").transform;
            zone.SetParent(go.transform, false);
            zone.localPosition = new Vector3(0f, size.y / 2f + zs.y / 2f, 0f);
            zone.localScale = zs;
        }

        AddSceneObject(go, category, attributes, zone);
        return go;
    }

    static void AddSceneObject(GameObject go, CoGroundCategory category, List<(string key, string value)> attributes, Transform placeZone)
    {
        var so = new SerializedObject(go.AddComponent<CoGroundSceneObject>());
        so.FindProperty("objectId").stringValue = go.name;
        so.FindProperty("category").enumValueIndex = (int)category;
        if (attributes != null)
        {
            var list = so.FindProperty("attributes");
            list.arraySize = attributes.Count;
            for (int i = 0; i < attributes.Count; i++)
            {
                var e = list.GetArrayElementAtIndex(i);
                e.FindPropertyRelative("key").stringValue = attributes[i].key;
                e.FindPropertyRelative("value").stringValue = attributes[i].value;
            }
        }
        so.FindProperty("placeZone").objectReferenceValue = placeZone;
        so.ApplyModifiedPropertiesWithoutUndo();
    }
}
