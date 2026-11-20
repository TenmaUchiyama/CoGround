using System;
using System.Collections.Generic;
using Meta.XR;
using UnityEngine;

/// <summary>1 フレーム分の検出を 3D の箱にしたもの（平滑化前の生の値）。</summary>
public struct LocatedBox
{
    public string Label;
    public float Score;
    public Vector3 Center;       // 箱の中心（ワールド）
    public Quaternion Rotation;  // ヨーのみ。ローカル X = 画面の左右方向、Z = 奥行き方向
    public Vector3 Size;         // (幅, 高さ, 奥行き) [m]
    public string Method;        // "surface" / "billboard" / "fallback"
}

[Serializable]
public class DetectionLocatorSettings
{
    [Header("複数点のレイキャスト")]
    [Tooltip("矩形の内側に N×N 点のレイを飛ばす。")]
    [Range(1, 5)] public int gridSize = 3;

    [Tooltip("レイを飛ばす範囲（矩形の中心寄りの割合）。0.6 = 中心寄り 60%。")]
    [Range(0.2f, 1f)] public float innerFraction = 0.6f;

    [Tooltip("手前側の距離（下位 25%）より、この割合以上奥に当たった点は背景として捨てる。")]
    public float backgroundRelTolerance = 0.25f;

    [Tooltip("背景判定に足す固定の余裕 [m]。")]
    public float backgroundAbsTolerance = 0.05f;

    [Tooltip("レイの最大距離 [m]。")]
    public float maxRayDistance = 5f;

    [Header("机の面に合わせる")]
    [Tooltip("矩形の下端のすぐ下にレイを当てて机の高さを求め、机に平置きの箱を作る。")]
    public bool fitToSurface = true;

    [Tooltip("机を探すレイを、矩形の下端からどれだけ下に飛ばすか（矩形の高さに対する割合）。")]
    public float bottomProbeMargin = 0.04f;

    [Tooltip("箱の最小の高さ [m]。")]
    public float minHeight = 0.02f;

    [Tooltip("箱の最小の奥行き [m]。")]
    public float minDepth = 0.03f;

    [Tooltip("奥行きの上限 = 幅 × この値。")]
    public float maxDepthRatio = 2f;

    [Tooltip("奥行きを実測できないときの仮定: 奥行き = 幅 × この値。")]
    public float depthRatio = 1f;

    [Header("レイが 1 本も当たらないとき")]
    [Tooltip("カメラから固定距離の位置に箱を置く（デプスが無い環境のデバッグ用）。")]
    public bool useFallbackDistance = true;

    public float fallbackDistance = 1f;
}

/// <summary>
/// 2D の検出矩形（カメラ画像のピクセル）と「撮影時のカメラ姿勢」から 3D の箱を作る。
///
///   1. 矩形の内側に複数のレイを飛ばし、奥に飛びすぎた点（背景）を捨てる
///   2. 矩形の下端のすぐ下にレイを当てて、机の高さを求める
///   3. 机に平置き・画面の左右方向に揃えた箱を作る
///        手前の面 = 矩形の下端のレイ と 机の面 の交点
///        高さ     = 当たった点の最高点 − 机の高さ
///        奥行き   = 矩形の上端のレイ と 物体の上面 の交点まで
///        幅       = 矩形の左右端 と 手前の面の辺 の交点の間隔
///
/// 机の面に合わせられないとき（カメラが物体より低い等）は、従来どおりカメラ向きの箱にする。
/// </summary>
public class DetectionLocator
{
    /// <summary>現実の面（環境デプスやコライダー）へのレイキャスト。</summary>
    public delegate bool SurfaceRaycast(Ray ray, out Vector3 point, out Vector3 normal);

    private struct Hit
    {
        public Vector3 Point;
        public float Distance;
    }

    private readonly PassthroughCameraAccess _cam;
    private readonly SurfaceRaycast _raycast;
    private readonly DetectionLocatorSettings _s;
    private readonly List<Hit> _hits = new();
    private readonly List<float> _scratch = new();

