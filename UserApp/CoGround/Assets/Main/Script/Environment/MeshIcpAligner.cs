using System.Collections.Generic;
using Meta.XR.MRUtilityKit;
using UnityEngine;

/// <summary>
/// スキャンのメッシュ (Source。LivingModel.fbx など) を、MRUK の部屋のメッシュ (GLOBAL_MESH) に ICP で重ねる。
/// 動かすのは Source の親 (SplatOffsetPlacer の Target = Splat Align)。だから同じ親の子のスプラットも一緒に合う。
///
/// ■ 何を合わせるか
///   位置 (x, y, z) と真上まわりの向き (yaw) だけ。傾きと大きさは変えない
///   (重力の向きはどちらも分かっていて、傾きまで動かすと床や壁が少ない場所で暴れるため。大きさは先に合わせておく)。
///
/// ■ 使い方
///   先にコントローラで大まかに合わせてから Align を呼ぶ (ICP は近くの面に吸い付くので、最初が大きくずれていると間違える)。
///   目安は位置 0.3 m、向き 15° 以内。SplatOffsetPlacer のスプラットを動かすモードで右 A を押すと、これが走って保存される。
///
/// ■ 必要なもの
///   Source の FBX はインポート設定で Read/Write を ON にする (Play 中に頂点を読むため)。
/// </summary>
public class MeshIcpAligner : MonoBehaviour
{
    [Tooltip("部屋に重ねるスキャンのメッシュ (この下の MeshFilter を全部使う)")]
    [SerializeField] Transform source;

    [Header("ICP")]
    [Tooltip("スキャンのメッシュから取る点の数")]
    [SerializeField] int sourceSamples = 4000;
    [Tooltip("部屋のメッシュから取る点の数")]
    [SerializeField] int roomSamples = 40000;
    [SerializeField] int iterations = 40;
    [Tooltip("最初に組にする距離の上限 [m] (これより遠い点は使わない)")]
    [SerializeField] float startMaxDistance = 0.5f;
    [Tooltip("最後に組にする距離の上限 [m]")]
    [SerializeField] float endMaxDistance = 0.05f;
    [Tooltip("1 回で動いた量がこれより小さければ (かつ上限が最後まで縮んでいれば) 止める [m]")]
    [SerializeField] float converge = 0.0005f;
    [Tooltip("1 回の Align で動かしてよい量。超えたら失敗として元に戻す [m]")]
    [SerializeField] float maxShift = 1.0f;
    [Tooltip("1 回の Align で回してよい量。超えたら失敗として元に戻す [deg]")]
    [SerializeField] float maxTurn = 30f;

    public Transform Source => source;

