using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Diminished Reality: sends the mask box transforms to the background shaders (DR/StencilReadTextured, DR/StencilReadSplat),
/// so it can fade the patch out near the box silhouette (edge feather) instead of a hard cut.
///
/// Put it on every mask box (a Cube with the DR/StencilMask shader). DRMaskFollowDetection and
/// CoGroundAfterView add it to their mask boxes automatically.
/// Up to <see cref="MaxBoxes"/> boxes get the feather. With more boxes the feather is switched off
/// (hard edges), the masks themselves still work.
/// </summary>
[DisallowMultipleComponent]
public class DRMaskShaderGlobals : MonoBehaviour
{
    /// <summary>Same as DR_MASK_MAX in DR_StencilReadTextured.shader and DR_StencilReadSplat.shader.</summary>
    public const int MaxBoxes = 8;

    private static readonly int WorldToLocalId = Shader.PropertyToID("_DRMaskWorldToLocal");
    private static readonly int CountId = Shader.PropertyToID("_DRMaskCount");

    private static readonly List<DRMaskShaderGlobals> Boxes = new List<DRMaskShaderGlobals>();
    private static readonly Matrix4x4[] Matrices = new Matrix4x4[MaxBoxes];
    private static bool _warnedTooMany;

    private Renderer _renderer;

    private void Awake()
    {
        _renderer = GetComponent<Renderer>();
    }

    private void OnEnable()
    {
        Boxes.Add(this);
    }

    private void OnDisable()
    {
        Boxes.Remove(this);
        Push();
    }

    private void LateUpdate()
    {
        Push();
    }

    /// <summary>The boxes are Unity Cubes (local extents -0.5..0.5); the shader works in that space.</summary>
    private static void Push()
    {
        var count = 0;
        var tooMany = false;
        foreach (var box in Boxes)
        {
            if (box._renderer != null && !box._renderer.enabled) continue;
            if (count == MaxBoxes) { tooMany = true; break; }
            Matrices[count++] = box.transform.worldToLocalMatrix;
        }

        if (tooMany)
        {
            // A box the shader does not know would be faded out completely, so no feather at all.
            count = 0;
            if (!_warnedTooMany)
            {
                _warnedTooMany = true;
                Debug.LogWarning($"[{nameof(DRMaskShaderGlobals)}] More than {MaxBoxes} mask boxes: edge feather is off.");
            }
        }

        Shader.SetGlobalMatrixArray(WorldToLocalId, Matrices); // always the full length (the size is fixed on first use)
        Shader.SetGlobalFloat(CountId, count);
    }
}
