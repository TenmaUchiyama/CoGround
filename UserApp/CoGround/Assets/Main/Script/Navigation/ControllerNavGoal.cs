using System.Collections;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// コントローラから Ray を出し、トリガーで床を指して Navigation の目標を置く。P キーで計画、X キーで実行。
/// 実際の計画・実行は RosBaseNavigator (ROS の move_base) がやる。
///
///   トリガーを押す  … Ray が当たった床に目標を置く (向きはコントローラから見て奥向き)
///   押したまま動かす … 押した点から Ray の先への向きを目標の向きにする
///   P キー          … Plan (計画を頼む。経路とゴーストが出る)
///   X キー          … Execute (計画した経路で動かす)
///
/// Ray は物理コライダーに当て、上向きの面 (床・MRUK の FLOOR の箱など) に当たったときだけ目標にする。
/// 机の天板など床より高い面も上向きなので、maxFloorHeight より高い面は目標にしない。
/// </summary>
public class ControllerNavGoal : MonoBehaviour
{
    public enum Hand { Left, Right }

    [Header("ナビゲーション")]
    [Tooltip("未設定ならシーンから探す。無効になっていたら有効にする")]
    [SerializeField] RosBaseNavigator navigator;
    [Tooltip("目標を置いただけでは計画しない (P キーで計画する)")]
    [SerializeField] bool planOnlyByKey = true;

    [Header("コントローラ")]
    [Tooltip("Ray を出す手。右トリガーは PushToTalk (音声入力) が使っているので、既定は左")]
    [SerializeField] Hand hand = Hand.Left;
    [Tooltip("未設定なら OVRCameraRig の手のアンカーを使う")]
    [SerializeField] Transform rayOrigin;
    [SerializeField] float maxDistance = 10f;
    [SerializeField] LayerMask rayMask = ~0;
    [Tooltip("床とみなす面の傾きの限度 (法線と真上の角度) [deg]")]
    [SerializeField] float maxSlope = 20f;
    [Tooltip("ロボットの床 (台車の底) からこの高さより上の面は目標にしない [m]")]
    [SerializeField] float maxFloorHeight = 0.15f;
    [Tooltip("押したまま、これ以上 Ray の先を動かしたら向きを決める [m]")]
    [SerializeField] float dragForHeading = 0.15f;

    [Header("キー")]
    [SerializeField] bool allowKeyboard = true;

    [Header("見た目")]
    [SerializeField] float rayWidth = 0.004f;
    [SerializeField] Color validColor = new Color(0.2f, 1f, 0.4f, 0.9f);
    [SerializeField] Color invalidColor = new Color(1f, 0.3f, 0.3f, 0.6f);
    [SerializeField] bool haptics = true;

    LineRenderer ray;
    bool dragging;
    Vector3 dragStart;
    float dragYaw;
    string lastStatus;

    OVRInput.Controller Controller => hand == Hand.Left ? OVRInput.Controller.LTouch : OVRInput.Controller.RTouch;

    void Start()
    {
        if (navigator == null) navigator = FindAnyObjectByType<RosBaseNavigator>();
        if (navigator == null)
        {
            Debug.LogError("[ControllerNavGoal] RosBaseNavigator がシーンにない");
            enabled = false;
            return;
        }
        if (!navigator.enabled)
        {
            Debug.LogWarning("[ControllerNavGoal] RosBaseNavigator が無効だったので有効にした");
            navigator.enabled = true;
        }
        if (planOnlyByKey) navigator.PlanWhenGoalStops = false;

        if (rayOrigin == null)
        {
            var rig = FindAnyObjectByType<OVRCameraRig>();
            if (rig != null) rayOrigin = hand == Hand.Left ? rig.leftControllerAnchor : rig.rightControllerAnchor;
        }
        if (rayOrigin == null) Debug.LogWarning("[ControllerNavGoal] コントローラのアンカーが見つからない。Ray Origin を設定すること");

        ray = new GameObject("Nav Goal Ray").AddComponent<LineRenderer>();
        ray.useWorldSpace = true;
        ray.positionCount = 2;
        ray.widthMultiplier = rayWidth;
        ray.sharedMaterial = FetchGhost.MakeMaterial(validColor);
        ray.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        ray.receiveShadows = false;
    }

