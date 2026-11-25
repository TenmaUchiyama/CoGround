using System.Collections;
using System.Collections.Generic;
using Meta.XR.MRUtilityKit;
using UnityEngine;

/// <summary>
/// VR の中でコントローラを使って箱 (置き場所の候補) を置き、EnvironmentBoxLayout に保存する。
/// 名前は Editor で、保存先のアセット (Layout) の Boxes に入れる。
///
/// ■ 操作 (右コントローラ)
///   A                      … 新しい箱をコントローラの少し先に出す
///   箱に Ray を当ててグリップ … つかんで動かす (箱は倒れない。向きは真上まわりだけ変わる)
///     + 右スティック上下    … 箱を遠ざける / 近づける
///     + 左グリップ          … 大きさを変える (両手の間隔を、箱の左右・高さ・前後の向きに広げた分だけ大きくなる。底は動かない)
///   箱に Ray を当てて B を長押し … その箱を消す
///   グリップを離したとき・箱を出したとき・消したときに自動で保存する (保存できたら短く振動する)。
///
/// ■ 保存先
///   エディタ (Link で Play): Layout のアセットに書き込む。Play を止めても残る。
///   実機のアプリ          : Application.persistentDataPath/environment_boxes.json に書き、次の起動で読む
///                          (実機からエディタへ持ってくる仕組みは無い)。
///
/// ■ 位置の基準
///   MRUK の部屋の床のアンカーから見た位置で保存する (EnvironmentBoxLayout の説明を参照)。
///   Room Timeout 秒待っても部屋が出なければ、前に保存したときの基準 (無ければワールドの原点) を使う。
/// </summary>
public class EnvironmentBoxPlacer : MonoBehaviour
{
    [SerializeField] EnvironmentBoxLayout layout;

    [Header("コントローラ")]
    [Tooltip("未設定なら OVRCameraRig の右コントローラのアンカー")]
    [SerializeField] Transform rightController;
    [Tooltip("未設定なら OVRCameraRig の左コントローラのアンカー")]
    [SerializeField] Transform leftController;
    [SerializeField] float maxDistance = 10f;
    [Tooltip("スティックで遠ざける / 近づける速さ (1 秒あたりの倍率)")]
    [SerializeField] float pushSpeed = 1.5f;
    [Tooltip("B をこの秒数押し続けると消す")]
    [SerializeField] float deleteHold = 0.6f;

    [Header("箱")]
    [SerializeField] Vector3 newBoxSize = new Vector3(0.3f, 0.3f, 0.3f);
    [Tooltip("新しい箱を出す位置 (コントローラの先) [m]")]
    [SerializeField] float newBoxDistance = 0.5f;
    [SerializeField] float minSize = 0.03f;

    [Header("部屋")]
    [Tooltip("MRUK の部屋が出るのを待つ時間 [s]")]
    [SerializeField] float roomTimeout = 5f;

    [Header("見た目")]
    [SerializeField] Color boxColor = new Color(0.2f, 0.6f, 1f, 0.3f);
    [SerializeField] Color hoverColor = new Color(1f, 0.85f, 0.1f, 0.4f);
    [SerializeField] Color heldColor = new Color(0.2f, 1f, 0.4f, 0.45f);
    [SerializeField] float rayWidth = 0.004f;
    [SerializeField] float labelSize = 0.05f;

    class Live
    {
        public EnvironmentBoxLayout.Box data;
        public Transform root;   // 箱の中心。向きは真上まわりだけ
        public Transform cube;   // 見た目 (スケール = 大きさ)
        public Material material;
        public TextMesh label;
    }

    readonly List<Live> boxes = new List<Live>();
    LineRenderer ray;
    Material rayMaterial;
    Transform head;
    bool ready;

    Vector3 originPosition;
    float originYaw;
    string roomUuid = "";
    bool hasRoomOrigin;      // 今の基準が MRUK の部屋から取れたものか (false なら前回保存したときの仮の基準)

    Live held;
    Vector3 grabLocal;       // つかんだときの箱の中心 (コントローラから見た位置)
    float grabYaw;           // つかんだときの箱の向き - コントローラの向き
    float lastControllerYaw;

