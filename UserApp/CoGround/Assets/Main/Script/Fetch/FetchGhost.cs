using UnityEngine;

/// <summary>
/// 半透明の「ゴースト」(RViz のオレンジの目標や緑の計画結果のような表示) を作る共通処理。
/// </summary>
public static class FetchGhost
{
    /// <summary>
    /// 半透明のマテリアルを作る。URP では Resources のテンプレートを複製し、
    /// ビルドにも半透明シェーダーバリアントを含める。
    /// </summary>
    public static Material MakeMaterial(Color color)
    {
        if (UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline is
            UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset)
        {
            var template = Resources.Load<Material>("FetchGhostURP");
            if (template == null)
                throw new System.InvalidOperationException("FetchGhostURP material is missing from Resources.");

            var material = new Material(template);
            material.SetColor("_BaseColor", color);
            return material;
        }

        var standard = Shader.Find("Standard");
        if (standard != null)
        {
            // Standard の Rendering Mode = Fade と同じ設定
            var m = new Material(standard);
            m.SetFloat("_Mode", 2f);
            m.SetOverrideTag("RenderType", "Transparent");
            m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            m.SetInt("_ZWrite", 0);
            m.DisableKeyword("_ALPHATEST_ON");
            m.EnableKeyword("_ALPHABLEND_ON");
            m.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
            m.color = color;
            return m;
        }
        var fallback = Shader.Find("Legacy Shaders/Transparent/Diffuse") ?? Shader.Find("Sprites/Default");
        return new Material(fallback) { color = color };
    }

    /// <summary>
    /// src 以下の表示用メッシュだけを複製した、物理も URDF のスクリプトも持たない見た目だけの GameObject を作る。
    /// 戻り値のルートは src と同じ位置・向きに置かれる (= src のリンク座標系)。
    /// </summary>
    public static GameObject CreateVisualCopy(Transform src, string name, Material material)
    {
        var root = new GameObject(name);
        root.transform.SetPositionAndRotation(src.position, src.rotation);
        Matrix4x4 srcInv = src.worldToLocalMatrix;
        foreach (var renderer in src.GetComponentsInChildren<MeshRenderer>())
        {
            if (!renderer.enabled) continue;
            var filter = renderer.GetComponent<MeshFilter>();
            if (filter == null || filter.sharedMesh == null) continue;

            var go = new GameObject(renderer.name);
            go.transform.SetParent(root.transform, false);
            Matrix4x4 rel = srcInv * renderer.transform.localToWorldMatrix;
            go.transform.localPosition = rel.GetPosition();
            go.transform.localRotation = rel.rotation;
            go.transform.localScale = rel.lossyScale;
            go.AddComponent<MeshFilter>().sharedMesh = filter.sharedMesh;
            var r = go.AddComponent<MeshRenderer>();
            var mats = new Material[renderer.sharedMaterials.Length];
            for (int i = 0; i < mats.Length; i++) mats[i] = material;
            r.sharedMaterials = mats;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }
        return root;
    }
}
