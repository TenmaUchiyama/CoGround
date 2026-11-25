using System.Collections;
using Meta.XR.MRUtilityKit;
using UnityEngine;

/// <summary>
/// VR の中でコントローラを使って Gaussian Splatting のモデル (Target) を動かし、机などの実物に重ねる。
/// 位置・回転・大きさは SplatOffset に、部屋の基準 (MRUK の床のアンカー) から見た値で保存する。
/// 次の起動では、保存した値で Target を置き直す。
///
/// ■ Target
///   スプラット (BaseRendererSplatXR) をそのまま入れず、空の親 (例: Splat Align) を作って、その親を入れる。
///   取り込んだときの向きの直し (上下が逆なら X に 180° など) は子のスプラットのほうに入れておく。
///   Target はシーンの一番上に置く (親の Transform があると位置がずれる)。
///
/// ■ 操作
///   左 Y                       … スプラットを動かすモードの ON / OFF (ON のあいだ EnvironmentBoxPlacer は止まる)
///   ON のとき (右コントローラ)
///     グリップ                  … つかんで動かす (傾きは変わらない。向きは真上まわりだけ)
///       + トリガー              … 傾きも含めて自由に回す
///       + 左グリップ            … 両手の間隔で大きさを変える (右手の位置を中心に)
///     右スティック (つかんでいないとき) … 左右: 真上まわりに回す、上下: 上げる / 下げる (細かい合わせ用)
///     左スティック (つかんでいないとき) … 前後左右に少しずつ動かす (向きは見ている方向)
///     B 長押し                  … 最後に保存した位置に戻す
///     A                         … スキャンのメッシュを部屋のメッシュに自動で重ねる (Aligner があるとき。MeshIcpAligner を参照)
///   グリップを離したとき・スティックを戻したとき・モードを OFF にしたときに自動で保存する (保存できたら短く振動する)。
///
/// ■ 保存先
///   EnvironmentBoxPlacer と同じ (エディタではアセット、実機のアプリでは persistentDataPath/splat_offset.json)。
/// </summary>
public class SplatOffsetPlacer : MonoBehaviour
{
    [SerializeField] SplatOffset offset;
    [Tooltip("動かすもの (スプラットの空の親)")]
    [SerializeField] Transform target;
    [Tooltip("スプラットを動かすモードのあいだ止める (コントローラの操作がぶつかるため)")]
    [SerializeField] EnvironmentBoxPlacer boxPlacer;
    [SerializeField] bool startInSplatMode;
    [Tooltip("右 A で、スキャンのメッシュを部屋のメッシュに自動で重ねる (無ければ使わない)")]
    [SerializeField] MeshIcpAligner aligner;

    [Header("コントローラ")]
    [Tooltip("未設定なら OVRCameraRig の右コントローラのアンカー")]
    [SerializeField] Transform rightController;
    [Tooltip("未設定なら OVRCameraRig の左コントローラのアンカー")]
    [SerializeField] Transform leftController;
    [Tooltip("右スティックで回す速さ [deg/s]")]
    [SerializeField] float turnSpeed = 20f;
    [Tooltip("スティックで動かす速さ [m/s]")]
    [SerializeField] float nudgeSpeed = 0.1f;
    [Tooltip("B をこの秒数押し続けると、保存した位置に戻す")]
    [SerializeField] float revertHold = 0.6f;
    [SerializeField] float minScale = 0.01f;
    [SerializeField] float maxScale = 100f;

    [Header("部屋")]
    [Tooltip("MRUK の部屋が出るのを待つ時間 [s]")]
    [SerializeField] float roomTimeout = 5f;

    [Header("見た目")]
    [SerializeField] float labelSize = 0.025f;

    const OVRInput.Controller Right = OVRInput.Controller.RTouch;
    const OVRInput.Controller Left = OVRInput.Controller.LTouch;
    const float StickDead = 0.2f;

