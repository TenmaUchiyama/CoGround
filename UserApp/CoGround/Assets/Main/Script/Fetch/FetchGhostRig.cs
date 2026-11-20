using System;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 見た目だけの Fetch (ゴースト)。物理 (ArticulationBody) もスクリプトも持たず、関節の Transform を直接回して形を作る。
/// Nav のゴースト (FetchGhost.CreateVisualCopy) と同じ「見た目だけ・動かすのは 1 か所だけ」のやり方で、腕も曲げられるようにしたもの。
///
/// ■ 元になるモデル
///   Resources/FetchGhostModel.prefab (メニュー CoGround > Fetch ゴーストの準備 で作る)。
///   シーンの Fetch (本物) は実行中に一切読まない。本物を非表示・無効にしてもゴーストは同じように出る。
///
/// ■ 関節の回し方 (順運動学を Transform で行う)
///   URDF Importer はリンクを親子にそのまま並べ、関節 0 のときのリンクの位置・向き = URDF の joint origin (To&lt;FLU&gt; で変換) にしている。
///   なので関節の値 q のとき、子リンクのローカルは
///     回転関節: localRotation = rest * AngleAxis(-q [deg], axis)   (ROS の右手系の回転 → Unity では角度の符号が逆になる)
///     直動関節: localPosition = rest + restRotation * (axis * q)
///   axis は URDF の axis を To&lt;FLU&gt; と同じ対応 (x, y, z) → (-y, z, x) で Unity にしたもの (子リンクのローカル)。
///
/// ■ 使い方
///   var rig = FetchGhostRig.Create("名前", material);
///   rig.SetBasePose(位置, 向き);           // base_link の World の位置・向き
///   rig.SetJoint("shoulder_pan_joint", 0.3f); // 関節名 (URDF の joint 名)、rad または m
///   rig.Visible = true;
/// </summary>
public class FetchGhostRig : MonoBehaviour
{
    public const string ResourceName = "FetchGhostModel";

    [Serializable]
    public class Joint
    {
        public string name;
        public bool prismatic;
        public Transform link;
        [Tooltip("子リンクのローカルでの関節の軸 (Unity)")]
        public Vector3 axis;
        public Vector3 restPosition;
        public Quaternion restRotation;
    }

    [SerializeField] Transform baseLink;
    [SerializeField] List<Joint> joints = new List<Joint>();

    readonly Dictionary<string, Joint> jointByName = new Dictionary<string, Joint>();
    readonly Dictionary<string, Transform> linkByName = new Dictionary<string, Transform>();
    Renderer[] renderers;
    Material[][] originalMaterials;
    UnityEngine.Rendering.ShadowCastingMode[] originalShadows;
    bool visible = true;
    bool initialized;

    public Transform BaseLink => baseLink;
    public IReadOnlyList<Joint> Joints => joints;

    /// <summary>
    /// Resources/FetchGhostModel から作る。見つからなければ null (メニューで作るようにエラーを出す)。
    /// 作った直後は非表示。
    /// </summary>
    public static FetchGhostRig Create(string name, Material material)
    {
        var prefab = Resources.Load<FetchGhostRig>(ResourceName);
        if (prefab == null)
        {
            Debug.LogError($"[FetchGhostRig] Resources/{ResourceName}.prefab が無い。" +
                           "Editor でメニュー CoGround > Fetch ゴーストの準備 を一度実行する");
            return null;
        }
        var rig = Instantiate(prefab);
        rig.name = name;
        rig.Init();
        if (material != null) rig.SetMaterial(material);
        rig.Visible = false;
        return rig;
    }

    void Awake() => Init();

    void Init()
    {
        if (initialized) return;
        initialized = true;
        foreach (var j in joints)
            if (j.link != null) jointByName[j.name] = j;
        foreach (var t in GetComponentsInChildren<Transform>(true))
            if (!linkByName.ContainsKey(t.name)) linkByName[t.name] = t;
        renderers = GetComponentsInChildren<Renderer>(true);
        // モデルの元の見た目 (Fetch の URDF のマテリアル) を覚えておく (RestoreOriginalMaterials で戻す)
        originalMaterials = new Material[renderers.Length][];
        originalShadows = new UnityEngine.Rendering.ShadowCastingMode[renderers.Length];
        for (int i = 0; i < renderers.Length; i++)
        {
            originalMaterials[i] = renderers[i].sharedMaterials;
            originalShadows[i] = renderers[i].shadowCastingMode;
        }
        if (baseLink == null) baseLink = transform;
    }

    public bool Visible
    {
        get => visible;
        set
        {
            if (visible == value) return;
            visible = value;
            foreach (var r in renderers) if (r != null) r.enabled = value;
        }
    }

    public void SetMaterial(Material material)
    {
        foreach (var r in renderers)
        {
            var mats = new Material[r.sharedMaterials.Length];
            for (int i = 0; i < mats.Length; i++) mats[i] = material;
            r.sharedMaterials = mats;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
        }
    }

    /// <summary>モデルの元の見た目 (不透明・影あり。本物のロボットとして見せるとき) に戻す</summary>
    public void RestoreOriginalMaterials()
    {
        for (int i = 0; i < renderers.Length; i++)
        {
            renderers[i].sharedMaterials = originalMaterials[i];
            renderers[i].shadowCastingMode = originalShadows[i];
            renderers[i].receiveShadows = true;
        }
    }

    /// <summary>リンク (やその下の Transform) を名前で探す</summary>
    public bool TryGetLink(string linkName, out Transform link) => linkByName.TryGetValue(linkName, out link);

    public bool HasJoint(string jointName) => jointByName.ContainsKey(jointName);

    /// <summary>関節の値 (rad または m) にする。知らない関節名なら false</summary>
    public bool SetJoint(string jointName, float value)
    {
        if (!jointByName.TryGetValue(jointName, out var j)) return false;
        if (j.prismatic)
        {
            j.link.localPosition = j.restPosition + j.restRotation * (j.axis * value);
        }
        else
        {
            j.link.localRotation = j.restRotation * Quaternion.AngleAxis(-value * Mathf.Rad2Deg, j.axis);
        }
        return true;
    }

    public void SetJoints(IReadOnlyDictionary<string, float> values)
    {
        if (values == null) return;
        foreach (var kv in values) SetJoint(kv.Key, kv.Value);
    }

    /// <summary>全部の関節を 0 (モデルを作ったときの姿勢) にする</summary>
    public void ResetJoints()
    {
        foreach (var j in joints)
        {
            if (j.link == null) continue;
            j.link.localPosition = j.restPosition;
            j.link.localRotation = j.restRotation;
        }
    }

    /// <summary>base_link を World のこの位置・向きに置く</summary>
    public void SetBasePose(Vector3 position, Quaternion rotation)
    {
        var root = transform;
        var localRot = Quaternion.Inverse(root.rotation) * baseLink.rotation;
        var localPos = Quaternion.Inverse(root.rotation) * (baseLink.position - root.position);
        var rootRot = rotation * Quaternion.Inverse(localRot);
        root.SetPositionAndRotation(position - rootRot * localPos, rootRot);
    }

    // ---- Editor (メニュー CoGround > Fetch ゴーストの準備) から使う ----
    public void EditorSetup(Transform baseLinkTransform, List<Joint> jointList)
    {
        baseLink = baseLinkTransform;
        joints = jointList;
    }
}
