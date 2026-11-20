using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 床の上の格子で A* を解き、台車が通れる道 (折れ線) を作る。地図は持たず、Unity のコライダーをその場で調べる。
///
///   - 格子の各マスで「台車の円柱 (半径 RobotRadius、高さ MinHeight〜MaxHeight)」が何かに当たるかを調べる
///     (床より少し上から調べるので床自体は当たらない。Ignore 以下のコライダー = ロボット自身は無視する)
///   - 8 近傍の A* (斜めは角をすり抜けない) → 見通しの利く点を飛ばして折れ線を短くする
///   - 格子は始点と終点を囲む範囲 + SearchMargin だけ。マスは必要になったときに調べる
/// </summary>
public class BaseNavPlanner
{
    public float RobotRadius = 0.35f;
    public float CellSize = 0.1f;
    /// <summary>台車の底から何 m 上を障害物として見るか (床を拾わないように少し上から)</summary>
    public float MinHeight = 0.05f;
    public float MaxHeight = 1.6f;
    public float SearchMargin = 3f;
    public int MaxCells = 200 * 200;
    public LayerMask Mask = ~0;
    /// <summary>このTransform 以下のコライダーは障害物にしない (ロボット自身)</summary>
    public Transform Ignore;

    // 直前の計画の格子 (Gizmo 表示用)
    Vector3 origin;
    int nx, nz;
    float baseY;
    sbyte[] cells; // 0 = 未調査, 1 = 通れる, 2 = ぶつかる
    readonly Collider[] hits = new Collider[256];

    public bool TryPlan(Vector3 start, Vector3 goal, List<Vector3> result, out string error)
    {
        result.Clear();
        error = null;
        baseY = start.y;
        goal.y = baseY;

        var min = Vector3.Min(start, goal) - new Vector3(SearchMargin, 0f, SearchMargin);
        var max = Vector3.Max(start, goal) + new Vector3(SearchMargin, 0f, SearchMargin);
        origin = new Vector3(min.x, baseY, min.z);
        nx = Mathf.CeilToInt((max.x - min.x) / CellSize);
        nz = Mathf.CeilToInt((max.z - min.z) / CellSize);
        if (nx * nz > MaxCells) { error = "Goal is too far"; return false; }
        cells = new sbyte[nx * nz];

        if (!Free(goal)) { error = "The base doesn't fit at the goal (too close to obstacles)"; return false; }

        int s = CellOf(start), g = CellOf(goal);
        cells[s] = 1; // 今いる場所は通れることにする (机に近づいて止まっている場合など)

        // 直接行けるならそれで終わり
        if (LineFree(start, goal))
        {
            result.Add(start);
            result.Add(goal);
            return true;
        }

        var cellPath = AStar(s, g);
        if (cellPath == null) { error = "No passable path to the goal"; return false; }

        var raw = new List<Vector3> { start };
        for (int i = 1; i < cellPath.Count - 1; i++) raw.Add(CenterOf(cellPath[i]));
        raw.Add(goal);

        // 見通しの利く限り先の点へ飛ぶ
        result.Add(raw[0]);
        int k = 0;
        while (k < raw.Count - 1)
        {
            int j = raw.Count - 1;
            while (j > k + 1 && !LineFree(raw[k], raw[j])) j--;
            result.Add(raw[j]);
            k = j;
        }
        return true;
    }

    List<int> AStar(int start, int goal)
    {
        int n = nx * nz;
        var gScore = new float[n];
        var parent = new int[n];
        var closed = new bool[n];
        for (int i = 0; i < n; i++) { gScore[i] = float.PositiveInfinity; parent[i] = -1; }
        gScore[start] = 0f;
        var open = new MinHeap();
        open.Push(Heuristic(start, goal), start);

        while (open.Count > 0)
        {
            int cur = open.Pop();
            if (closed[cur]) continue;
            if (cur == goal)
            {
                var path = new List<int>();
                for (int c = goal; c != -1; c = parent[c]) path.Add(c);
                path.Reverse();
                return path;
            }
            closed[cur] = true;
            int cx = cur % nx, cz = cur / nx;
            for (int dz = -1; dz <= 1; dz++)
            for (int dx = -1; dx <= 1; dx++)
            {
                if (dx == 0 && dz == 0) continue;
                int x = cx + dx, z = cz + dz;
                if (x < 0 || z < 0 || x >= nx || z >= nz) continue;
                int next = z * nx + x;
                if (closed[next] || !Free(next)) continue;
                if (dx != 0 && dz != 0 && (!Free(cz * nx + x) || !Free(z * nx + cx))) continue; // 角をすり抜けない
                float cost = gScore[cur] + (dx != 0 && dz != 0 ? 1.41421356f : 1f);
                if (cost >= gScore[next]) continue;
                gScore[next] = cost;
                parent[next] = cur;
                open.Push(cost + Heuristic(next, goal), next);
            }
        }
        return null;
    }