    Transform head;
    TextMesh label;
    bool ready;
    bool splatMode;

    /// <summary>スキャンを動かすモードになっているか (DRHandMask はこのあいだ DR を止めて全体を見せる)</summary>
    public bool IsSplatMode => splatMode;
    public Transform Target => target;
    public MeshIcpAligner Aligner => aligner;

    Vector3 originPosition;
    float originYaw;
    string roomUuid = "";
    bool hasRoomOrigin;     // 今の基準が MRUK の部屋から取れたものか (false なら前回のワールド座標の仮の基準)
    bool savedWithoutRoom;  // 部屋が無いあいだに手で合わせて保存したか

    bool holding;
    bool freeRotate;
    Vector3 grabLocal;       // つかんだときの Target の位置 (コントローラから見た位置)
    Quaternion grabRotation; // つかんだときの Target の回転 (コントローラ / コントローラの真上まわりの向きから見た回転)
    float lastControllerYaw;

    bool scaling;
    float scaleStartDistance;
    float scaleStart;
    Vector3 scaleStartOffset; // 右手から Target までの向き (大きさを変え始めたとき)

    bool nudging;
    float revertTimer;
    bool revertDone;

    IEnumerator Start()
    {
        if (target == null)
        {
            Debug.LogError("[SplatOffsetPlacer] Target が未設定。スプラットの空の親を入れること", this);
            enabled = false;
            yield break;
        }
        if (target.parent != null)
            Debug.LogWarning("[SplatOffsetPlacer] Target に親がある。シーンの一番上に置かないと、保存した位置とずれる", this);
        if (offset == null)
        {
            Debug.LogWarning("[SplatOffsetPlacer] Offset が未設定。今回だけの値を使う (保存されない)", this);
            offset = ScriptableObject.CreateInstance<SplatOffset>();
        }
        offset.LoadDeviceCopy();

        var rig = FindAnyObjectByType<OVRCameraRig>();
        if (rig != null)
        {
            if (rightController == null) rightController = rig.rightControllerAnchor;
            if (leftController == null) leftController = rig.leftControllerAnchor;
            head = rig.centerEyeAnchor;
        }
        if (head == null && Camera.main != null) head = Camera.main.transform;
        if (rightController == null || leftController == null)
        {
            Debug.LogError("[SplatOffsetPlacer] コントローラのアンカーが見つからない。Right / Left Controller を設定すること", this);
            enabled = false;
            yield break;
        }

        // MRUK の部屋が出るのを待つ (位置の基準にする)
        float waited = 0f;
        while (MRUK.Instance != null && !EnvironmentRoom.HasRoom() && waited < roomTimeout)
        {
            waited += Time.unscaledDeltaTime;
            yield return null;
        }
        hasRoomOrigin = EnvironmentRoom.TryGetOrigin(out originPosition, out originYaw, out roomUuid);
        if (!hasRoomOrigin)
        {
            originPosition = offset.originPosition;
            originYaw = offset.originYaw;
            roomUuid = "";
            Debug.LogWarning("[SplatOffsetPlacer] MRUK の部屋がまだ無い。仮に前回の基準で置き、部屋が読み込まれたら置き直す", this);
        }
        else WarnIfOtherRoom();

        if (offset.saved) ApplySaved();

        label = EnvironmentRoom.MakeLabel(transform, labelSize);
        label.gameObject.name = "Splat Offset Label";

        ready = true;
        SetSplatMode(startInSplatMode);
        Debug.Log("[SplatOffsetPlacer] 準備できた (左 Y: スプラットを動かすモード)", this);

        // 部屋の読み込みが待ち時間より遅れたとき・読み込み直されたときに、部屋の基準で置き直す
        if (MRUK.Instance != null) MRUK.Instance.RegisterSceneLoadedCallback(OnSceneLoaded);
    }