    public DetectionLocator(PassthroughCameraAccess cam, SurfaceRaycast raycast, DetectionLocatorSettings settings)
    {
        _cam = cam;
        _raycast = raycast;
        _s = settings;
    }

    /// <param name="texSize">矩形の座標系になっているカメラ画像のサイズ（ピクセル）。</param>
    /// <param name="pose">その画像を撮影したときのカメラ姿勢。</param>
    public bool TryLocate(float xmin, float ymin, float xmax, float ymax, Vector2 texSize, Pose pose, out LocatedBox box)
    {
        box = default;
        if (xmin > xmax) (xmin, xmax) = (xmax, xmin);
        if (ymin > ymax) (ymin, ymax) = (ymax, ymin);
        float w = xmax - xmin, h = ymax - ymin;
        if (w < 1f || h < 1f || texSize.x < 1f || texSize.y < 1f) return false;

        // ピクセル → ビューポート (0..1)。画像は上が y=0、ビューポートは下が 0 なので反転する
        Ray RayAt(float px, float py) =>
            _cam.ViewportPointToRay(new Vector2(px / texSize.x, 1f - py / texSize.y), pose);

        float cx = (xmin + xmax) * 0.5f, cy = (ymin + ymax) * 0.5f;

        // ---- 1. 複数点のレイキャスト ----
        _hits.Clear();
        int n = Mathf.Max(1, _s.gridSize);
        float lo = (1f - _s.innerFraction) * 0.5f;
        for (int iy = 0; iy < n; iy++)
        {
            for (int ix = 0; ix < n; ix++)
            {
                float u = n == 1 ? 0.5f : lo + _s.innerFraction * ix / (n - 1);
                float v = n == 1 ? 0.5f : lo + _s.innerFraction * iy / (n - 1);
                Cast(RayAt(xmin + u * w, ymin + v * h), pose);
            }
        }
        // 高さを測るための追加の点（矩形の上端寄り）。背景に当たった点は下で捨てられる
        for (int i = 1; i <= 3; i++)
            Cast(RayAt(xmin + w * i / 4f, ymin + h * 0.1f), pose);

        if (_hits.Count == 0)
        {
            if (!_s.useFallbackDistance) return false;
            box = Billboard(RayAt(cx, cy), RayAt(xmin, cy), RayAt(xmax, cy), RayAt(cx, ymin), RayAt(cx, ymax),
                _s.fallbackDistance, "fallback");
            return IsValid(box);
        }

        // ---- 背景を捨てる: 手前側（下位 25%）の距離より大きく奥の点は使わない ----
        _scratch.Clear();
        foreach (var hit in _hits) _scratch.Add(hit.Distance);
        float limit = Percentile(_scratch, 0.25f) * (1f + _s.backgroundRelTolerance) + _s.backgroundAbsTolerance;
        _hits.RemoveAll(hit => hit.Distance > limit);

        _scratch.Clear();
        foreach (var hit in _hits) _scratch.Add(hit.Distance);
        float frontDistance = Percentile(_scratch, 0.5f);

        if (_s.fitToSurface &&
            TryFitToSurface(xmin, ymin, xmax, ymax, texSize, pose, RayAt, out box))
        {
            return true;
        }

        // 机の面に合わせられない → カメラ向きの箱（距離だけ複数点の代表値を使う）
        box = Billboard(RayAt(cx, cy), RayAt(xmin, cy), RayAt(xmax, cy), RayAt(cx, ymin), RayAt(cx, ymax),
            frontDistance, "billboard");
        return IsValid(box);
    }

