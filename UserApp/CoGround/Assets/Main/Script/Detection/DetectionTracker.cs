using System;
using System.Collections.Generic;
using UnityEngine;

[Serializable]
public class DetectionTrackerSettings
{
    [Header("対応づけ")]
    [Tooltip("同じラベルで、中心がこの距離 [m] 以内なら同じ物体とみなす（物体が大きいときは、その半分の大きさまで広げる）。")]
    public float matchDistance = 0.15f;

    [Tooltip("この回数検出されるまでは表示しない（一瞬だけの誤検出を出さないため）。")]
    public int confirmAfterHits = 2;

    [Tooltip("視界に入っているのに、この秒数検出されなければ消す。")]
    public float forgetAfterSeconds = 1.5f;

    [Tooltip("固定済みの物体を消すまでの秒数（手で一時的に隠れても残すため長め）。")]
    public float lockedForgetAfterSeconds = 3f;

    [Header("平滑化")]
    [Tooltip("直近 N 回の中央値を目標にする（外れ値を捨てる）。1 で無効。")]
    [Range(1, 15)] public int medianWindow = 5;

    [Tooltip("0 = 目標値にすぐ追従、1 に近いほど滑らかで遅い。")]
    [Range(0f, 0.95f)] public float smoothing = 0.6f;

    [Header("固定")]
    [Tooltip("この回数連続で安定したら箱を固定する。0 = 固定しない。")]
    public int lockAfterStableDetections = 5;

    [Tooltip("検出の中心が今の箱からこの距離 [m] 以内なら「安定」。")]
    public float stableDistance = 0.03f;

    [Tooltip("検出のサイズが今の箱からこの割合以内なら「安定」。")]
    public float stableSizeRatio = 0.15f;

    [Tooltip("サイズの差がこの長さ [m] 以内なら、割合に関係なく「安定」。\n" +
             "キーボードのような薄い物は、高さ 3cm に対してデプスの誤差が 1cm あるだけで 30% ずれるので、割合だけだと固定されない。")]
    public float stableSizeAbs = 0.03f;

    [Tooltip("固定中、検出がこの距離 [m] 以上ずれたら「動いた」と数える。")]
    public float unlockDistance = 0.08f;

    [Tooltip("「動いた」がこの回数続いたら固定を解除して追従し直す。")]
    public int unlockAfterDetections = 3;

    [Header("計測")]
    [Tooltip("ばらつき（標準偏差）を計算する時間窓 [秒]。")]
    public float statsWindowSeconds = 10f;
}

/// <summary>追跡中の物体 1 個。Center / Rotation / Size は平滑化済みの値。</summary>
public class DetectionTrack
{
    public int Id { get; internal set; }
    public string Label { get; internal set; }
    public float Score { get; internal set; }
    public Vector3 Center { get; internal set; }
    public Quaternion Rotation { get; internal set; }
    public Vector3 Size { get; internal set; }
    public string Method { get; internal set; }
    public int Hits { get; internal set; }
    public int StableCount { get; internal set; }
    public bool IsConfirmed { get; internal set; }
    public bool IsLocked { get; internal set; }

    internal float UnseenTime;
    internal int MovedCount;
    internal bool Matched;
    internal readonly List<Vector3> RecentCenters = new();
    internal readonly List<Vector3> RecentSizes = new();
    internal readonly List<Sample> Samples = new();

    internal struct Sample
    {
        public float Time;
        public Vector3 RawCenter, RawSize, OutCenter, OutSize;
    }
}

/// <summary>物体を動かさずに置いたときの、位置とサイズのばらつき。</summary>
public struct DetectionTrackStats
{
    public int Count;
    public float RawCenterStd, OutCenterStd; // 中心の標準偏差 [m]（3 軸合成）
    public Vector3 RawSizeCv, OutSizeCv;     // 幅・高さ・奥行きの 標準偏差 / 平均
    public Vector3 MeanRawSize;
}

/// <summary>
/// フレームをまたいで検出を同じ物体に対応づけ、位置とサイズを平滑化し、安定したら固定する。
/// </summary>
public class DetectionTracker
{
    private readonly DetectionTrackerSettings _s;
    private readonly List<DetectionTrack> _tracks = new();
    private readonly List<(float distance, int track, int measurement)> _pairs = new();
    private readonly List<float> _scratch = new();
    private int _nextId = 1;

