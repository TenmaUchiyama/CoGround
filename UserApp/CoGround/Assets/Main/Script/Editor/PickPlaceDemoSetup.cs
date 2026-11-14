using UnityEditor;
using UnityEngine;

/// <summary>
/// メニュー CoGround > Pick &amp; Place デモを配置
/// Fetch の正面に、机・小さい箱 2 つ (BoxA / BoxB)・置き場所 2 つ (PlaceA / PlaceB) を置く。
/// 位置は ROS 側で計画できることを確認した配置 (base_link 基準):
///   机   : 中心 前 0.85 m、上面の高さ 0.70 m、大きさ 前後 0.6 × 左右 1.0 × 厚さ 0.05 m
///   BoxA : 前 0.65 m、左 0.15 m (5 cm の立方体)   → PlaceA : 前 0.75 m、右 0.30 m
///   BoxB : 前 0.65 m、右 0.15 m                    → PlaceB : 前 0.75 m、左 0.30 m
/// 胴体を上げても上からつかめるのは正面 0.8 m 程度まで。
/// </summary>
public static class PickPlaceDemoSetup
{
    const float DeskTop = 0.70f;
    const float DeskThickness = 0.05f;
    const float BoxSize = 0.05f;

    [MenuItem("CoGround/Pick & Place デモを配置")]
    static void Create()
    {
        Transform baseLink = FindBaseLink();
        if (baseLink == null)
        {
            EditorUtility.DisplayDialog("Pick & Place デモ", "RosJointToFetch が付いた fetch (base_link) が見つかりません。", "OK");
            return;
        }

        Vector3 origin = baseLink.position;
        Vector3 forward = Vector3.ProjectOnPlane(baseLink.forward, Vector3.up).normalized; // ROS の +x
        Vector3 left = Vector3.Cross(forward, Vector3.up);                                  // ROS の +y
        Quaternion yaw = Quaternion.LookRotation(forward, Vector3.up);
        Vector3 At(float x, float y, float z) => origin + forward * x + left * y + Vector3.up * z;

        var root = new GameObject("PickPlaceDemo");
        Undo.RegisterCreatedObjectUndo(root, "Pick & Place デモを配置");

        // 机 (上面の高さ DeskTop)
        var desk = Cube("Desk", root.transform, At(0.85f, 0f, DeskTop - DeskThickness / 2f), yaw,
                        new Vector3(1.0f, DeskThickness, 0.6f), new Color(0.55f, 0.4f, 0.3f));
        desk.AddComponent<MoveItCollisionBox>();

        var red = new Color(0.9f, 0.25f, 0.2f);
        var blue = new Color(0.2f, 0.45f, 0.95f);
        Box("BoxA", root.transform, At(0.65f, 0.15f, DeskTop + BoxSize / 2f), yaw, red);
        Box("BoxB", root.transform, At(0.65f, -0.15f, DeskTop + BoxSize / 2f), yaw, blue);
        Target("PlaceA", root.transform, At(0.75f, -0.30f, DeskTop), yaw, red);
        Target("PlaceB", root.transform, At(0.75f, 0.30f, DeskTop), yaw, blue);

        if (Object.FindAnyObjectByType<MoveItArmPanel>() == null)
        {
            Undo.AddComponent<MoveItArmPanel>(baseLink.GetComponentInParent<RosJointToFetch>().gameObject);
        }
        Selection.activeGameObject = root;
        Debug.Log("[PickPlaceDemoSetup] 机・BoxA/BoxB・PlaceA/PlaceB を配置した。シーンを保存してから Play する");
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

    static GameObject Cube(string name, Transform parent, Vector3 position, Quaternion rotation, Vector3 scale, Color color)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.SetPositionAndRotation(position, rotation);
        go.transform.localScale = scale;
        var mat = new Material(Shader.Find("Standard")) { color = color };
        go.GetComponent<MeshRenderer>().sharedMaterial = mat;
        return go;
    }

    static void Box(string name, Transform parent, Vector3 position, Quaternion rotation, Color color)
    {
        var go = Cube(name, parent, position, rotation, Vector3.one * BoxSize, color);
        go.AddComponent<MoveItCollisionBox>();
        go.AddComponent<MoveItPickable>();
    }

    static void Target(string name, Transform parent, Vector3 position, Quaternion rotation, Color color)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        go.transform.SetPositionAndRotation(position, rotation);
        var target = go.AddComponent<MoveItPlaceTarget>();
        var so = new SerializedObject(target);
        so.FindProperty("color").colorValue = new Color(color.r, color.g, color.b, 0.35f);
        so.ApplyModifiedPropertiesWithoutUndo();
    }
}
