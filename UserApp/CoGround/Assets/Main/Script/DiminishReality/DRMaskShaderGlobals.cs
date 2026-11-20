using UnityEngine;

/// <summary>
/// Diminished Reality: sends the mask box transform to the background shader (DR/StencilReadTextured),
/// so it can fade the patch out near the box silhouette (edge feather) instead of a hard cut.
///
/// Put it on the mask box (the Cube with DR_StencilMask.mat). DRMaskFollowDetection adds it to its
/// mask box automatically. Only one mask box is supported (the values are global).
/// </summary>
[DisallowMultipleComponent]
public class DRMaskShaderGlobals : MonoBehaviour
{
    private static readonly int WorldToLocalId = Shader.PropertyToID("_DRMaskWorldToLocal");
    private static readonly int EnabledId = Shader.PropertyToID("_DRMaskEnabled");

    private Renderer _renderer;

    private void Awake()
    {
        _renderer = GetComponent<Renderer>();
    }

    private void LateUpdate()
    {
        // The box is a Unity Cube (local extents -0.5..0.5); the shader works in that space.
        Shader.SetGlobalMatrix(WorldToLocalId, transform.worldToLocalMatrix);
        Shader.SetGlobalFloat(EnabledId, _renderer == null || _renderer.enabled ? 1f : 0f);
    }

    private void OnDisable()
    {
        Shader.SetGlobalFloat(EnabledId, 0f);
    }
}