    /// <summary>
    /// moveTarget (Source の親) を動かして、Source を部屋のメッシュに重ねる。
    /// 成功したら true。失敗したら moveTarget は動かさず、理由を report に入れる。
    /// </summary>
    public bool Align(Transform moveTarget, out string report)
    {
        report = "";
        if (source == null || moveTarget == null) { report = "Source か Target が未設定"; return false; }
        if (!source.IsChildOf(moveTarget)) { report = "Source が Target の子になっていない"; return false; }

        var room = MRUK.Instance != null ? (MRUK.Instance.GetCurrentRoom() ?? (MRUK.Instance.Rooms.Count > 0 ? MRUK.Instance.Rooms[0] : null)) : null;
        var anchor = room != null ? room.GlobalMeshAnchor : null;
        var roomMesh = anchor != null ? anchor.GlobalMesh : null;
        if (roomMesh == null) { report = "部屋のメッシュ (GLOBAL_MESH) が無い"; return false; }

        var rng = new System.Random(1234);
        var roomPoints = SampleMesh(new List<(Mesh, Matrix4x4)> { (roomMesh, anchor.transform.localToWorldMatrix) }, roomSamples, rng, out string roomError);
        if (roomPoints == null) { report = "部屋のメッシュ: " + roomError; return false; }
        var sourceMeshes = new List<(Mesh, Matrix4x4)>();
        foreach (var mf in source.GetComponentsInChildren<MeshFilter>(true))
        {
            if (mf.sharedMesh == null) continue;
            if (!mf.sharedMesh.isReadable) { report = $"{mf.sharedMesh.name} が読めない。FBX のインポート設定で Read/Write を ON にすること"; return false; }
            sourceMeshes.Add((mf.sharedMesh, mf.transform.localToWorldMatrix));
        }
        var srcPoints = SampleMesh(sourceMeshes, sourceSamples, rng, out string srcError);
        if (srcPoints == null) { report = "スキャンのメッシュ: " + srcError; return false; }

        var tree = new PointKdTree(roomPoints);

        // 合計の動き: p' = Rot(yaw) * p + shift
        float yaw = 0f;
        Vector3 shift = Vector3.zero;
        var moved = new Vector3[srcPoints.Length];
        var a = new List<Vector3>(srcPoints.Length);
        var b = new List<Vector3>(srcPoints.Length);
        float rms = 0f;
        int used = 0;

        for (int it = 0; it < iterations; it++)
        {
            float t = iterations > 1 ? (float)it / (iterations - 1) : 1f;
            float maxDist = Mathf.Lerp(startMaxDistance, endMaxDistance, Mathf.Clamp01(t * 1.5f));
            var rot = Quaternion.Euler(0f, yaw, 0f);
            for (int i = 0; i < srcPoints.Length; i++) moved[i] = rot * srcPoints[i] + shift;

            a.Clear();
            b.Clear();
            float sum = 0f;
            for (int i = 0; i < moved.Length; i++)
            {
                if (!tree.Nearest(moved[i], maxDist * maxDist, out var hit, out float dsq)) continue;
                a.Add(moved[i]);
                b.Add(hit);
                sum += dsq;
            }
            used = a.Count;
            if (used < 50) { report = $"重なる点が少なすぎる ({used} 点)。先にコントローラでもっと近づけること"; return false; }
            rms = Mathf.Sqrt(sum / used);

            SolveYawShift(a, b, out float dYaw, out Vector3 dShift);
            // 今の動きに足す: p'' = dRot * (Rot p + shift) + dShift
            var dRot = Quaternion.Euler(0f, dYaw, 0f);
            yaw += dYaw;
            shift = dRot * shift + dShift;

            if (maxDist <= endMaxDistance + 1e-4f && dShift.magnitude < converge && Mathf.Abs(dYaw) < 0.02f) break;
        }

        // 合計の動きで最後に 1 回 RMS を測る
        {
            var rot = Quaternion.Euler(0f, yaw, 0f);
            float sum = 0f;
            used = 0;
            for (int i = 0; i < srcPoints.Length; i++)
            {
                if (!tree.Nearest(rot * srcPoints[i] + shift, endMaxDistance * endMaxDistance, out _, out float dsq)) continue;
                sum += dsq;
                used++;
            }
            rms = used > 0 ? Mathf.Sqrt(sum / used) : float.PositiveInfinity;
        }

        // 動いた量 (Target の位置で測る)
        var finalRot = Quaternion.Euler(0f, yaw, 0f);
        var newPosition = finalRot * moveTarget.position + shift;
        float moveDist = Vector3.Distance(newPosition, moveTarget.position);
        float turn = Mathf.Abs(Mathf.DeltaAngle(0f, yaw));
        if (moveDist > maxShift || turn > maxTurn)
        {
            report = $"動きが大きすぎる (位置 {moveDist:0.00} m, 向き {turn:0.0}°)。間違った場所に吸い付いた可能性があるので動かさなかった";
            return false;
        }

        moveTarget.SetPositionAndRotation(newPosition, finalRot * moveTarget.rotation);
        float inlier = (float)used / srcPoints.Length;
        report = $"位置 {moveDist * 100f:0.0} cm, 向き {Mathf.DeltaAngle(0f, yaw):0.00}° 動かした。" +
                 $"誤差 (RMS) {rms * 100f:0.0} cm、{endMaxDistance * 100f:0} cm 以内の点 {inlier * 100f:0}%";
        return true;
    }

    /// <summary>a を真上まわりに回して動かし b に重ねる、いちばん近い回転と移動 (最小二乗)</summary>
    static void SolveYawShift(List<Vector3> a, List<Vector3> b, out float yawDeg, out Vector3 shift)
    {
        Vector3 ma = Vector3.zero, mb = Vector3.zero;
        for (int i = 0; i < a.Count; i++) { ma += a[i]; mb += b[i]; }
        ma /= a.Count;
        mb /= a.Count;

        // Unity の Euler(0, θ, 0) は (x, z) → (x cosθ + z sinθ, -x sinθ + z cosθ)
        double sc = 0, ss = 0;
        for (int i = 0; i < a.Count; i++)
        {
            var p = a[i] - ma;
            var q = b[i] - mb;
            sc += p.x * q.x + p.z * q.z;
            ss += p.z * q.x - p.x * q.z;
        }
        yawDeg = (float)(System.Math.Atan2(ss, sc) * 180.0 / System.Math.PI);
        shift = mb - Quaternion.Euler(0f, yawDeg, 0f) * ma;
    }