    void Update()
    {
        UpdateRay();

        if (allowKeyboard && KeyDown(KeyP)) navigator.Plan();
        if (allowKeyboard && KeyDown(KeyX)) navigator.Execute();

        // ヘッドセットの中では OnGUI のパネルが見えないので、状態が変わったら Console に出す
        if (navigator.Status != lastStatus)
        {
            lastStatus = navigator.Status;
            Debug.Log($"[ControllerNavGoal] {lastStatus}");
        }
    }

    void UpdateRay()
    {
        if (rayOrigin == null) return;
        var origin = rayOrigin.position;
        var dir = rayOrigin.forward;
        bool hit = Physics.Raycast(origin, dir, out var info, maxDistance, rayMask, QueryTriggerInteraction.Ignore);
        bool valid = hit && IsFloor(info);

        var end = hit ? info.point : origin + dir * maxDistance;
        ray.SetPosition(0, origin);
        ray.SetPosition(1, end);
        ray.startColor = ray.endColor = valid ? validColor : invalidColor;

        bool down = OVRInput.GetDown(OVRInput.Button.PrimaryIndexTrigger, Controller);
        bool held = OVRInput.Get(OVRInput.Button.PrimaryIndexTrigger, Controller);

        if (down && valid)
        {
            dragging = true;
            dragStart = info.point;
            var away = Vector3.ProjectOnPlane(info.point - origin, Vector3.up); // 既定の向き: コントローラから見て奥
            dragYaw = away.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(away).eulerAngles.y : 0f;
            navigator.SetGoal(dragStart, dragYaw);
            Pulse(0.6f);
        }
        else if (dragging && held)
        {
            if (hit)
            {
                var d = Vector3.ProjectOnPlane(info.point - dragStart, Vector3.up);
                if (d.magnitude > dragForHeading)
                {
                    dragYaw = Quaternion.LookRotation(d).eulerAngles.y;
                    navigator.SetGoal(dragStart, dragYaw);
                }
            }
        }
        else if (dragging && !held)
        {
            dragging = false;
            Debug.Log($"[ControllerNavGoal] 目標を置いた: 位置 {dragStart:F2}, 向き {dragYaw:F0} deg (P で計画、X で実行)");
            Pulse(0.3f);
        }
    }

    bool IsFloor(RaycastHit info)
    {
        if (Vector3.Angle(info.normal, Vector3.up) > maxSlope) return false;
        // ロボット自身や机の天板は目標にしない
        if (navigator != null && info.collider.transform.IsChildOf(navigator.transform)) return false;
        float floorY = FetchRobotState.Instance.TryGetBasePose(out var basePos, out _) ? basePos.y : 0f;
        return info.point.y - floorY <= maxFloorHeight;
    }

    void Pulse(float amplitude)
    {
        if (haptics) StartCoroutine(PulseRoutine(amplitude));
    }

    IEnumerator PulseRoutine(float amplitude)
    {
        OVRInput.SetControllerVibration(1f, amplitude, Controller);
        yield return new WaitForSecondsRealtime(0.06f);
        OVRInput.SetControllerVibration(0f, 0f, Controller);
    }

    void OnDestroy()
    {
        if (ray != null) Destroy(ray.gameObject);
    }

    const char KeyP = 'p', KeyX = 'x';

    static bool KeyDown(char key)
    {
#if ENABLE_INPUT_SYSTEM
        var k = Keyboard.current;
        if (k == null) return false;
        return key == KeyP ? k.pKey.wasPressedThisFrame : k.xKey.wasPressedThisFrame;
#else
        return Input.GetKeyDown(key == KeyP ? KeyCode.P : KeyCode.X);
#endif
    }
}
