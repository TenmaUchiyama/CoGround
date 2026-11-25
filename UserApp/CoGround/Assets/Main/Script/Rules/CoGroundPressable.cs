using System;
using UnityEngine;

/// <summary>
/// World Space の Canvas (物体の吹き出しなど) を、Ray で押せるようにする。
/// Canvas の大きさに合わせた薄い当たり判定 (トリガー) を付ける。Ray を当てて押すのは使う側 (CoGroundRuleTagView)。
///
/// トリガーなので、物理・台車の経路 (BaseNavPlanner)・床を指す Ray (ControllerNavGoal) には当たらない
/// (どれも QueryTriggerInteraction.Ignore)。
///
/// ■ スクリプトから
///   CoGroundPressable.Add(吹き出しのルート, 押されたときの処理)。
///   CoGroundPressable.Raycast(ray, 距離) で Ray の先のいちばん近いもの、SetHovered で指している印 (少し大きくする)、Press() で押す。
/// </summary>
public class CoGroundPressable : MonoBehaviour
{
    [Tooltip("Ray が当たっている間の大きさ (何倍か)")]
    [SerializeField] float hoverScale = 1.08f;
    [Tooltip("当たり判定の厚み [m]")]
    [SerializeField] float thickness = 0.01f;

    public event Action Pressed;

    RectTransform rect;
    BoxCollider box;
    Vector3 baseScale;

    static CoGroundPressable hovered;
    static readonly RaycastHit[] hits = new RaycastHit[32];

    /// <summary>root 以下の最初の Canvas を押せるようにする。Canvas が無ければ null</summary>
    public static CoGroundPressable Add(GameObject root, Action onPress)
    {
        var canvas = root.GetComponentInChildren<Canvas>(true);
        if (canvas == null) return null;
        var p = root.AddComponent<CoGroundPressable>();
        p.rect = (RectTransform)canvas.rootCanvas.transform;
        p.box = p.rect.gameObject.AddComponent<BoxCollider>();
        p.box.isTrigger = true;
        p.baseScale = root.transform.localScale;
        p.Pressed += onPress;
        p.Fit();
        return p;
    }

    /// <summary>Ray の先の、いちばん近い押せるもの (無ければ null)。手前に物があっても選べる</summary>
    public static CoGroundPressable Raycast(Ray ray, float maxDistance)
    {
        int n = Physics.RaycastNonAlloc(ray, hits, maxDistance, ~0, QueryTriggerInteraction.Collide);
        CoGroundPressable best = null;
        float bestDistance = float.PositiveInfinity;
        for (int i = 0; i < n; i++)
        {
            if (hits[i].distance >= bestDistance) continue;
            var p = hits[i].collider.GetComponentInParent<CoGroundPressable>();
            if (p == null || !p.isActiveAndEnabled) continue;
            best = p;
            bestDistance = hits[i].distance;
        }
        return best;
    }

    /// <summary>Ray が指しているものを少し大きくする (null で戻す)</summary>
    public static void SetHovered(CoGroundPressable target)
    {
        if (hovered == target) return;
        if (hovered != null) hovered.transform.localScale = hovered.baseScale;
        hovered = target;
        if (hovered != null) hovered.transform.localScale = hovered.baseScale * hovered.hoverScale;
    }

    public void Press() => Pressed?.Invoke();

    // 中身に合わせて Canvas の大きさが変わる (ContentSizeFitter) ので、毎フレーム合わせる
    void LateUpdate() => Fit();

    void Fit()
    {
        if (rect == null || box == null) return;
        var r = rect.rect;
        float depth = thickness / Mathf.Max(1e-5f, Mathf.Abs(rect.lossyScale.z));
        box.center = new Vector3(r.center.x, r.center.y, 0f);
        box.size = new Vector3(r.width, r.height, depth);
    }

    void OnDisable()
    {
        if (hovered == this) hovered = null;
    }
}
