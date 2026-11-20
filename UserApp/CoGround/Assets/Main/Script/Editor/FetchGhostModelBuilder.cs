using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using UnityEditor;
using UnityEngine;

/// <summary>
/// メニュー CoGround > Fetch ゴーストの準備
///   1. シーンの Fetch (RosJointToFetch が付いたもの) から、見た目だけのゴースト用モデル
///      Assets/Main/Resources/FetchGhostModel.prefab を作る (作り直す)。
///        - リンクの親子関係はそのまま。残すのは Transform / MeshFilter / MeshRenderer だけ
///          (ArticulationBody・コライダー・スクリプトは全部外す。Collisions のメッシュも消す)
///        - 関節の情報 (名前・回転/直動・軸・関節 0 の姿勢) は URDF (fetch.urdf) から読んで FetchGhostRig に入れる
///   2. その Fetch に FetchRobotModeInfo (本物を使うときに無効にする一覧) が無ければ付ける。
///
/// Fetch を読むのはこのメニューを実行したときだけ。実行中 (Play) のゴーストは本物を読まない。
/// Fetch の URDF を取り込み直したら、もう一度実行する。
/// </summary>
public static class FetchGhostModelBuilder
{
    const string UrdfPath = "Assets/Main/URDF/Fetch/fetch.urdf";
    const string PrefabPath = "Assets/Main/Resources/" + FetchGhostRig.ResourceName + ".prefab";

    [MenuItem("CoGround/Fetch ゴーストの準備 (ゴースト用モデルを作る)")]
    static void Build()
    {
        if (EditorApplication.isPlaying)
        {
            EditorUtility.DisplayDialog("Fetch ゴーストの準備", "Play を止めてから実行する。", "OK");
            return;
        }
        var source = FindSource();
        if (source == null)
        {
            EditorUtility.DisplayDialog("Fetch ゴーストの準備", "RosJointToFetch が付いた fetch がシーンに見つからない。", "OK");
            return;
        }
        if (!File.Exists(UrdfPath))
        {
            EditorUtility.DisplayDialog("Fetch ゴーストの準備", $"{UrdfPath} が見つからない。", "OK");
            return;
        }

        var copy = UnityEngine.Object.Instantiate(source);
        try
        {
            copy.name = "FetchGhostModel";
            copy.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);

            StripToVisuals(copy);

            var linkByName = new Dictionary<string, Transform>();
            foreach (var t in copy.GetComponentsInChildren<Transform>(true))
                if (!linkByName.ContainsKey(t.name)) linkByName[t.name] = t;

            var joints = ReadJoints(linkByName, out var missing);
            linkByName.TryGetValue("base_link", out var baseLink);

            var rig = copy.AddComponent<FetchGhostRig>();
            rig.EditorSetup(baseLink != null ? baseLink : copy.transform, joints);

            Directory.CreateDirectory(Path.GetDirectoryName(PrefabPath));
            PrefabUtility.SaveAsPrefabAsset(copy, PrefabPath, out bool ok);
            if (!ok) throw new Exception($"{PrefabPath} を保存できなかった");

            int renderers = copy.GetComponentsInChildren<MeshRenderer>(true).Length;
            Debug.Log($"[FetchGhostModelBuilder] {PrefabPath} を作成 (元: {source.name}, 関節 {joints.Count} 個, メッシュ {renderers} 個)" +
                      (missing.Count > 0 ? $"。リンクが見つからない関節: {string.Join(", ", missing)}" : ""));
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(copy);
        }

