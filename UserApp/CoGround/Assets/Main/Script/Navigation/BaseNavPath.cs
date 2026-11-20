using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 台車の動き = 「その場で回転」と「直進」の並び。時刻 t の位置・向きを Sample で取れる。
/// プレビュー (ゴースト) と実行 (本体) で同じものを使うので、見せた動きと実際の動きが一致する。
///
/// 向き (yaw) は Unity の流儀: 上から見て右回りが正、0° = +Z [deg]。
/// 各区間は SmoothStep で加減速する (区間の長さは 最高速度で動く場合の 1.5 倍 = 最高速度が上限に一致)。
/// </summary>
public class BaseNavPath
{
    public struct Segment
    {
        public bool IsRotation;
        public Vector3 From, To;
        public float YawFrom, YawTo;
        public float StartTime, Duration;
    }

    const float EaseFactor = 1.5f; // SmoothStep のピーク速度 / 平均速度

    readonly List<Segment> segments = new List<Segment>();
    readonly List<Vector3> waypoints = new List<Vector3>();

    public IReadOnlyList<Segment> Segments => segments;
    /// <summary>通る点 (始点・曲がり角・終点)</summary>
    public IReadOnlyList<Vector3> Waypoints => waypoints;
    public float Duration { get; private set; }
    /// <summary>走る距離 [m]</summary>
    public float Length { get; private set; }

    /// <param name="points">始点から終点までの点 (2 点以上)</param>
    /// <param name="startYaw">今の向き [deg]</param>
    /// <param name="goalYaw">最後の向き [deg]</param>
    /// <param name="linearSpeed">直進の最高速度 [m/s]</param>
    /// <param name="angularSpeed">回転の最高速度 [deg/s]</param>
    public static BaseNavPath Build(IList<Vector3> points, float startYaw, float goalYaw, float linearSpeed, float angularSpeed)
    {
        var path = new BaseNavPath();
        path.waypoints.AddRange(points);
        float yaw = startYaw;
        float time = 0f;

        void Rotate(Vector3 at, float to)
        {
            float delta = Mathf.DeltaAngle(yaw, to);
            if (Mathf.Abs(delta) < 0.5f) { yaw = to; return; }
            float d = Mathf.Abs(delta) / angularSpeed * EaseFactor;
            path.segments.Add(new Segment { IsRotation = true, From = at, To = at, YawFrom = yaw, YawTo = yaw + delta, StartTime = time, Duration = d });
            time += d;
            yaw = to;
        }

        for (int i = 0; i + 1 < points.Count; i++)
        {
            Vector3 a = points[i], b = points[i + 1];
            Vector3 flat = Vector3.ProjectOnPlane(b - a, Vector3.up);
            float dist = flat.magnitude;
            if (dist < 1e-3f) continue;
            Rotate(a, YawOf(flat));
            float d = dist / linearSpeed * EaseFactor;
            path.segments.Add(new Segment { From = a, To = b, YawFrom = yaw, YawTo = yaw, StartTime = time, Duration = d });
            time += d;
            path.Length += dist;
        }
        Rotate(points[points.Count - 1], goalYaw);
        path.Duration = time;
        return path;
    }

    public static float YawOf(Vector3 direction) => Mathf.Atan2(direction.x, direction.z) * Mathf.Rad2Deg;

    /// <summary>時刻 t [s] の位置と向き [deg]。範囲外は端の値</summary>
    public void Sample(float t, out Vector3 position, out float yaw)
    {
        int i = SegmentIndexAt(t);
        if (i < 0)
        {
            position = waypoints.Count > 0 ? waypoints[0] : Vector3.zero;
            yaw = 0f;
            return;
        }
        var s = segments[i];
        float u = s.Duration > 1e-6f ? Mathf.Clamp01((t - s.StartTime) / s.Duration) : 1f;
        u = u * u * (3f - 2f * u); // SmoothStep
        position = Vector3.Lerp(s.From, s.To, u);
        yaw = Mathf.Lerp(s.YawFrom, s.YawTo, u);
    }

    /// <summary>時刻 t の区間の番号 (区間が無ければ -1)</summary>
    public int SegmentIndexAt(float t)
    {
        if (segments.Count == 0) return -1;
        for (int i = 0; i < segments.Count; i++)
            if (t < segments[i].StartTime + segments[i].Duration) return i;
        return segments.Count - 1;
    }

    /// <summary>時刻 t から先に通る道 (今の位置 + この先の曲がり角・終点)</summary>
    public void RemainingPoints(float t, List<Vector3> result)
    {
        result.Clear();
        Sample(t, out var here, out _);
        result.Add(here);
        int i = Mathf.Max(SegmentIndexAt(t), 0);
        for (; i < segments.Count; i++)
        {
            if (segments[i].IsRotation) continue;
            if ((segments[i].To - result[result.Count - 1]).sqrMagnitude > 1e-6f) result.Add(segments[i].To);
        }
    }
}