    /// <summary>三角形の面積に比例して、面の上の点をワールド座標で取る</summary>
    static Vector3[] SampleMesh(List<(Mesh mesh, Matrix4x4 toWorld)> meshes, int count, System.Random rng, out string error)
    {
        error = "";
        var tris = new List<(Vector3 a, Vector3 b, Vector3 c)>();
        var cumulative = new List<double>();
        double total = 0;
        foreach (var (mesh, toWorld) in meshes)
        {
            var v = mesh.vertices;
            for (int s = 0; s < mesh.subMeshCount; s++)
            {
                if (mesh.GetTopology(s) != MeshTopology.Triangles) continue;
                var idx = mesh.GetTriangles(s);
                for (int i = 0; i + 2 < idx.Length; i += 3)
                {
                    var p0 = toWorld.MultiplyPoint3x4(v[idx[i]]);
                    var p1 = toWorld.MultiplyPoint3x4(v[idx[i + 1]]);
                    var p2 = toWorld.MultiplyPoint3x4(v[idx[i + 2]]);
                    double area = Vector3.Cross(p1 - p0, p2 - p0).magnitude * 0.5;
                    if (area <= 1e-10) continue;
                    total += area;
                    tris.Add((p0, p1, p2));
                    cumulative.Add(total);
                }
            }
        }
        if (tris.Count == 0) { error = "三角形が無い"; return null; }

        var points = new Vector3[count];
        for (int i = 0; i < count; i++)
        {
            int k = cumulative.BinarySearch(rng.NextDouble() * total);
            if (k < 0) k = ~k;
            if (k >= tris.Count) k = tris.Count - 1;
            float u = (float)rng.NextDouble(), w = (float)rng.NextDouble();
            if (u + w > 1f) { u = 1f - u; w = 1f - w; }
            var (a, b, c) = tris[k];
            points[i] = a + (b - a) * u + (c - a) * w;
        }
        return points;
    }

    /// <summary>いちばん近い点を探すための k-d 木</summary>
    sealed class PointKdTree
    {
        readonly Vector3[] points;
        readonly int[] order;

        public PointKdTree(Vector3[] points)
        {
            this.points = points;
            order = new int[points.Length];
            for (int i = 0; i < order.Length; i++) order[i] = i;
            Build(0, order.Length, 0);
        }

        void Build(int lo, int hi, int axis)
        {
            if (hi - lo <= 1) return;
            var pts = points;
            System.Array.Sort(order, lo, hi - lo, Comparer<int>.Create((x, y) => pts[x][axis].CompareTo(pts[y][axis])));
            int mid = (lo + hi) / 2;
            int next = (axis + 1) % 3;
            Build(lo, mid, next);
            Build(mid + 1, hi, next);
        }

        /// <summary>q からいちばん近い点 (距離の 2 乗が maxSq 以下のものだけ)</summary>
        public bool Nearest(Vector3 q, float maxSq, out Vector3 hit, out float distSq)
        {
            int best = -1;
            float bestSq = maxSq;
            Search(0, order.Length, 0, q, ref best, ref bestSq);
            hit = best >= 0 ? points[best] : default;
            distSq = bestSq;
            return best >= 0;
        }

        void Search(int lo, int hi, int axis, Vector3 q, ref int best, ref float bestSq)
        {
            if (lo >= hi) return;
            int mid = (lo + hi) / 2;
            var m = points[order[mid]];
            float d = (m - q).sqrMagnitude;
            if (d < bestSq) { bestSq = d; best = order[mid]; }
            float diff = q[axis] - m[axis];
            int next = (axis + 1) % 3;
            if (diff < 0f)
            {
                Search(lo, mid, next, q, ref best, ref bestSq);
                if (diff * diff < bestSq) Search(mid + 1, hi, next, q, ref best, ref bestSq);
            }
            else
            {
                Search(mid + 1, hi, next, q, ref best, ref bestSq);
                if (diff * diff < bestSq) Search(lo, mid, next, q, ref best, ref bestSq);
            }
        }
    }
}
