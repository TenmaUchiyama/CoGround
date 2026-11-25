using UnityEngine;

/// <summary>
/// UI パネルを頭 (カメラ) の下前方にゆっくり追従させる。
///   ・目線より下・近めに置き、顔の方へ傾ける (見下ろすと読める / 正面の視界は空ける)
///   ・顔を大きく横に向けたときだけ付いてくるので、普段は止まっていて読みやすい
///   ・上下の首振り (見下ろす) では動かない
/// </summary>
public class LazyFollowHead : MonoBehaviour
{
    [Tooltip("空なら Camera.main")]
    [SerializeField] private Transform head;
    [Tooltip("頭からの水平距離 (m)")]
    [SerializeField] private float distance = 0.42f;
    [Tooltip("目の高さからのずらし (m, 下はマイナス)")]
    [SerializeField] private float heightOffset = -0.26f;
    [Tooltip("左右にずらす (m, 右がプラス)")]
    [SerializeField] private float sideOffset = 0f;
    [Tooltip("目の方を向く角度に足す傾き (度, プラスでより上向き)")]
    [SerializeField] private float extraTilt = 0f;
    [Tooltip("顔の向きとパネルの水平角度がこれを超えたら追従する")]
    [SerializeField] private float angleThreshold = 35f;
    [Tooltip("頭がこれ以上動いたら追従する (m)")]
    [SerializeField] private float distanceThreshold = 0.2f;
    [SerializeField] private float smoothTime = 0.3f;

    bool following = true;
    Vector3 velocity;

    bool ResolveHead()
    {
        if (head != null) return true;
        if (Camera.main == null) return false;
        head = Camera.main.transform;
        return true;
    }

    Vector3 HeadForward()
    {
        Vector3 f = Vector3.ProjectOnPlane(head.forward, Vector3.up);
        if (f.sqrMagnitude < 1e-4f) f = Vector3.ProjectOnPlane(head.up, Vector3.up); // 真下/真上を見ている
        return f.normalized;
    }

    Vector3 TargetPosition(Vector3 forward)
    {
        Vector3 right = Vector3.Cross(Vector3.up, forward);
        return head.position + forward * distance + right * sideOffset + Vector3.up * heightOffset;
    }

    /// <summary>目の方を向く (下にあるので自然に上向きに傾く)。Canvas は -Z が表</summary>
    Quaternion FacingRotation(Vector3 position)
    {
        Vector3 look = position - head.position;
        if (look.sqrMagnitude < 1e-6f) return transform.rotation;
        var rot = Quaternion.LookRotation(look.normalized, Vector3.up);
        return rot * Quaternion.Euler(-extraTilt, 0f, 0f);
    }

    void LateUpdate()
    {
        if (!ResolveHead()) return;

        Vector3 forward = HeadForward();
        Vector3 target = TargetPosition(forward);

        // 定位置の方向と比べる (横にずらしたパネルが、正面からのずれだけで追従し続けないように)
        Vector3 toPanel = Vector3.ProjectOnPlane(transform.position - head.position, Vector3.up);
        Vector3 toTarget = Vector3.ProjectOnPlane(target - head.position, Vector3.up);
        float angle = Vector3.Angle(toPanel, toTarget.sqrMagnitude > 1e-6f ? toTarget : forward);
        if (angle > angleThreshold || (transform.position - target).magnitude > distanceThreshold + distance * 0.5f)
            following = true;

        if (following)
        {
            transform.position = Vector3.SmoothDamp(transform.position, target, ref velocity, smoothTime);
            if ((transform.position - target).sqrMagnitude < 0.0002f) following = false;
        }

        transform.rotation = Quaternion.Slerp(transform.rotation, FacingRotation(transform.position), Time.deltaTime * 10f);
    }

    /// <summary>すぐに定位置へ移動</summary>
    public void SnapToFront()
    {
        if (!ResolveHead()) return;
        following = false;
        velocity = Vector3.zero;
        transform.position = TargetPosition(HeadForward());
        transform.rotation = FacingRotation(transform.position);
    }

    void OnEnable() => SnapToFront();
}