    /// <summary>MRUK の部屋が読み込まれたとき: 基準が変わっていたら、スプラットを部屋の基準で置き直す</summary>
    void OnSceneLoaded()
    {
        if (!ready || target == null) return;
        if (!EnvironmentRoom.TryGetOrigin(out var p, out var y, out var uuid)) return;
        if (hasRoomOrigin && uuid == roomUuid && (p - originPosition).sqrMagnitude < 1e-6f && Mathf.Abs(Mathf.DeltaAngle(y, originYaw)) < 0.01f)
            return; // もう同じ基準で置いてある

        originPosition = p;
        originYaw = y;
        roomUuid = uuid;
        hasRoomOrigin = true;
        WarnIfOtherRoom();

        if (savedWithoutRoom)
        {
            // 部屋が無いあいだに手で合わせた位置が正しいので、それを部屋の基準で保存し直す
            Save();
            Debug.Log("[SplatOffsetPlacer] 部屋が読み込まれた。部屋が無いあいだに合わせた位置を、部屋の基準で保存し直した", this);
        }
        else if (offset.saved && !holding)
        {
            ApplySaved();
            Debug.Log("[SplatOffsetPlacer] 部屋が読み込まれたので、保存した位置に置き直した", this);
        }
    }

    void WarnIfOtherRoom()
    {
        if (!string.IsNullOrEmpty(offset.roomUuid) && offset.roomUuid != roomUuid)
            Debug.LogWarning($"[SplatOffsetPlacer] 保存したときと部屋が違う (保存: {offset.roomUuid}、今: {roomUuid})。MRUK の Data Source (実機 / JSON) が前回と違うとずれる。この部屋で合わせ直して保存すること", this);
    }

    void Update()
    {
        if (!ready) return;

        bool grip = OVRInput.Get(OVRInput.Button.PrimaryHandTrigger, Right);

        // モードの切り替えは、つかんでいないときだけ
        if (!holding && OVRInput.GetDown(OVRInput.Button.Two, Left)) SetSplatMode(!splatMode);

        if (splatMode)
        {
            if (!holding)
            {
                if (OVRInput.GetDown(OVRInput.Button.PrimaryHandTrigger, Right)) BeginHold();
                else if (OVRInput.GetDown(OVRInput.Button.One, Right)) AutoAlign();
                else
                {
                    UpdateNudge();
                    UpdateRevert();
                }
            }
            else if (!grip)
            {
                holding = false;
                scaling = false;
                Save();
            }
            else if (OVRInput.Get(OVRInput.Button.PrimaryHandTrigger, Left))
            {
                if (!scaling) BeginScale();
                UpdateScale();
            }
            else
            {
                bool trigger = OVRInput.Get(OVRInput.Button.PrimaryIndexTrigger, Right);
                if (scaling || trigger != freeRotate) BeginHold(); // 両手を離した / トリガーを変えたら、つかみ直す
                UpdateMove();
            }
        }

        UpdateLabel();
    }

    void SetSplatMode(bool on)
    {
        if (splatMode && !on) Save();
        splatMode = on;
        if (boxPlacer != null) boxPlacer.enabled = !on;
        nudging = false;
        Pulse(on ? 0.5f : 0.2f);
    }

    // ---- つかんで動かす ----

    void BeginHold()
    {
        holding = true;
        scaling = false;
        lastAlignReport = ""; // 手で動かしたら、前の自動の結果は古い
        freeRotate = OVRInput.Get(OVRInput.Button.PrimaryIndexTrigger, Right);
        lastControllerYaw = ControllerYaw();
        grabLocal = Quaternion.Inverse(rightController.rotation) * (target.position - rightController.position);
        grabRotation = Quaternion.Inverse(HoldFrame()) * target.rotation;
        Pulse(0.4f);
    }

    void UpdateMove()
    {
        target.SetPositionAndRotation(
            rightController.position + rightController.rotation * grabLocal,
            HoldFrame() * grabRotation);
    }