    bool stretching;
    Vector3 stretchHands;    // 大きさを変え始めたときの両手の間隔 (箱の向きで見た絶対値)
    Vector3 stretchSize;
    Vector3 stretchPosition;

    float deleteTimer;
    bool deleteDone;

    const OVRInput.Controller Right = OVRInput.Controller.RTouch;
    const OVRInput.Controller Left = OVRInput.Controller.LTouch;

    IEnumerator Start()
    {
        if (layout == null)
        {
            Debug.LogWarning("[EnvironmentBoxPlacer] Layout が未設定。今回だけの一覧を使う (保存されない)", this);
            layout = ScriptableObject.CreateInstance<EnvironmentBoxLayout>();
        }
        layout.LoadDeviceCopy();

        var rig = FindAnyObjectByType<OVRCameraRig>();
        if (rig != null)
        {
            if (rightController == null) rightController = rig.rightControllerAnchor;
            if (leftController == null) leftController = rig.leftControllerAnchor;
            head = rig.centerEyeAnchor;
        }
        if (head == null && Camera.main != null) head = Camera.main.transform;
        if (rightController == null)
        {
            Debug.LogError("[EnvironmentBoxPlacer] 右コントローラのアンカーが見つからない。Right Controller を設定すること", this);
            enabled = false;
            yield break;
        }

        // MRUK の部屋が出るのを待つ (箱の位置の基準にする)
        float waited = 0f;
        while (MRUK.Instance != null && !EnvironmentRoom.HasRoom() && waited < roomTimeout)
        {
            waited += Time.unscaledDeltaTime;
            yield return null;
        }
        hasRoomOrigin = EnvironmentRoom.TryGetOrigin(out originPosition, out originYaw, out roomUuid, layout.roomUuid);
        if (!hasRoomOrigin)
        {
            originPosition = layout.originPosition;
            originYaw = layout.originYaw;
            roomUuid = "";
            Debug.LogWarning("[EnvironmentBoxPlacer] MRUK の部屋がまだ無い。仮に前に保存したときの基準で箱を置き、部屋が読み込まれたら置き直す", this);
        }
        else if (!string.IsNullOrEmpty(layout.roomUuid) && layout.roomUuid != roomUuid)
        {
            Debug.LogWarning($"[EnvironmentBoxPlacer] 保存したときと部屋が違う (保存: {layout.roomUuid}、今: {roomUuid})。箱の位置がずれているかもしれない", this);
        }

        foreach (var data in layout.boxes) Spawn(data);

        ray = new GameObject("Box Placer Ray").AddComponent<LineRenderer>();
        ray.useWorldSpace = true;
        ray.positionCount = 2;
        ray.widthMultiplier = rayWidth;
        rayMaterial = FetchGhost.MakeMaterial(boxColor);
        ray.sharedMaterial = rayMaterial;
        ray.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        ray.receiveShadows = false;

        ready = true;
        Debug.Log($"[EnvironmentBoxPlacer] 箱 {boxes.Count} 個を読み込んだ (A: 新しい箱、グリップ: 動かす、+左グリップ: 大きさ、B 長押し: 消す)", this);
    }

    void Update()
    {
        if (!ready) return;

        FollowRoom();

        Vector3 origin = rightController.position;
        Vector3 dir = rightController.forward;
        float hitDistance = maxDistance;
        Live hover = held ?? Pick(origin, dir, out hitDistance);

        bool grip = OVRInput.Get(OVRInput.Button.PrimaryHandTrigger, Right);
        bool leftGrip = leftController != null && OVRInput.Get(OVRInput.Button.PrimaryHandTrigger, Left);

        if (held == null)
        {
            if (OVRInput.GetDown(OVRInput.Button.One, Right)) hover = Create();
            else if (hover != null && OVRInput.GetDown(OVRInput.Button.PrimaryHandTrigger, Right)) BeginHold(hover);
            UpdateDelete(ref hover);
        }
        else if (!grip)
        {
            held = null;
            stretching = false;
            Save();
        }
        else if (leftGrip)
        {
            if (!stretching) BeginStretch();
            UpdateStretch();
        }
        else
        {
            if (stretching)
            {
                stretching = false;
                BeginHold(held); // 大きさを変えている間に動いた手に合わせて、つかみ直す
            }
            UpdateMove();
        }

        UpdateVisuals(hover, origin, dir, hitDistance);
    }

