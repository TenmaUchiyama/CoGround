using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// メニュー CoGround > DR 右手マスクを配置
/// Diminished Reality のお試し用に、右コントローラの先にマスクの箱を付ける (DRHandMask)。
///   - 背景は Splat Offset Placer の Aligner の Source (CoGround > Splat Offset を配置 で置いたスキャン。LivingModel)
///     Splat Offset Placer の Target (Splat Align) の下にスプラット (SplatXR/SplatShader) があれば、Target を背景にする
///     (DRHandMask がスプラットだけで DR をする)
///   - 背景用の DR マテリアル (DR/StencilReadTextured + スキャンのテクスチャ) を、スキャンの元のマテリアルの隣に作る
/// 先に CoGround > Splat Offset を配置 を実行しておくこと。何度実行してもよい。
/// </summary>
public static class DRHandMaskSetup
{
    const string ObjectName = "DR Hand Mask";

    [MenuItem("CoGround/DR 右手マスクを配置")]
    static void Setup()
    {
        var placer = Object.FindAnyObjectByType<SplatOffsetPlacer>(FindObjectsInactive.Include);
        var scan = placer != null && placer.Aligner != null ? placer.Aligner.Source : null;
        if (scan == null)
        {
            EditorUtility.DisplayDialog("DR 右手マスク", "背景のスキャンが見つからない。\n先に CoGround > Splat Offset を配置 を実行すること。", "OK");
            return;
        }

        var drMaterial = MakeDrMaterial(scan);
        if (drMaterial == null) return;

        var mask = Object.FindAnyObjectByType<DRHandMask>(FindObjectsInactive.Include);
        if (mask == null)
        {
            var go = new GameObject(ObjectName);
            Undo.RegisterCreatedObjectUndo(go, "DR Hand Mask Setup");
            mask = go.AddComponent<DRHandMask>();
        }
        var so = new SerializedObject(mask);
        var splatRoot = placer.Target != null && HasSplat(placer.Target) ? placer.Target : null;
        so.FindProperty("background").objectReferenceValue = splatRoot != null ? splatRoot : scan;
        so.FindProperty("backgroundDrMaterial").objectReferenceValue = drMaterial;
        so.FindProperty("splatPlacer").objectReferenceValue = placer;
        so.FindProperty("splatDrShader").objectReferenceValue = Shader.Find("DR/StencilReadSplat");
        so.ApplyModifiedProperties();
        if (splatRoot != null) scan = splatRoot;

        EditorSceneManager.MarkSceneDirty(mask.gameObject.scene);
        Selection.activeObject = mask.gameObject;
        Debug.Log($"[DRHandMaskSetup] {ObjectName} を置いた (背景: {scan.name}、マテリアル: {AssetDatabase.GetAssetPath(drMaterial)})。シーンを保存すること", mask);
    }

    static bool HasSplat(Transform root)
    {
        foreach (var r in root.GetComponentsInChildren<Renderer>(true))
            foreach (var m in r.sharedMaterials)
                if (m != null && m.shader != null && m.shader.name == "SplatXR/SplatShader") return true;
        return false;
    }

    /// <summary>スキャンの最初のマテリアルのテクスチャで、DR/StencilReadTextured のマテリアルを作る (あればそれを使う)</summary>
    static Material MakeDrMaterial(Transform scan)
    {
        var renderer = scan.GetComponentInChildren<Renderer>(true);
        var source = renderer != null ? renderer.sharedMaterial : null;
        if (source == null)
        {
            EditorUtility.DisplayDialog("DR 右手マスク", $"{scan.name} にマテリアルが無い", "OK");
            return null;
        }
        if (source.shader != null && source.shader.name == "DR/StencilReadTextured") return source;

        string sourcePath = AssetDatabase.GetAssetPath(source);
        string dir = string.IsNullOrEmpty(sourcePath) ? "Assets/Main/Material/DiminishReality" : System.IO.Path.GetDirectoryName(sourcePath).Replace('\\', '/');
        string path = $"{dir}/{scan.name}_DR.mat";

        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material != null) return material;

        var shader = Shader.Find("DR/StencilReadTextured");
        if (shader == null)
        {
            EditorUtility.DisplayDialog("DR 右手マスク", "シェーダー DR/StencilReadTextured が見つからない", "OK");
            return null;
        }
        material = new Material(shader);
        var texture = source.HasProperty("_MainTex") ? source.GetTexture("_MainTex") : null;
        if (texture == null && source.HasProperty("_BaseMap")) texture = source.GetTexture("_BaseMap");
        if (texture == null) texture = source.mainTexture;
        material.SetTexture("_MainTex", texture);
        material.SetInt("_StencilRef", 1);
        AssetDatabase.CreateAsset(material, path);
        AssetDatabase.SaveAssets();
        if (texture == null) Debug.LogWarning($"[DRHandMaskSetup] {source.name} のテクスチャが取れなかった。{path} の Texture を手で入れること", material);
        return material;
    }
}