    /// <summary>つかんでいる向きの基準。自由に回すときはコントローラそのもの、それ以外は真上まわりの向きだけ</summary>
    Quaternion HoldFrame() => freeRotate ? rightController.rotation : Quaternion.Euler(0f, ControllerYaw(), 0f);

    /// <summary>コントローラの向き (真上まわり)。真上・真下を向いているときは、直前の値を返す</summary>
    float ControllerYaw()
    {
        var f = Vector3.ProjectOnPlane(rightController.forward, Vector3.up);
        if (f.sqrMagnitude > 0.01f) lastControllerYaw = Quaternion.LookRotation(f).eulerAngles.y;
        return lastControllerYaw;
    }

    // ---- 大きさを変える ----

    void BeginScale()
    {
        scaling = true;
        scaleStartDistance = Mathf.Max(HandDistance(), 0.01f);
        scaleStart = target.localScale.x;
        scaleStartOffset = target.position - rightController.position;
        Pulse(0.3f);
    }

    void UpdateScale()
    {
        float k = HandDistance() / scaleStartDistance;
        float s = Mathf.Clamp(scaleStart * k, minScale, maxScale);
        k = s / scaleStart;
        target.localScale = Vector3.one * s;
        target.position = rightController.position + scaleStartOffset * k;
    }

    float HandDistance() => Vector3.Distance(rightController.position, leftController.position);

    // ---- スティックで細かく合わせる ----

    void UpdateNudge()
    {
        var r = OVRInput.Get(OVRInput.Axis2D.PrimaryThumbstick, Right);
        var l = OVRInput.Get(OVRInput.Axis2D.PrimaryThumbstick, Left);
        r = new Vector2(Mathf.Abs(r.x) > StickDead ? r.x : 0f, Mathf.Abs(r.y) > StickDead ? r.y : 0f);
        l = new Vector2(Mathf.Abs(l.x) > StickDead ? l.x : 0f, Mathf.Abs(l.y) > StickDead ? l.y : 0f);

        if (r == Vector2.zero && l == Vector2.zero)
        {
            if (nudging)
            {
                nudging = false;
                Save();
            }
            return;
        }
        nudging = true;
        float dt = Time.unscaledDeltaTime;

        // 真上まわりに回す (Target の原点が中心)
        if (r.x != 0f) target.rotation = Quaternion.Euler(0f, r.x * turnSpeed * dt, 0f) * target.rotation;

        // 上下と、見ている方向に合わせた前後左右
        var move = Vector3.up * r.y;
        if (l != Vector2.zero && head != null)
        {
            var fwd = Vector3.ProjectOnPlane(head.forward, Vector3.up).normalized;
            var right = Vector3.Cross(Vector3.up, fwd);
            move += fwd * l.y + right * l.x;
        }
        target.position += move * nudgeSpeed * dt;
    }

    // ---- 自動で重ねる ----

    string lastAlignReport = "";

    /// <summary>スキャンのメッシュを部屋のメッシュに ICP で重ね、うまくいったら保存する</summary>
    [ContextMenu("部屋のメッシュに自動で重ねる")]
    public void AutoAlign()
    {
        if (!ready) return;
        if (aligner == null)
        {
            lastAlignReport = "Aligner が未設定";
            Debug.LogWarning("[SplatOffsetPlacer] Aligner が未設定。自動で重ねられない", this);
            return;
        }
        if (aligner.Align(target, out lastAlignReport))
        {
            Debug.Log($"[SplatOffsetPlacer] 自動で重ねた: {lastAlignReport}", this);
            Save();
        }
        else
        {
            Debug.LogWarning($"[SplatOffsetPlacer] 自動で重ねられなかった: {lastAlignReport}", this);
            Pulse(0.15f);
        }
    }

    // ---- 保存した位置に戻す ----

