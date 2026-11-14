using System.Collections.Generic;
using Meta.XR;
using Meta.XR.BuildingBlocks.AIBlocks;
using UnityEngine;

/// <summary>
/// Diminished Reality: moves a mask box (DR/StencilMask material) onto a real object
/// found by the Object Detection building block, e.g. a keyboard on the desk.
///
/// Flow:
///   ObjectDetectionAgent.OnBoxesUpdated (2D boxes from the passthrough camera)
///   -> filter by label
///   -> 2D box to 3D, in one of two ways:
///        a) Environment depth: ObjectDetectionVisualizer.TryProject (needs the Depth API to be available)
///        b) Fallback: rays from the passthrough camera through the box, hitting colliders in the scene
///           (e.g. a MeshCollider on the aligned desk scan). Works without the Depth API.
///   -> fit the mask box flat on the desk, smooth it, and lock it once it is stable.
///
/// Anything drawn with DR/StencilReadTextured (the desk scan) then shows only inside the box,
/// so the object looks removed.
/// </summary>
public class DRMaskFollowDetection : MonoBehaviour
{
    [Header("Detection (from [BuildingBlock] Object Detection)")]
    [SerializeField] private ObjectDetectionAgent agent;
    [SerializeField] private ObjectDetectionVisualizer visualizer;

    [Tooltip("Passthrough camera used by the detector (found automatically if empty).")]
    [SerializeField] private PassthroughCameraAccess cameraAccess;

    [Tooltip("Class name to hide (see Assets/MetaXR/class_labels.txt).")]
    [SerializeField] private string targetLabel = "keyboard";

    [Header("3D position")]
    [Tooltip("Try environment depth first. If depth is not available, the collider raycast below is used.")]
    [SerializeField] private bool useEnvironmentDepth = true;

    [Tooltip("Layers the fallback ray may hit. Put a MeshCollider on the desk scan (House) so the ray lands on the desk.")]
    [SerializeField] private LayerMask raycastLayers = ~0;

    [Tooltip("Maximum distance of the fallback ray (metres).")]
    [SerializeField] private float maxRayDistance = 5f;

    [Header("Mask")]
    [Tooltip("The box with the DR_StencilMask material (e.g. DR_MaskBox).")]
    [SerializeField] private Transform maskBox;

    [Tooltip("Hide the mask until the target has been found once.")]
    [SerializeField] private bool hideUntilDetected = true;

    [Header("Box size")]
    [Tooltip("Extra size around the detected outline (1.2 = 20% larger).")]
    [SerializeField] private float sizeMargin = 1.2f;

    [Tooltip("Minimum depth (front-to-back) of the box in metres.")]
    [SerializeField] private float minDepth = 0.2f;

    [Tooltip("How far the box goes below the detected surface point (metres). Should reach the desk.")]
    [SerializeField] private float extentBelow = 0.05f;

    [Tooltip("How far the box goes above the detected surface point (metres). Should cover the top of the object.")]
    [SerializeField] private float extentAbove = 0.04f;

    [Header("Stability")]
    [Tooltip("0 = jump straight to each detection, closer to 1 = smoother but slower.")]
    [Range(0f, 0.95f)]
    [SerializeField] private float smoothing = 0.7f;

    [Tooltip("Stop moving the box once this many detections in a row landed close together. 0 = never lock.")]
    [SerializeField] private int lockAfterStableDetections = 5;

    [Tooltip("Detections closer than this (metres) to the current box count as 'the same place'.")]
    [SerializeField] private float stableDistance = 0.03f;

    [Header("Debug")]
    [Tooltip("Write a Debug.Log line when the target is detected (also while the mask is locked).")]
    [SerializeField] private bool logDetections = true;

    [Tooltip("Minimum seconds between detection logs, so the console is not flooded. 0 = log every detection.")]
    [SerializeField] private float logInterval = 0.5f;

    [Tooltip("Also log every label the detector returns (not only the target). Use this to see whether detection runs at all.")]
    [SerializeField] private bool logAllLabels = true;

    [Tooltip("Log a 'still waiting' line this often (seconds) while no detection result has arrived.")]
    [SerializeField] private float noResultWarningInterval = 5f;

    private float _lastLogTime = float.NegativeInfinity;
    private float _lastAllLabelsLogTime = float.NegativeInfinity;
    private float _lastResultTime = float.NegativeInfinity;
    private float _lastNoResultWarningTime;
    private int _batchCount;
    private bool _depthFailureLogged;

    private Renderer _maskRenderer;
    private Collider[] _maskColliders;
    private bool _hasPose;
    private int _stableCount;
    private Vector3 _center;
    private Quaternion _rotation;
    private Vector3 _size;