    public IReadOnlyList<DetectionTrack> Tracks => _tracks;

    public DetectionTracker(DetectionTrackerSettings settings) => _s = settings;

    /// <summary>追跡をやり直す。label を指定するとそのラベルだけ。</summary>
    public void Reset(string label = null)
    {
        if (string.IsNullOrEmpty(label)) _tracks.Clear();
        else _tracks.RemoveAll(t => string.Equals(t.Label, label, StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>1 回の推論で得られた検出を取り込む。</summary>
    public void Update(List<LocatedBox> measurements, float now)
    {
        foreach (var t in _tracks) t.Matched = false;

        // 同じラベルで近いもの同士を、近い順に 1 対 1 で対応づける
        _pairs.Clear();
        for (int ti = 0; ti < _tracks.Count; ti++)
        {
            for (int mi = 0; mi < measurements.Count; mi++)
            {
                if (_tracks[ti].Label != measurements[mi].Label) continue;
                float d = Vector3.Distance(_tracks[ti].Center, measurements[mi].Center);
                if (d < Gate(_tracks[ti])) _pairs.Add((d, ti, mi));
            }
        }
        _pairs.Sort((a, b) => a.distance.CompareTo(b.distance));

        var used = new bool[measurements.Count];
        foreach (var (_, ti, mi) in _pairs)
        {
            if (_tracks[ti].Matched || used[mi]) continue;
            _tracks[ti].Matched = true;
            used[mi] = true;
            Apply(_tracks[ti], measurements[mi], now);
        }

        int existing = _tracks.Count;
        for (int mi = 0; mi < measurements.Count; mi++)
        {
            if (used[mi]) continue;
            var m = measurements[mi];

            // 対応済みの物体のすぐ近くに出た同じラベルの検出は、同じ物体の重複とみなして捨てる
            bool duplicate = false;
            for (int ti = 0; ti < existing && !duplicate; ti++)
            {
                var t = _tracks[ti];
                duplicate = t.Matched && t.Label == m.Label && Vector3.Distance(t.Center, m.Center) < Gate(t);
            }
            if (duplicate) continue;

            var track = new DetectionTrack
            {
                Id = _nextId++,
                Label = m.Label,
                Center = m.Center,
                Rotation = m.Rotation,
                Size = m.Size,
                Matched = true,
            };
            _tracks.Add(track);
            Apply(track, m, now);
        }
    }

    /// <summary>
    /// 毎フレーム呼ぶ。視界に入っているのに検出されない時間を数え、長く見失った物体を消す。
    /// </summary>
    public void Tick(float deltaTime, Func<Vector3, bool> isInView)
    {
        for (int i = _tracks.Count - 1; i >= 0; i--)
        {
            var t = _tracks[i];
            if (isInView(t.Center)) t.UnseenTime += deltaTime;
            if (t.UnseenTime > (t.IsLocked ? _s.lockedForgetAfterSeconds : _s.forgetAfterSeconds))
                _tracks.RemoveAt(i);
        }
    }

    private float Gate(DetectionTrack t) =>
        Mathf.Max(_s.matchDistance, 0.5f * Mathf.Max(t.Size.x, t.Size.z));

    private void Apply(DetectionTrack t, LocatedBox m, float now)
    {
        t.Hits++;
        t.UnseenTime = 0f;
        t.Score = m.Score;
        t.Method = m.Method;
        if (t.Hits >= _s.confirmAfterHits) t.IsConfirmed = true;

        if (t.IsLocked)
        {
            // 固定中は動かさない。ずれた検出が続いたら「物体が動いた」とみなして解除する
            t.MovedCount = Vector3.Distance(m.Center, t.Center) > _s.unlockDistance ? t.MovedCount + 1 : 0;
            if (t.MovedCount >= _s.unlockAfterDetections)
            {
                t.IsLocked = false;
                t.MovedCount = 0;
                t.StableCount = 0;
                t.RecentCenters.Clear();
                t.RecentSizes.Clear();
                t.Samples.Clear();
                t.Center = m.Center;
                t.Rotation = m.Rotation;
                t.Size = m.Size;
            }
            else
            {
                Record(t, m, now);
                return;
            }
        }

        Push(t.RecentCenters, m.Center);
        Push(t.RecentSizes, m.Size);

        if (t.Hits > 1)
        {
            bool stable = Vector3.Distance(m.Center, t.Center) < _s.stableDistance &&
                          IsSizeStable(m.Size, t.Size);
            t.StableCount = stable ? t.StableCount + 1 : 0;

            float k = 1f - _s.smoothing;
            t.Center = Vector3.Lerp(t.Center, Median(t.RecentCenters), k);
            t.Size = Vector3.Lerp(t.Size, Median(t.RecentSizes), k);
            t.Rotation = Quaternion.Slerp(t.Rotation, m.Rotation, k);
        }

        if (_s.lockAfterStableDetections > 0 && t.StableCount >= _s.lockAfterStableDetections)
            t.IsLocked = true;

        Record(t, m, now);
    }

    private void Push(List<Vector3> list, Vector3 v)
    {
        list.Add(v);
        while (list.Count > Mathf.Max(1, _s.medianWindow)) list.RemoveAt(0);
    }

    private Vector3 Median(List<Vector3> values)
    {
        Vector3 result = default;
        for (int axis = 0; axis < 3; axis++)
        {
            _scratch.Clear();
            foreach (var v in values) _scratch.Add(v[axis]);
            _scratch.Sort();
            int mid = _scratch.Count / 2;
            result[axis] = _scratch.Count % 2 == 1 ? _scratch[mid] : (_scratch[mid - 1] + _scratch[mid]) * 0.5f;
        }
        return result;
    }

    /// <summary>各軸の差が「割合」か「長さ」のどちらかの許容範囲に入っていれば安定。</summary>
    private bool IsSizeStable(Vector3 a, Vector3 b)
    {
        for (int i = 0; i < 3; i++)
        {
            float diff = Mathf.Abs(a[i] - b[i]);
            if (diff > Mathf.Max(_s.stableSizeRatio * b[i], _s.stableSizeAbs)) return false;
        }
        return true;
    }

    // ---------------------------------------------------------------- 計測

    private void Record(DetectionTrack t, LocatedBox m, float now)
    {
        t.Samples.Add(new DetectionTrack.Sample
        {
            Time = now, RawCenter = m.Center, RawSize = m.Size, OutCenter = t.Center, OutSize = t.Size,
        });
        while (t.Samples.Count > 0 && now - t.Samples[0].Time > _s.statsWindowSeconds) t.Samples.RemoveAt(0);
    }

    /// <summary>直近 statsWindowSeconds 秒の、生の値 (Raw) と平滑化後 (Out) のばらつき。</summary>
    public DetectionTrackStats GetStats(DetectionTrack t)
    {
        var stats = new DetectionTrackStats { Count = t.Samples.Count };
        if (stats.Count < 2) return stats;

        Vector3 rawC = default, rawS = default, outC = default, outS = default;
        foreach (var s in t.Samples) { rawC += s.RawCenter; rawS += s.RawSize; outC += s.OutCenter; outS += s.OutSize; }
        rawC /= stats.Count; rawS /= stats.Count; outC /= stats.Count; outS /= stats.Count;

        Vector3 rawCv = default, rawSv = default, outCv = default, outSv = default;
        foreach (var s in t.Samples)
        {
            rawCv += Sq(s.RawCenter - rawC); rawSv += Sq(s.RawSize - rawS);
            outCv += Sq(s.OutCenter - outC); outSv += Sq(s.OutSize - outS);
        }
        float n = stats.Count - 1;
        stats.RawCenterStd = Mathf.Sqrt((rawCv.x + rawCv.y + rawCv.z) / n);
        stats.OutCenterStd = Mathf.Sqrt((outCv.x + outCv.y + outCv.z) / n);
        stats.RawSizeCv = Cv(rawSv / n, rawS);
        stats.OutSizeCv = Cv(outSv / n, outS);
        stats.MeanRawSize = rawS;
        return stats;
    }

    private static Vector3 Sq(Vector3 v) => Vector3.Scale(v, v);

    private static Vector3 Cv(Vector3 variance, Vector3 mean) => new(
        Mathf.Sqrt(variance.x) / Mathf.Max(mean.x, 1e-4f),
        Mathf.Sqrt(variance.y) / Mathf.Max(mean.y, 1e-4f),
        Mathf.Sqrt(variance.z) / Mathf.Max(mean.z, 1e-4f));
}
