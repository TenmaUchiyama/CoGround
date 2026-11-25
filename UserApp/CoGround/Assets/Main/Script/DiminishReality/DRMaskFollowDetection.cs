using System;
using Meta.XR.BuildingBlocks.AIBlocks;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// Diminished Reality: moves a mask box (DR/StencilMask material) onto a real object
/// found by the Object Detection building block, e.g. a keyboard on the desk.
///
/// Flow:
///   ObjectDetectionAgent
///   -> DetectionPipeline (shared with DetectionBox3DSpawner):
///        2D box to 3D with rays against the environment depth (EnvironmentRaycastManager),
///        or against colliders in the scene (e.g. a MeshCollider on the aligned desk scan) when depth is not available,
///        then tracking, smoothing and locking once stable.
///   -> this script picks the track with the target label and fits the mask box around it.
///
/// Anything drawn with DR/StencilReadTextured (the desk scan) then shows only inside the box,
/// so the object looks removed.
///
/// Smoothing and locking are configured on the DetectionPipeline component (added next to the agent
/// automatically if it is missing).
/// </summary>
public class DRMaskFollowDetection : MonoBehaviour
{
    [Header("Detection (from [BuildingBlock] Object Detection)")]
    [SerializeField] private ObjectDetectionAgent agent;

    [Tooltip("Shared 2D -> 3D + tracking. Found or added next to the agent if empty.")]
    [SerializeField] private DetectionPipeline pipeline;

    [Tooltip("Class name to hide (see Assets/MetaXR/class_labels.txt).")]
    [SerializeField] private string targetLabel = "keyboard";

    [Header("3D position")]
    [Tooltip("Layers the collider ray may hit when environment depth gives no hit. Put a MeshCollider on the desk scan (House) so the ray lands on the desk.")]
    [SerializeField] private LayerMask raycastLayers = ~0;

    [Header("Mask")]
    [Tooltip("The box with the DR_StencilMask material (e.g. DR_MaskBox).")]
    [SerializeField] private Transform maskBox;

    [Tooltip("Hide the mask until the target has been found once.")]
    [SerializeField] private bool hideUntilDetected = true;

    [Header("Box size")]
    [Tooltip("Extra size around the detected footprint (1.2 = 20% larger).")]
    [SerializeField] private float sizeMargin = 1.2f;

    [Tooltip("Minimum depth (front-to-back) of the box in metres.")]
    [SerializeField] private float minDepth = 0.2f;

    [Tooltip("How far the box goes below the bottom of the detected object (metres). Should reach into the desk.")]
    [SerializeField] private float extentBelow = 0.05f;

    [Tooltip("How far the box goes above the top of the detected object (metres).")]
    [SerializeField] private float extentAbove = 0.04f;

    [Header("Debug")]
    [Tooltip("Write a Debug.Log line when the mask starts following an object and when it locks.")]
    [SerializeField] private bool logDetections = true;

    [Tooltip("Draw the outline of the mask box (the box itself is invisible). Green = following, gray = locked.\n" +
             "Drawn on top of everything, so the edges on the far side are visible too.\n" +
             "Keyboard: Space = show / hide.")]
    [SerializeField] private bool showDebugOutline = true;

    [SerializeField] private float outlineWidth = 0.002f;

    [Tooltip("Outline color while following (RGB only, the strength is Outline Alpha).")]
    [SerializeField] private Color outlineColor = new Color(0.7f, 1f, 0.75f, 1f);

    [Tooltip("Outline color once locked (RGB only, the strength is Outline Alpha).")]
    [SerializeField] private Color outlineLockedColor = new Color(0.75f, 0.75f, 0.75f, 1f);

    [Tooltip("How strong the outline is (0 = invisible, 1 = solid). Keyboard: I = brighter, K = darker / fainter. Logged on change.")]
    [Range(0f, 1f)]
    [SerializeField] private float outlineAlpha = 0.35f;

    [Tooltip("How much I / K change Outline Alpha per press.")]
    [SerializeField] private float outlineAlphaStep = 0.05f;

    private Renderer _maskRenderer;
    private LineRenderer _outline;
    private int _trackId = -1;

    /// <summary>True once the box has stopped following detections.</summary>
    public bool IsLocked { get; private set; }

    private void Awake()
    {
        if (!agent) agent = FindFirstObjectByType<ObjectDetectionAgent>();
        if (!pipeline) pipeline = DetectionPipeline.GetOrCreate(agent);

        if (!pipeline || !maskBox)
        {
            Debug.LogError($"[{nameof(DRMaskFollowDetection)}] agent / maskBox is not set.", this);
            enabled = false;
            return;
        }

        _maskRenderer = maskBox.GetComponent<Renderer>();
        // Edge feather in DR/StencilReadTextured needs the box transform.
        if (!maskBox.GetComponent<DRMaskShaderGlobals>()) maskBox.gameObject.AddComponent<DRMaskShaderGlobals>();
        // The mask box itself must not be hit by the collider rays.
        pipeline.EnablePhysicsFallback(raycastLayers, maskBox.GetComponentsInChildren<Collider>(true));

        if (hideUntilDetected && _maskRenderer) _maskRenderer.enabled = false;
        _outline = CreateOutline(maskBox, outlineWidth); // created even when hidden, so Space can show it

        Debug.Log($"[{nameof(DRMaskFollowDetection)}] Ready. pipeline='{pipeline.name}' mask='{maskBox.name}' target='{targetLabel}'", this);
    }