    /// <summary>True once the box has stopped following detections.</summary>
    public bool IsLocked { get; private set; }

    /// <summary>Result of turning a 2D detection into a footprint on the desk.</summary>
    private struct Footprint
    {
        public Vector3 SurfacePoint; // point on the object's top surface (box centre on screen)
        public Quaternion Yaw;       // rotation around world up only
        public float Width;          // along the box's local X (metres)
        public float Depth;          // along the box's local Z (metres)
        public string Method;
    }

    private void Awake()
    {
        if (!agent) agent = FindFirstObjectByType<ObjectDetectionAgent>();
        if (!visualizer) visualizer = FindFirstObjectByType<ObjectDetectionVisualizer>();
        if (!cameraAccess) cameraAccess = FindFirstObjectByType<PassthroughCameraAccess>();
        if (maskBox)
        {
            _maskRenderer = maskBox.GetComponent<Renderer>();
            _maskColliders = maskBox.GetComponentsInChildren<Collider>(true);
        }

        if (!agent || !maskBox)
        {
            Debug.LogError($"[{nameof(DRMaskFollowDetection)}] agent / maskBox is not set.", this);
            enabled = false;
            return;
        }

        if (!visualizer && !cameraAccess)
        {
            Debug.LogError($"[{nameof(DRMaskFollowDetection)}] Need either an ObjectDetectionVisualizer (depth) or a PassthroughCameraAccess (raycast fallback).", this);
            enabled = false;
            return;
        }

        if (hideUntilDetected && _maskRenderer) _maskRenderer.enabled = false;

        Debug.Log($"[{nameof(DRMaskFollowDetection)}] Ready. agent='{agent.name}' visualizer='{(visualizer ? visualizer.name : "none")}' " +
                  $"camera='{(cameraAccess ? cameraAccess.name : "none")}' mask='{maskBox.name}' target='{targetLabel}'", this);
    }

    private void Update()
    {
        // Warn regularly while the detector has not delivered any result yet.
        if (noResultWarningInterval <= 0f) return;
        var sinceResult = Time.time - _lastResultTime;
        if (sinceResult > noResultWarningInterval && Time.time - _lastNoResultWarningTime > noResultWarningInterval)
        {
            _lastNoResultWarningTime = Time.time;
            Debug.LogWarning(_batchCount == 0
                ? $"[{nameof(DRMaskFollowDetection)}] No detection result yet. Is the passthrough camera running and is camera permission granted? (agent enabled={agent.isActiveAndEnabled})"
                : $"[{nameof(DRMaskFollowDetection)}] No detection result for {sinceResult:0}s (received {_batchCount} batches so far). Nothing is being detected right now.", this);
        }
    }

    private void OnEnable()
    {
        if (agent) agent.OnBoxesUpdated += OnBoxesUpdated;
    }

    private void OnDisable()
    {
        if (agent) agent.OnBoxesUpdated -= OnBoxesUpdated;
    }

    /// <summary>Unlock and follow detections again (e.g. after the object was moved).</summary>
    public void ResetMask()
    {
        IsLocked = false;
        _hasPose = false;
        _stableCount = 0;
        if (hideUntilDetected && _maskRenderer) _maskRenderer.enabled = false;
    }

    private void OnBoxesUpdated(List<BoxData> boxes)
    {
        // This runs inside the agent's async task, which swallows exceptions silently,
        // so catch and log everything here.
        try
        {
            HandleBoxes(boxes);
        }
        catch (System.Exception e)
        {
            Debug.LogError($"[{nameof(DRMaskFollowDetection)}] {e}", this);
        }
    }