    // ---- 2〜3. 机の面に合わせた箱 ----
    private bool TryFitToSurface(float xmin, float ymin, float xmax, float ymax, Vector2 texSize, Pose pose,
        Func<float, float, Ray> rayAt, out LocatedBox box)
    {
        box = default;
        float w = xmax - xmin, h = ymax - ymin;
        float cx = (xmin + xmax) * 0.5f;

        // 箱の軸: X = カメラの右方向を水平にしたもの、Z = それに直交する水平方向（カメラから見て奥）
        Vector3 right = pose.rotation * Vector3.right;
        right.y = 0f;
        if (right.sqrMagnitude < 1e-4f) return false;
        right.Normalize();
        Vector3 fwd = Vector3.Cross(right, Vector3.up);

        // 当たった点の高さ
        _scratch.Clear();
        foreach (var hit in _hits) _scratch.Add(hit.Point.y);
        float topY = Percentile(_scratch, 1f);
        float lowY = Percentile(_scratch, 0.25f);

        // 机の高さ: 矩形の下端のすぐ下（物体の手前の机）に当てる
        _scratch.Clear();
        float probeY = Mathf.Min(ymax + h * _s.bottomProbeMargin, texSize.y - 1f);
        for (int i = 1; i <= 3; i++)
        {
            if (_raycast(rayAt(xmin + w * i / 4f, probeY), out var p, out var normal) && normal.y > 0.5f)
                _scratch.Add(p.y);
        }
        float deskY = _scratch.Count > 0 ? Mathf.Min(Percentile(_scratch, 0.5f), lowY) : lowY;
        if (deskY >= pose.position.y - 0.02f) return false; // カメラが机より上にないと成り立たない

        // 手前の面: 矩形の下端のレイ と 机の面
        if (!HorizontalPlanePoint(rayAt(cx, ymax), deskY, out var front)) return false;
        float zFront = Vector3.Dot(fwd, front);

        // 高さ: 実測（最高点 − 机）。矩形の上端のレイが手前の面を通る高さで上限/下限をかける
        float height = Mathf.Max(topY - deskY, _s.minHeight);
        Ray topRay = rayAt(cx, ymin);
        if (VerticalPlanePoint(topRay, fwd, zFront, out var topAtFront))
        {
            float bound = topAtFront.y - deskY;
            // レイが下向きなら、物体の上端はこの高さより低い。上向きなら、これより高い。
            height = topRay.direction.y < 0f ? Mathf.Min(height, bound) : Mathf.Max(height, bound);
            height = Mathf.Max(height, _s.minHeight);
        }

        // 幅と左右位置: 矩形の左右端は「手前の面の、カメラに一番近い高さの辺」で決まるので、その辺の上で測る
        float edgeY = Mathf.Clamp(pose.position.y, deskY, deskY + height);
        Vector3 edgePoint = fwd * zFront + Vector3.up * edgeY;
        if (!LateralOnEdge(rayAt(xmin, ymin), rayAt(xmin, ymax), edgePoint, right, out float leftX) ||
            !LateralOnEdge(rayAt(xmax, ymin), rayAt(xmax, ymax), edgePoint, right, out float rightX))
        {
            return false;
        }
        float width = rightX - leftX;
        float lateral = (leftX + rightX) * 0.5f;
        if (width <= 0f) return false;

        // 奥行き: 矩形の上端のレイ と 物体の上面（机 + 高さ）の交点 = 奥の上の辺
        // （上面を見下ろしていないときは測れないので、幅からの仮定のまま）
        float depth = width * _s.depthRatio;
        if (topRay.direction.y < 0f && HorizontalPlanePoint(topRay, deskY + height, out var back))
        {
            float measured = Vector3.Dot(fwd, back) - zFront;
            if (measured > 0f) depth = measured;
        }
        depth = Mathf.Clamp(depth, _s.minDepth, Mathf.Max(_s.minDepth, width * _s.maxDepthRatio));
        float zCenter = zFront + depth * 0.5f;

        box = new LocatedBox
        {
            Center = right * lateral + fwd * zCenter + Vector3.up * (deskY + height * 0.5f),
            Rotation = Quaternion.LookRotation(fwd, Vector3.up),
            Size = new Vector3(width, height, depth),
            Method = "surface",
        };
        return IsValid(box);
    }