    float Heuristic(int a, int b)
    {
        int dx = Mathf.Abs(a % nx - b % nx), dz = Mathf.Abs(a / nx - b / nx);
        return Mathf.Max(dx, dz) + 0.41421356f * Mathf.Min(dx, dz);
    }

    int CellOf(Vector3 p)
    {
        int x = Mathf.Clamp(Mathf.FloorToInt((p.x - origin.x) / CellSize), 0, nx - 1);
        int z = Mathf.Clamp(Mathf.FloorToInt((p.z - origin.z) / CellSize), 0, nz - 1);
        return z * nx + x;
    }

    Vector3 CenterOf(int cell) =>
        new Vector3(origin.x + (cell % nx + 0.5f) * CellSize, baseY, origin.z + (cell / nx + 0.5f) * CellSize);

    bool Free(Vector3 p) => Free(CellOf(p));

    bool Free(int cell)
    {
        if (cells[cell] == 0) cells[cell] = (sbyte)(Overlaps(CenterOf(cell)) ? 2 : 1);
        return cells[cell] == 1;
    }

    bool LineFree(Vector3 a, Vector3 b)
    {
        float dist = Vector3.Distance(a, b);
        int steps = Mathf.Max(1, Mathf.CeilToInt(dist / (CellSize * 0.5f)));
        for (int i = 0; i <= steps; i++)
            if (!Free(Vector3.Lerp(a, b, i / (float)steps))) return false;
        return true;
    }

    bool Overlaps(Vector3 center)
    {
        // マスの中心だけを調べるので、半マス分だけ余裕を持たせる
        float r = RobotRadius + CellSize * 0.5f;
        float low = MinHeight + r, high = Mathf.Max(MaxHeight - r, low);
        int count = Physics.OverlapCapsuleNonAlloc(center + Vector3.up * low, center + Vector3.up * high, r, hits, Mask,
                                                   QueryTriggerInteraction.Ignore);
        for (int i = 0; i < count; i++)
        {
            if (Ignore != null && hits[i].transform.IsChildOf(Ignore)) continue;
            return true;
        }
        return false;
    }

    /// <summary>直前の計画で調べたマス (赤 = ぶつかる) を Gizmo で描く</summary>
    public void DrawGizmos()
    {
        if (cells == null) return;
        var size = new Vector3(CellSize, 0.01f, CellSize) * 0.9f;
        for (int i = 0; i < cells.Length; i++)
        {
            if (cells[i] != 2) continue;
            Gizmos.color = new Color(1f, 0.2f, 0.2f, 0.5f);
            Gizmos.DrawCube(CenterOf(i), size);
        }
    }

    class MinHeap
    {
        readonly List<(float key, int value)> items = new List<(float, int)>();
        public int Count => items.Count;

        public void Push(float key, int value)
        {
            items.Add((key, value));
            int i = items.Count - 1;
            while (i > 0)
            {
                int p = (i - 1) / 2;
                if (items[p].key <= items[i].key) break;
                (items[p], items[i]) = (items[i], items[p]);
                i = p;
            }
        }

        public int Pop()
        {
            int top = items[0].value;
            int last = items.Count - 1;
            items[0] = items[last];
            items.RemoveAt(last);
            int i = 0;
            while (true)
            {
                int l = 2 * i + 1, r = l + 1, m = i;
                if (l < items.Count && items[l].key < items[m].key) m = l;
                if (r < items.Count && items[r].key < items[m].key) m = r;
                if (m == i) break;
                (items[m], items[i]) = (items[i], items[m]);
                i = m;
            }
            return top;
        }
    }
}