    private void HandleBoxes(List<BoxData> boxes)
    {
        if (boxes == null) return;

        _batchCount++;
        _lastResultTime = Time.time;

        if (logAllLabels && Time.time - _lastAllLabelsLogTime >= logInterval)
        {
            _lastAllLabelsLogTime = Time.time;
            var labels = new List<string>(boxes.Count);
            foreach (var b in boxes) labels.Add(b.label);
            Debug.Log($"[{nameof(DRMaskFollowDetection)}] Batch #{_batchCount}: {boxes.Count} objects [{string.Join(", ", labels)}]", this);
        }

        // Pick the detection of the target class with the largest box on screen.
        var found = false;
        var bestArea = -1f;
        var best = default(BoxData);
        foreach (var b in boxes)
        {
            // Labels look like "keyboard 0.82".
            if (string.IsNullOrEmpty(b.label) ||
                !b.label.StartsWith(targetLabel, System.StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            // In the agent's output, position.xy = (xmin, ymin) and scale.xy = (xmax, ymax) in camera pixels.
            var area = Mathf.Abs((b.scale.x - b.position.x) * (b.scale.y - b.position.y));
            if (area > bestArea)
            {
                bestArea = area;
                best = b;
                found = true;
            }
        }

        if (!found) return;

        var located = TryLocate(best, out var footprint, out var failReason);
        LogDetection(best, located, footprint, failReason);

        if (!located || IsLocked) return;

        FitBox(footprint);
    }

    // ---------------------------------------------------------------- 2D -> 3D

    private bool TryLocate(BoxData box, out Footprint footprint, out string failReason)
    {
        footprint = default;
        failReason = null;

        if (useEnvironmentDepth && visualizer && TryLocateWithDepth(box, out footprint))
        {
            return true;
        }

        if (cameraAccess && TryLocateWithRaycast(box, out footprint, out failReason))
        {
            return true;
        }

        if (failReason == null) failReason = cameraAccess ? "raycast failed" : "no PassthroughCameraAccess for the raycast fallback";
        return false;
    }

    private bool TryLocateWithDepth(BoxData box, out Footprint footprint)
    {
        footprint = default;
        bool ok;
        Vector3 hitPoint, faceScale;
        Quaternion faceRotation;
        try
        {
            // Throws (NullReferenceException) while no depth frame has arrived, e.g. when the Depth API
            // is not available (missing Unity OpenXR: Meta package, or not supported over Link).
            ok = visualizer.TryProject(box.position.x, box.position.y, box.scale.x, box.scale.y,
                out hitPoint, out faceRotation, out faceScale);
        }
        catch (System.Exception)
        {
            ok = false;
            hitPoint = default;
            faceScale = default;
            faceRotation = default;
        }

        if (!ok)
        {
            if (!_depthFailureLogged)
            {
                _depthFailureLogged = true;
                Debug.LogWarning($"[{nameof(DRMaskFollowDetection)}] Environment depth is not available, using the collider raycast instead.", this);
            }
            return false;
        }

        // TryProject returns a camera-facing quad; keep only its yaw because the object lies flat on the desk.
        footprint = new Footprint
        {
            SurfacePoint = hitPoint,
            Yaw = YawOnly(faceRotation * Vector3.forward),
            Width = faceScale.x,
            Depth = faceScale.y, // camera-facing height; minDepth makes up for the viewing angle
            Method = "depth",
        };
        return true;
    }

    private bool TryLocateWithRaycast(BoxData box, out Footprint footprint, out string failReason)
    {
        footprint = default;
        failReason = null;

        if (!cameraAccess.IsPlaying)
        {
            failReason = "passthrough camera is not playing";
            return false;
        }

        var tex = cameraAccess.GetTexture();
        if (!tex)
        {
            failReason = "no camera texture";
            return false;
        }

        // Pixel box -> viewport (0..1, origin bottom-left), same convention as ObjectDetectionVisualizer.
        float w = tex.width, h = tex.height;
        var xMin = Mathf.Min(box.position.x, box.scale.x) / w;
        var xMax = Mathf.Max(box.position.x, box.scale.x) / w;
        var yTop = Mathf.Min(box.position.y, box.scale.y) / h;
        var yBottom = Mathf.Max(box.position.y, box.scale.y) / h;
        var cx = (xMin + xMax) * 0.5f;
        var cy = (yTop + yBottom) * 0.5f;

        var pose = cameraAccess.GetCameraPose();
        var centerRay = cameraAccess.ViewportPointToRay(new Vector2(cx, 1f - cy), pose);
        if (!RaycastIgnoringMask(centerRay, out var hit))
        {
            failReason = "center ray hit no collider (add a MeshCollider to the desk scan)";
            return false;
        }

        // Project the four edge midpoints onto the surface plane at the hit point
        // to get the real footprint size on the desk.
        var plane = new Plane(hit.normal, hit.point);
        if (!PlanePoint(plane, cameraAccess.ViewportPointToRay(new Vector2(xMin, 1f - cy), pose), out var left) ||
            !PlanePoint(plane, cameraAccess.ViewportPointToRay(new Vector2(xMax, 1f - cy), pose), out var right) ||
            !PlanePoint(plane, cameraAccess.ViewportPointToRay(new Vector2(cx, 1f - yTop), pose), out var far) ||
            !PlanePoint(plane, cameraAccess.ViewportPointToRay(new Vector2(cx, 1f - yBottom), pose), out var near))
        {
            failReason = "box edges do not hit the surface plane";
            return false;
        }

        // Box X axis follows the screen's left-right direction, flattened onto the floor plane.
        var rightDir = right - left;
        rightDir.y = 0f;
        var forward = rightDir.sqrMagnitude > 1e-6f
            ? Vector3.Cross(rightDir.normalized, Vector3.up)
            : pose.rotation * Vector3.forward;

        footprint = new Footprint
        {
            SurfacePoint = hit.point,
            Yaw = YawOnly(forward),
            Width = Vector3.Distance(left, right),
            Depth = Vector3.Distance(near, far),
            Method = $"raycast on '{hit.collider.name}'",
        };
        return true;
    }

    private bool RaycastIgnoringMask(Ray ray, out RaycastHit result)
    {
        result = default;
        var hits = Physics.RaycastAll(ray, maxRayDistance, raycastLayers, QueryTriggerInteraction.Ignore);
        var bestDistance = float.PositiveInfinity;
        var found = false;
        foreach (var hit in hits)
        {
            if (IsMaskCollider(hit.collider) || hit.distance >= bestDistance) continue;
            bestDistance = hit.distance;
            result = hit;
            found = true;
        }
        return found;
    }

    private bool IsMaskCollider(Collider c)
    {
        if (_maskColliders == null) return false;
        foreach (var m in _maskColliders)
        {
            if (m == c) return true;
        }
        return false;
    }

    private static bool PlanePoint(Plane plane, Ray ray, out Vector3 point)
    {
        if (plane.Raycast(ray, out var distance) && distance > 0f)
        {
            point = ray.GetPoint(distance);
            return true;
        }
        point = default;
        return false;
    }

    private static Quaternion YawOnly(Vector3 forward)
    {
        forward.y = 0f;
        if (forward.sqrMagnitude < 1e-6f) forward = Vector3.forward;
        return Quaternion.LookRotation(forward.normalized, Vector3.up);
    }

    // ---------------------------------------------------------------- mask placement

    private void FitBox(Footprint fp)
    {
        var targetSize = new Vector3(
            fp.Width * sizeMargin,
            extentBelow + extentAbove,
            Mathf.Max(fp.Depth * sizeMargin, minDepth));

        // Box spans from (surface - extentBelow) to (surface + extentAbove) vertically.
        var targetCenter = fp.SurfacePoint + Vector3.up * ((extentAbove - extentBelow) * 0.5f);

        if (!_hasPose)
        {
            _center = targetCenter;
            _rotation = fp.Yaw;
            _size = targetSize;
            _hasPose = true;
            _stableCount = 0;
        }
        else
        {
            _stableCount = Vector3.Distance(_center, targetCenter) < stableDistance ? _stableCount + 1 : 0;

            var t = 1f - smoothing;
            _center = Vector3.Lerp(_center, targetCenter, t);
            _rotation = Quaternion.Slerp(_rotation, fp.Yaw, t);
            _size = Vector3.Lerp(_size, targetSize, t);
        }

        maskBox.SetPositionAndRotation(_center, _rotation);
        maskBox.localScale = _size;
        if (_maskRenderer) _maskRenderer.enabled = true;

        if (logDetections)
        {
            Debug.Log($"[{nameof(DRMaskFollowDetection)}] Mask moved to {_center:F3}, size {_size:F2} via {fp.Method} (stable {_stableCount}/{lockAfterStableDetections})", this);
        }

        if (lockAfterStableDetections > 0 && _stableCount >= lockAfterStableDetections)
        {
            IsLocked = true;
            Debug.Log($"[{nameof(DRMaskFollowDetection)}] Mask locked at {_center} size {_size}", this);
        }
    }

    // ---------------------------------------------------------------- logging

    private void LogDetection(BoxData box, bool located, Footprint fp, string failReason)
    {
        if (!logDetections || Time.time - _lastLogTime < logInterval) return;
        _lastLogTime = Time.time;

        var rect = $"px ({box.position.x:0},{box.position.y:0})-({box.scale.x:0},{box.scale.y:0})";
        var state = IsLocked ? "locked" : "following";
        if (located)
        {
            Debug.Log($"[{nameof(DRMaskFollowDetection)}] Detected '{box.label}' {rect} -> world {fp.SurfacePoint:F3}, footprint {fp.Width:F2}x{fp.Depth:F2} m via {fp.Method} [{state}]", this);
        }
        else
        {
            Debug.LogWarning($"[{nameof(DRMaskFollowDetection)}] Detected '{box.label}' {rect} -> could not get a 3D position: {failReason} [{state}]", this);
        }
    }
}