    // ---- 部屋についていく ----

    /// <summary>
    /// 部屋の基準が変わったら (部屋が後から読み込まれた・MRUK が部屋の位置を合わせ直した)、
    /// 箱を部屋と一緒に動かす。つかんでいる箱はコントローラについていくので動かさない。
    /// </summary>
    void FollowRoom()
    {
        // 一度決めた部屋を使い続ける (今いる部屋で選ぶと、歩いて部屋をまたいだときに全部の箱が飛ぶ)
        if (!EnvironmentRoom.TryGetOrigin(out var p, out var y, out var uuid, hasRoomOrigin ? roomUuid : layout.roomUuid)) return;
        if (hasRoomOrigin && uuid != roomUuid) return; // 基準の部屋が見つからなくなった: 箱は動かさない
        if (hasRoomOrigin && !EnvironmentRoom.OriginMoved(originPosition, originYaw, p, y)) return;

        if (!hasRoomOrigin)
        {
            Debug.Log("[EnvironmentBoxPlacer] MRUK の部屋が読み込まれたので、箱を部屋の基準で置き直した", this);
            if (!string.IsNullOrEmpty(layout.roomUuid) && layout.roomUuid != uuid)
                Debug.LogWarning($"[EnvironmentBoxPlacer] 保存したときと部屋が違う (保存: {layout.roomUuid}、今: {uuid})。箱の位置がずれているかもしれない", this);
        }

        foreach (var box in boxes)
        {
            if (box == held) continue;
            EnvironmentBoxLayout.ToLocal(originPosition, originYaw, box.root.position, box.root.eulerAngles.y, out var local, out var yaw);
            EnvironmentBoxLayout.ToWorld(p, y, local, yaw, out var position, out var rotation);
            box.root.SetPositionAndRotation(position, rotation);
        }
        originPosition = p;
        originYaw = y;
        roomUuid = uuid;
        hasRoomOrigin = true;
    }

    // ---- つかんで動かす ----

    void BeginHold(Live box)
    {
        held = box;
        lastControllerYaw = ControllerYaw();
        grabLocal = Quaternion.Inverse(rightController.rotation) * (box.root.position - rightController.position);
        grabYaw = box.root.eulerAngles.y - lastControllerYaw;
        Pulse(0.4f);
    }

    void UpdateMove()
    {
        float stick = OVRInput.Get(OVRInput.Axis2D.PrimaryThumbstick, Right).y;
        if (Mathf.Abs(stick) > 0.2f) grabLocal *= 1f + stick * pushSpeed * Time.unscaledDeltaTime;

        held.root.SetPositionAndRotation(
            rightController.position + rightController.rotation * grabLocal,
            Quaternion.Euler(0f, ControllerYaw() + grabYaw, 0f));
    }

    /// <summary>コントローラの向き (真上まわり)。真上・真下を向いているときは、直前の値を返す</summary>
    float ControllerYaw()
    {
        var f = Vector3.ProjectOnPlane(rightController.forward, Vector3.up);
        if (f.sqrMagnitude > 0.01f) lastControllerYaw = Quaternion.LookRotation(f).eulerAngles.y;
        return lastControllerYaw;
    }

    // ---- 大きさを変える ----

    void BeginStretch()
    {
        stretching = true;
        stretchHands = HandsInBoxAxes();
        stretchSize = held.data.size;
        stretchPosition = held.root.position;
        Pulse(0.3f);
    }

    void UpdateStretch()
    {
        var size = stretchSize + (HandsInBoxAxes() - stretchHands);
        size = Vector3.Max(size, Vector3.one * minSize);
        held.data.size = size;
        // 底の高さを変えない
        held.root.position = stretchPosition + Vector3.up * ((size.y - stretchSize.y) / 2f);
        ApplySize(held);
    }