        if (source.GetComponent<FetchRobotModeInfo>() == null)
        {
            Undo.AddComponent<FetchRobotModeInfo>(source);
            Debug.Log($"[FetchGhostModelBuilder] {source.name} に FetchRobotModeInfo を付けた (シーンを保存する)");
        }
        Selection.activeObject = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
    }

    static GameObject FindSource()
    {
        var selected = Selection.activeGameObject != null ? Selection.activeGameObject.GetComponentInParent<RosJointToFetch>() : null;
        if (selected != null) return selected.gameObject;
        var robots = UnityEngine.Object.FindObjectsByType<RosJointToFetch>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        return robots.Length > 0 ? robots[0].gameObject : null;
    }

    // Transform / MeshFilter / MeshRenderer 以外を全部外し、表示されていないメッシュ (Collisions など) を消す
    static void StripToVisuals(GameObject root)
    {
        foreach (var t in root.GetComponentsInChildren<Transform>(true).Where(t => t != null && t.name == "Collisions").ToArray())
            if (t != null) UnityEngine.Object.DestroyImmediate(t.gameObject);

        foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
        {
            if (r.enabled) continue;
            var f = r.GetComponent<MeshFilter>();
            UnityEngine.Object.DestroyImmediate(r);
            if (f != null) UnityEngine.Object.DestroyImmediate(f);
        }

        // RequireComponent で他から必要とされているものは先に外せないので、外せるものから外していく
        for (int pass = 0; pass < 10; pass++)
        {
            var rest = root.GetComponentsInChildren<Component>(true).Where(c => c != null && !Keep(c)).ToArray();
            if (rest.Length == 0) return;
            bool removed = false;
            foreach (var c in rest)
            {
                if (c == null || RequiredByOthers(c)) continue;
                UnityEngine.Object.DestroyImmediate(c);
                removed = true;
            }
            if (!removed) break;
        }
        var left = root.GetComponentsInChildren<Component>(true).Where(c => c != null && !Keep(c)).Select(c => c.GetType().Name).Distinct().ToArray();
        if (left.Length > 0) Debug.LogWarning($"[FetchGhostModelBuilder] 外せなかったコンポーネント: {string.Join(", ", left)}");
    }

    static bool Keep(Component c) => c is Transform || c is MeshFilter || c is MeshRenderer;

    static bool RequiredByOthers(Component c)
    {
        var type = c.GetType();
        foreach (var other in c.GetComponents<Component>())
        {
            if (other == null || other == c) continue;
            foreach (RequireComponent req in other.GetType().GetCustomAttributes(typeof(RequireComponent), true))
            {
                foreach (var t in new[] { req.m_Type0, req.m_Type1, req.m_Type2 })
                    if (t != null && t.IsAssignableFrom(type)) return true;
            }
        }
        return false;
    }

    // URDF の可動関節 (revolute / continuous / prismatic) を読む
    static List<FetchGhostRig.Joint> ReadJoints(Dictionary<string, Transform> linkByName, out List<string> missing)
    {
        var joints = new List<FetchGhostRig.Joint>();
        missing = new List<string>();
        var doc = XDocument.Load(UrdfPath);
        foreach (var j in doc.Root.Elements("joint"))
        {
            string type = (string)j.Attribute("type");
            if (type != "revolute" && type != "continuous" && type != "prismatic") continue;
            string name = (string)j.Attribute("name");
            string child = (string)j.Element("child")?.Attribute("link");
            if (child == null || !linkByName.TryGetValue(child, out var link))
            {
                missing.Add(name);
                continue;
            }
            var axisRos = ParseVector((string)j.Element("axis")?.Attribute("xyz") ?? "1 0 0");
            // ROS (x 前, y 左, z 上) → Unity: To<FLU> と同じ対応 (x, y, z) → (-y, z, x)
            var axis = new Vector3(-axisRos.y, axisRos.z, axisRos.x).normalized;
            joints.Add(new FetchGhostRig.Joint
            {
                name = name,
                prismatic = type == "prismatic",
                link = link,
                axis = axis,
                restPosition = link.localPosition,
                restRotation = link.localRotation,
            });
        }
        return joints;
    }

    static Vector3 ParseVector(string s)
    {
        var p = s.Split((char[])null, StringSplitOptions.RemoveEmptyEntries)
                 .Select(v => float.Parse(v, CultureInfo.InvariantCulture)).ToArray();
        return p.Length >= 3 ? new Vector3(p[0], p[1], p[2]) : Vector3.right;
    }
}