    // ---- 従来方式: カメラから distance の位置に、カメラ向き（ヨーのみ）の箱を置く ----
    private LocatedBox Billboard(Ray center, Ray left, Ray right, Ray top, Ray bottom, float distance, string method)
    {
        float width = Vector3.Distance(left.GetPoint(distance), right.GetPoint(distance));
        float height = Vector3.Distance(top.GetPoint(distance), bottom.GetPoint(distance));
        float depth = Mathf.Max(width * _s.depthRatio, _s.minDepth);

        Vector3 forward = center.direction;
        forward.y = 0f;
        if (forward.sqrMagnitude < 1e-6f) forward = Vector3.forward;
        Quaternion rot = Quaternion.LookRotation(forward.normalized, Vector3.up);

        // レイが当たったのは「物体の手前の面」なので、箱の中心は depth/2 だけ奥
        return new LocatedBox
        {
            Center = center.GetPoint(distance) + rot * Vector3.forward * (depth * 0.5f),
            Rotation = rot,
            Size = new Vector3(width, height, depth),
            Method = method,
        };
    }

    private void Cast(Ray ray, Pose pose)
    {
        if (!_raycast(ray, out var point, out _)) return;
        float distance = Vector3.Distance(pose.position, point);
        if (distance > 0.05f && distance <= _s.maxRayDistance)
            _hits.Add(new Hit { Point = point, Distance = distance });
    }

    /// <summary>
    /// 画像の縦 1 列（同じ x の 2 本のレイが張る平面）と、edgePoint を通る right 方向の直線の交点。
    /// 交点の right 方向の座標を返す。
    /// </summary>
    private static bool LateralOnEdge(Ray columnTop, Ray columnBottom, Vector3 edgePoint, Vector3 right, out float lateral)
    {
        lateral = 0f;
        Vector3 normal = Vector3.Cross(columnTop.direction, columnBottom.direction);
        float denom = Vector3.Dot(normal, right);
        if (Mathf.Abs(denom) < 1e-6f) return false;
        float t = Vector3.Dot(normal, columnTop.origin - edgePoint) / denom;
        lateral = Vector3.Dot(right, edgePoint) + t;
        return true;
    }

    /// <summary>レイと水平面 (y = planeY) の交点。</summary>
    private static bool HorizontalPlanePoint(Ray ray, float planeY, out Vector3 point)
    {
        point = default;
        if (Mathf.Abs(ray.direction.y) < 1e-4f) return false;
        float t = (planeY - ray.origin.y) / ray.direction.y;
        if (t <= 0f) return false;
        point = ray.GetPoint(t);
        return true;
    }

    /// <summary>レイと垂直面（法線 fwd、fwd 方向の位置 z）の交点。</summary>
    private static bool VerticalPlanePoint(Ray ray, Vector3 fwd, float z, out Vector3 point)
    {
        point = default;
        float denom = Vector3.Dot(ray.direction, fwd);
        if (denom < 1e-4f) return false;
        float t = (z - Vector3.Dot(ray.origin, fwd)) / denom;
        if (t <= 0f) return false;
        point = ray.GetPoint(t);
        return true;
    }

    private static bool IsValid(LocatedBox box)
    {
        Vector3 c = box.Center, s = box.Size;
        return IsFinite(c.x) && IsFinite(c.y) && IsFinite(c.z) &&
               s.x > 0f && s.y > 0f && s.z > 0f && s.x < 3f && s.y < 3f && s.z < 3f;
    }

    private static bool IsFinite(float v) => !float.IsNaN(v) && !float.IsInfinity(v);

    /// <summary>values を並べ替えて p (0..1) の位置の値を返す。values は空でないこと。</summary>
    private static float Percentile(List<float> values, float p)
    {
        values.Sort();
        return values[Mathf.Clamp(Mathf.RoundToInt(p * (values.Count - 1)), 0, values.Count - 1)];
    }
}