    /// <summary>Unlock and follow detections again (e.g. after the object was moved).</summary>
    public void ResetMask()
    {
        pipeline.ResetTracks(targetLabel);
        IsLocked = false;
        _trackId = -1;
        if (hideUntilDetected && _maskRenderer) _maskRenderer.enabled = false;
    }

    private void LateUpdate()
    {
        if (!_outline) return;
        // Visible only while the mask is active.
        _outline.enabled = showDebugOutline && maskBox.gameObject.activeInHierarchy && (!_maskRenderer || _maskRenderer.enabled);
        var c = IsLocked ? outlineLockedColor : outlineColor;
        c.a = outlineAlpha;
        _outline.startColor = _outline.endColor = c;
    }

    /// <summary>Space = outline on / off, I = brighter, K = darker / fainter.</summary>
    private void HandleKeys()
    {
        if (KeyDown(Key.Space))
        {
            showDebugOutline = !showDebugOutline;
            Debug.Log($"[{nameof(DRMaskFollowDetection)}] Outline {(showDebugOutline ? "on" : "off")}", this);
        }
        var delta = (KeyDown(Key.I) ? 1 : 0) - (KeyDown(Key.K) ? 1 : 0);
        if (delta != 0)
        {
            outlineAlpha = Mathf.Clamp01(Mathf.Round((outlineAlpha + delta * outlineAlphaStep) * 1000f) / 1000f);
            Debug.Log($"[{nameof(DRMaskFollowDetection)}] Outline alpha = {outlineAlpha:0.00}", this);
        }
    }

#if ENABLE_INPUT_SYSTEM
    private static bool KeyDown(Key key) => Keyboard.current != null && Keyboard.current[key].wasPressedThisFrame;
#else
    private enum Key { Space = KeyCode.Space, I = KeyCode.I, K = KeyCode.K }
    private static bool KeyDown(Key key) => Input.GetKeyDown((KeyCode)key);
#endif

    /// <summary>Wireframe of the unit cube as a child of the box, so it follows the box position, rotation and size.</summary>
    private static LineRenderer CreateOutline(Transform box, float width)
    {
        var go = new GameObject("DR_MaskOutline");
        go.transform.SetParent(box, false);
        var lr = go.AddComponent<LineRenderer>();
        lr.useWorldSpace = false;
        // DR/DebugLine ignores depth, so edges behind the desk scan / on the far side are drawn too.
        var shader = Resources.Load<Shader>("DR_DebugLine");
        if (!shader) shader = Shader.Find("Sprites/Default"); // fallback: hidden edges are not drawn
        lr.material = new Material(shader);
        lr.startWidth = lr.endWidth = width;
        lr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        Vector3 P(float x, float y, float z) => new Vector3(x, y, z) * 0.5f;
        var path = new[]
        {
            P(-1,-1,-1), P(1,-1,-1), P(1,-1,1), P(-1,-1,1), P(-1,-1,-1), // bottom
            P(-1,1,-1), P(1,1,-1), P(1,-1,-1), P(1,1,-1),                // top edges and the vertical edges
            P(1,1,1), P(1,-1,1), P(1,1,1),
            P(-1,1,1), P(-1,-1,1), P(-1,1,1),
            P(-1,1,-1),
        };
        lr.positionCount = path.Length;
        lr.SetPositions(path);
        lr.enabled = false;
        return lr;
    }

    private void Update()
    {
        HandleKeys();
        var track = FindTarget();
        if (track == null) return; // target lost: leave the mask where it was

        if (track.Id != _trackId)
        {
            _trackId = track.Id;
            IsLocked = false;
            if (logDetections)
                Debug.Log($"[{nameof(DRMaskFollowDetection)}] Following '{track.Label}' #{track.Id} at {track.Center:F3}, size {track.Size:F2} via {track.Method}", this);
        }

        // Track box: bottom on the desk, top at the object's top. Add margins around it.
        var size = new Vector3(
            track.Size.x * sizeMargin,
            track.Size.y + extentBelow + extentAbove,
            Mathf.Max(track.Size.z * sizeMargin, minDepth));
        var bottom = track.Center.y - track.Size.y * 0.5f - extentBelow;
        var center = new Vector3(track.Center.x, bottom + size.y * 0.5f, track.Center.z);

        maskBox.SetPositionAndRotation(center, track.Rotation);
        maskBox.localScale = size;
        if (_maskRenderer) _maskRenderer.enabled = true;

        if (track.IsLocked && !IsLocked && logDetections)
            Debug.Log($"[{nameof(DRMaskFollowDetection)}] Mask locked at {center:F3} size {size:F2}", this);
        IsLocked = track.IsLocked;
    }

    /// <summary>The track we already follow, otherwise the confirmed target-label track with the largest footprint.</summary>
    private DetectionTrack FindTarget()
    {
        DetectionTrack best = null;
        var bestArea = -1f;
        foreach (var t in pipeline.Tracks)
        {
            if (!t.IsConfirmed || !t.Label.StartsWith(targetLabel, StringComparison.OrdinalIgnoreCase)) continue;
            if (t.Id == _trackId) return t;

            var area = t.Size.x * t.Size.z;
            if (area > bestArea)
            {
                bestArea = area;
                best = t;
            }
        }
        return best;
    }
}
