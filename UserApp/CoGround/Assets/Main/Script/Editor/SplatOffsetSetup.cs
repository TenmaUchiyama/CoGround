using SplatXR;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// メニュー CoGround > Splat Offset を配置
/// 開いているシーンのスキャン (スプラットと、そのメッシュの FBX) を、VR のコントローラで部屋に合わせられるようにする。
///   1. 空の親「Splat Align」を作る。シーンにスプラット (SplatXR の Base / LoD Renderer) があれば、その子にする (見た目の位置は変えない)
///   2. スキャンのメッシュ (ScanModelPath の FBX) を Splat Align の子に置く。
///      スプラットがあるときは見た目はスプラットに任せて、FBX は表示しない (自動で重ねるためだけに使う)
///   3. 保存先のアセット Assets/Main/SceneData/SplatOffset.asset を作る (あればそれを使う)
///   4. 「Splat Offset Placer」(SplatOffsetPlacer + MeshIcpAligner) を置き、上のものとシーンの EnvironmentBoxPlacer をつなぐ
/// 何度実行してもよい (あるものは作り直さない)。
///
/// スプラットと FBX は同じスキャンから書き出したもの (同じ座標) を前提にしている。
/// 重ならないときは、FBX のほうの Transform を直してスプラットに合わせる。
/// </summary>
public static class SplatOffsetSetup
{
    const string AlignName = "Splat Align";
    const string PlacerName = "Splat Offset Placer";
    const string AssetPath = "Assets/Main/SceneData/SplatOffset.asset";
    const string ScanModelPath = "Assets/Main/Model/TestLiving/LivingModel.fbx";

    [MenuItem("CoGround/Splat Offset を配置")]
    static void Setup()
    {
        var splat = FindSplat();

        // 1. 空の親
        var align = FindAlign(splat);
        if (align == null)
        {
            var go = new GameObject(AlignName);
            Undo.RegisterCreatedObjectUndo(go, "Splat Offset Setup");
            align = go.transform;
            if (splat != null)
            {
                align.SetPositionAndRotation(splat.position, Quaternion.identity);
                Undo.SetTransformParent(splat, align, "Splat Offset Setup"); // ワールドの位置は変わらない
            }
        }
        if (align.parent != null) Undo.SetTransformParent(align, null, "Splat Offset Setup");

        // 2. スキャンのメッシュ
        var scan = FindScan(align);
        if (scan == null)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ScanModelPath);
            if (model == null)
            {
                EditorUtility.DisplayDialog("Splat Offset", $"スキャンのメッシュが見つからない: {ScanModelPath}", "OK");
                return;
            }
            var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
            Undo.RegisterCreatedObjectUndo(go, "Splat Offset Setup");
            scan = go.transform;
            scan.SetParent(align, false);
            if (splat != null)
            {
                // スプラットと同じ位置・向き・大きさから始める (同じスキャンなら、これで重なる)
                scan.SetPositionAndRotation(splat.position, splat.rotation);
                scan.localScale = splat.lossyScale;
            }
        }
        EnsureReadable(ScanModelPath);
        if (splat != null)
        {
            foreach (var r in scan.GetComponentsInChildren<Renderer>(true))
            {
                Undo.RecordObject(r, "Splat Offset Setup");
                r.enabled = false;
            }
        }

        // 3. 保存先のアセット
        var offset = AssetDatabase.LoadAssetAtPath<SplatOffset>(AssetPath);
        if (offset == null)
        {
            offset = ScriptableObject.CreateInstance<SplatOffset>();
            AssetDatabase.CreateAsset(offset, AssetPath);
            AssetDatabase.SaveAssets();
        }

        // 4. コントローラで動かすコンポーネントと、自動で重ねるコンポーネント
        var placer = Object.FindAnyObjectByType<SplatOffsetPlacer>(FindObjectsInactive.Include);
        if (placer == null)
        {
            var go = new GameObject(PlacerName);
            Undo.RegisterCreatedObjectUndo(go, "Splat Offset Setup");
            placer = go.AddComponent<SplatOffsetPlacer>();
        }
        var aligner = placer.GetComponent<MeshIcpAligner>();
        if (aligner == null) aligner = Undo.AddComponent<MeshIcpAligner>(placer.gameObject);

        var alignerSo = new SerializedObject(aligner);
        alignerSo.FindProperty("source").objectReferenceValue = scan;
        alignerSo.ApplyModifiedProperties();

        var so = new SerializedObject(placer);
        so.FindProperty("offset").objectReferenceValue = offset;
        so.FindProperty("target").objectReferenceValue = align;
        so.FindProperty("aligner").objectReferenceValue = aligner;
        var boxPlacer = Object.FindAnyObjectByType<EnvironmentBoxPlacer>(FindObjectsInactive.Include);
        if (boxPlacer != null) so.FindProperty("boxPlacer").objectReferenceValue = boxPlacer;
        so.ApplyModifiedProperties();

        EditorSceneManager.MarkSceneDirty(placer.gameObject.scene);
        Selection.activeObject = placer.gameObject;
        string splatText = splat != null ? $"スプラット {splat.name} と" : "スプラットは無し。";
        Debug.Log($"[SplatOffsetSetup] {AlignName} の下に{splatText} {scan.name} を置き、{PlacerName} をつないだ (保存先: {AssetPath})。シーンを保存すること", placer);
    }

    static Transform FindSplat()
    {
        var b = Object.FindAnyObjectByType<BaseRendererSplatXR>(FindObjectsInactive.Include);
        if (b != null) return b.transform;
        var l = Object.FindAnyObjectByType<LoDRendererSplatXR>(FindObjectsInactive.Include);
        return l != null ? l.transform : null;
    }

    static Transform FindAlign(Transform splat)
    {
        if (splat != null && splat.parent != null && splat.parent.name == AlignName) return splat.parent;
        var placer = Object.FindAnyObjectByType<SplatOffsetPlacer>(FindObjectsInactive.Include);
        if (placer != null)
        {
            var t = new SerializedObject(placer).FindProperty("target").objectReferenceValue as Transform;
            if (t != null) return t;
        }
        var go = GameObject.Find(AlignName);
        return go != null ? go.transform : null;
    }

    /// <summary>Align の子で、ScanModelPath の FBX から置いたもの</summary>
    static Transform FindScan(Transform align)
    {
        var model = AssetDatabase.LoadAssetAtPath<GameObject>(ScanModelPath);
        foreach (Transform child in align)
        {
            if (PrefabUtility.GetCorrespondingObjectFromSource(child.gameObject) == model) return child;
        }
        return null;
    }

    /// <summary>Play 中に頂点を読めるよう、FBX の Read/Write を ON にする</summary>
    static void EnsureReadable(string path)
    {
        if (AssetImporter.GetAtPath(path) is ModelImporter importer && !importer.isReadable)
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
            Debug.Log($"[SplatOffsetSetup] {path} の Read/Write を ON にした");
        }
    }
}