    /// <summary>両手の間隔を、箱の左右・高さ・前後の向きに分けた大きさ</summary>
    Vector3 HandsInBoxAxes()
    {
        var d = Quaternion.Inverse(held.root.rotation) * (rightController.position - leftController.position);
        return new Vector3(Mathf.Abs(d.x), Mathf.Abs(d.y), Mathf.Abs(d.z));
    }

    // ---- 足す・消す ----

    /// <summary>新しい箱を右コントローラの先に出す</summary>
    [ContextMenu("箱を足す")]
    public void CreateBox() { if (ready) Create(); }

    Live Create()
    {
        var position = rightController.position + rightController.forward * newBoxDistance;
        EnvironmentBoxLayout.ToLocal(originPosition, originYaw, position, ControllerYaw(), out var local, out var yaw);
        var data = new EnvironmentBoxLayout.Box { position = local, yaw = yaw, size = newBoxSize };
        layout.boxes.Add(data);
        var box = Spawn(data);
        Save();
        return box;
    }

    void UpdateDelete(ref Live hover)
    {
        if (!OVRInput.Get(OVRInput.Button.Two, Right))
        {
            deleteTimer = 0f;
            deleteDone = false;
            return;
        }
        if (hover == null || deleteDone) return;
        deleteTimer += Time.unscaledDeltaTime;
        if (deleteTimer < deleteHold) return;

        deleteDone = true; // B を離すまで、次の箱は消さない
        layout.boxes.Remove(hover.data);
        boxes.Remove(hover);
        Destroy(hover.material);
        Destroy(hover.root.gameObject);
        hover = null;
        Save();
    }

    Live Spawn(EnvironmentBoxLayout.Box data)
    {
        EnvironmentBoxLayout.ToWorld(originPosition, originYaw, data.position, data.yaw, out var position, out var rotation);

        var root = new GameObject("Environment Box").transform;
        root.SetParent(transform, false);
        root.SetPositionAndRotation(position, rotation);

        var material = FetchGhost.MakeMaterial(boxColor);
        var cube = EnvironmentRoom.MakeCube("visual", root, material); // Ray は自前で当てるので、当たり判定は無い
        var label = EnvironmentRoom.MakeLabel(root, labelSize);

        var box = new Live { data = data, root = root, cube = cube, material = material, label = label };
        boxes.Add(box);
        ApplySize(box);
        return box;
    }

    void ApplySize(Live box)
    {
        box.cube.localScale = box.data.size;
        box.label.transform.localPosition = Vector3.up * (box.data.size.y / 2f + 0.02f);
    }

    // ---- Ray を箱に当てる ----

    /// <summary>Ray が最初に当たる箱 (無ければ null)。Ray の始点が箱の中なら、その箱</summary>
    Live Pick(Vector3 origin, Vector3 dir, out float distance)
    {
        Live best = null;
        distance = maxDistance;
        foreach (var box in boxes)
        {
            var inv = Quaternion.Inverse(box.root.rotation);
            if (RayBox(inv * (origin - box.root.position), inv * dir, box.data.size / 2f, out float t) && t < distance)
            {
                distance = t;
                best = box;
            }
        }
        return best;
    }

    /// <summary>箱 (中心が原点、軸に沿う) と Ray の交差。t は入る点までの距離 (始点が中なら 0)</summary>
    static bool RayBox(Vector3 origin, Vector3 dir, Vector3 half, out float t)
    {
        float near = 0f, far = float.PositiveInfinity;
        t = 0f;
        for (int i = 0; i < 3; i++)
        {
            if (Mathf.Abs(dir[i]) < 1e-6f)
            {
                if (Mathf.Abs(origin[i]) > half[i]) return false;
                continue;
            }
            float a = (-half[i] - origin[i]) / dir[i];
            float b = (half[i] - origin[i]) / dir[i];
            if (a > b) (a, b) = (b, a);
            near = Mathf.Max(near, a);
            far = Mathf.Min(far, b);
            if (near > far) return false;
        }
        t = near;
        return true;
    }

    // ---- 見た目 ----