    void UpdateRevert()
    {
        if (!OVRInput.Get(OVRInput.Button.Two, Right))
        {
            revertTimer = 0f;
            revertDone = false;
            return;
        }
        if (revertDone) return;
        revertTimer += Time.unscaledDeltaTime;
        if (revertTimer < revertHold) return;

        revertDone = true;
        if (offset.saved)
        {
            ApplySaved();
            Pulse(0.6f);
            Debug.Log("[SplatOffsetPlacer] 保存した位置に戻した", this);
        }
    }

    void ApplySaved()
    {
        offset.ToWorld(originPosition, originYaw, out var p, out var q);
        target.SetPositionAndRotation(p, q);
        target.localScale = Vector3.one * offset.scale;
    }

    // ---- 見た目 ----

    void UpdateLabel()
    {
        if (label == null) return;
        label.gameObject.SetActive(splatMode);
        if (!splatMode) return;

        label.transform.position = leftController.position + Vector3.up * 0.08f;
        string text = $"Splat 調整中  x{target.localScale.x:0.000}";
        if (holding) text += scaling ? "\n大きさ" : freeRotate ? "\n自由に回す" : "\n動かす";
        else if (!string.IsNullOrEmpty(lastAlignReport)) text += "\n" + lastAlignReport.Replace("。", "\n");
        if (label.text != text) label.text = text;
        EnvironmentRoom.FaceLabel(label, head);
    }

    // ---- 保存 ----

    /// <summary>今の Target の位置・回転・大きさを Offset に書き込む</summary>
    [ContextMenu("保存する")]
    public void Save()
    {
        if (!ready || target == null) return;

        // 部屋の基準は保存のたびに取り直す (MRUK が部屋の位置を合わせ直すことがあるため)
        if (EnvironmentRoom.TryGetOrigin(out var p, out var y, out var uuid))
        {
            originPosition = p;
            originYaw = y;
            roomUuid = uuid;
            hasRoomOrigin = true;
        }
        savedWithoutRoom = !hasRoomOrigin;
        offset.FromWorld(originPosition, originYaw, target.position, target.rotation);
        offset.scale = target.localScale.x;
        offset.originPosition = originPosition;
        offset.originYaw = originYaw;
        offset.roomUuid = roomUuid;
        offset.saved = true;

        try { offset.Persist(); }
        catch (System.Exception e) { Debug.LogError($"[SplatOffsetPlacer] 保存に失敗: {e.Message}", this); return; }
        Debug.Log($"[SplatOffsetPlacer] スプラットの位置を保存した (部屋から見て {offset.position}, 大きさ x{offset.scale:0.000})", this);
        Pulse(0.6f);
    }

    void Pulse(float amplitude)
    {
        if (isActiveAndEnabled) StartCoroutine(PulseRoutine(amplitude));
    }

    IEnumerator PulseRoutine(float amplitude)
    {
        OVRInput.SetControllerVibration(1f, amplitude, Right);
        yield return new WaitForSecondsRealtime(0.06f);
        OVRInput.SetControllerVibration(0f, 0f, Right);
    }

    void OnDestroy()
    {
        if (label != null) Destroy(label.gameObject);
        if (MRUK.Instance != null) MRUK.Instance.SceneLoadedEvent.RemoveListener(OnSceneLoaded);
    }

#if UNITY_EDITOR
    /// <summary>Play していないとき: 保存してある位置に Target を置く (最後に保存したときの部屋の基準で)</summary>
    [ContextMenu("保存した位置を Target に入れる (Editor)")]
    void ApplySavedInEditor()
    {
        if (Application.isPlaying || offset == null || target == null || !offset.saved) return;
        UnityEditor.Undo.RecordObject(target, "Apply Splat Offset");
        offset.ToWorld(offset.originPosition, offset.originYaw, out var p, out var q);
        target.SetPositionAndRotation(p, q);
        target.localScale = Vector3.one * offset.scale;
    }
#endif
}