    void UpdateVisuals(Live hover, Vector3 origin, Vector3 dir, float hitDistance)
    {
        for (int i = 0; i < boxes.Count; i++)
        {
            var box = boxes[i];
            box.material.color = box == held ? heldColor : box == hover ? hoverColor : boxColor;

            string text = layout.LabelOf(i);
            if (box == held) text += $"\n{box.data.size.x:0.00} x {box.data.size.y:0.00} x {box.data.size.z:0.00} m";
            if (box.label.text != text) box.label.text = text;
            EnvironmentRoom.FaceLabel(box.label, head);
        }

        if (held != null) hitDistance = Vector3.Distance(origin, held.root.position);
        ray.SetPosition(0, origin);
        ray.SetPosition(1, origin + dir * hitDistance);
        rayMaterial.color = held != null ? heldColor : hover != null ? hoverColor : boxColor;
    }

    // ---- 保存 ----

    /// <summary>今の箱の位置・向き・大きさを Layout に書き込む</summary>
    [ContextMenu("保存する")]
    public void Save()
    {
        if (!ready && boxes.Count == 0) return;

        // 部屋の基準が変わっていたら、先に箱を部屋について動かす
        // (基準だけ取り直して箱を動かさずに保存すると、全部の箱がずれた位置で保存される)
        FollowRoom();

        // 部屋の基準が分からないまま保存すると、前の部屋から見た位置が壊れるので保存しない
        if (!hasRoomOrigin && !string.IsNullOrEmpty(layout.roomUuid))
        {
            Debug.LogWarning("[EnvironmentBoxPlacer] MRUK の部屋がまだ無いので保存しない (部屋が読み込まれたら箱を置き直す)", this);
            return;
        }

        foreach (var box in boxes)
        {
            EnvironmentBoxLayout.ToLocal(originPosition, originYaw, box.root.position, box.root.eulerAngles.y,
                out box.data.position, out box.data.yaw);
        }
        layout.originPosition = originPosition;
        layout.originYaw = originYaw;
        layout.roomUuid = roomUuid;

        try { layout.Persist(); }
        catch (System.Exception e) { Debug.LogError($"[EnvironmentBoxPlacer] 保存に失敗: {e.Message}", this); return; }
        Debug.Log($"[EnvironmentBoxPlacer] 箱 {boxes.Count} 個を保存した", this);
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

    // SplatOffsetPlacer がスプラットを動かすあいだ、このコンポーネントを止める。止めているあいだ Ray を隠す
    void OnEnable()
    {
        if (ray != null) ray.enabled = true;
    }

    void OnDisable()
    {
        if (held != null && ready) Save(); // つかんだまま止められたら、そこで離す
        held = null;
        stretching = false;
        if (ray != null) ray.enabled = false;
        if (boxes != null) foreach (var box in boxes) if (box.material != null) box.material.color = boxColor;
    }

    void OnDestroy()
    {
        foreach (var box in boxes) if (box.material != null) Destroy(box.material);
        if (rayMaterial != null) Destroy(rayMaterial);
        if (ray != null) Destroy(ray.gameObject);
    }

#if UNITY_EDITOR
    // Play していないとき: 保存してある箱を、最後に保存したときの位置に枠と名前で描く (名前を付けるときの目印)
    void OnDrawGizmos()
    {
        if (layout == null || Application.isPlaying) return;
        for (int i = 0; i < layout.boxes.Count; i++)
        {
            var b = layout.boxes[i];
            EnvironmentBoxLayout.ToWorld(layout.originPosition, layout.originYaw, b.position, b.yaw, out var position, out var rotation);
            bool named = !string.IsNullOrWhiteSpace(b.name);
            Gizmos.color = named ? new Color(0.2f, 0.6f, 1f, 1f) : new Color(1f, 0.85f, 0.1f, 1f);
            Gizmos.matrix = Matrix4x4.TRS(position, rotation, Vector3.one);
            Gizmos.DrawWireCube(Vector3.zero, b.size);
            Gizmos.matrix = Matrix4x4.identity;
            UnityEditor.Handles.Label(position + Vector3.up * (b.size.y / 2f + 0.03f), layout.LabelOf(i));
        }
    }
#endif
}
