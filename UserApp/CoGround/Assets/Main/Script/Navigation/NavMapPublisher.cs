using System.Collections.Generic;
using RosMessageTypes.BuiltinInterfaces;
using RosMessageTypes.Geometry;
using RosMessageTypes.Nav;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

/// <summary>
/// 床 (Plane など) を move_base の地図 (global map) にして ROS に送る。
///
///   このスクリプト ──/coground/nav/map_unity (OccupancyGrid)──▶ base_command_server ──/coground/nav/map──▶ move_base (static_layer)
///
///   - 床のコライダーの上 = 通れる (0)。床の外・床の穴 = 通れない (100)
///   - 床の上で、床から obstacleHeight の高さにコライダーがあるマス = 通れない (100)
///     (机・棚・MoveItCollisionBox の箱など。ロボット自身と、つかんでいる MoveItPickable は除く)
///   - 台車の大きさ分の膨らませは move_base (robot_radius + inflation) がやるので、ここでは膨らませない
///
/// 床にする GameObject (Plane) に付ける。床が複数あるなら floors に並べる (どれか 1 つに付ければよい)。
/// checkSeconds ごとに作り直し、変わっていたら送る。変わらなくても heartbeatSeconds ごとに送る
/// (ROS 側を後から起動・再起動した場合のため)。
/// </summary>
public class NavMapPublisher : MonoBehaviour
{
    const string Topic = "/coground/nav/map_unity";

    [Header("床")]
    [Tooltip("床のコライダー。空ならこの GameObject (と子) のコライダー")]
    [SerializeField] Collider[] floors;
    [Tooltip("地図の 1 マス [m]。local costmap と同じ 0.05 が無難")]
    [SerializeField] float resolution = 0.05f;

    [Header("障害物 (床からの高さ)")]
    [Tooltip("床からこの高さの範囲にあるコライダーを障害物とみなす [m]")]
    [SerializeField] Vector2 obstacleHeight = new Vector2(0.05f, 1.6f);
    [SerializeField] LayerMask obstacleMask = ~0;
    [Tooltip("ロボット (このTransform 以下は障害物にしない)。未設定なら RosJointToFetch を探す")]
    [SerializeField] Transform robot;

    [Header("送信")]
    [SerializeField] float checkSeconds = 1f;
    [SerializeField] float heartbeatSeconds = 10f;

    [Header("表示")]
    [SerializeField] bool drawGizmos = true;

    ROSConnection ros;
    float nextCheck, nextHeartbeat;
    readonly Collider[] hits = new Collider[64];
    readonly HashSet<Collider> floorSet = new HashSet<Collider>();

    // 直前に作った地図 (ROS の world 座標: x = Unity z, y = -Unity x)
    sbyte[] data;
    int width, height;
    float originX, originY, floorTopY;

    void Start()
    {
        if (robot == null)
        {
            var r = FindAnyObjectByType<RosJointToFetch>();
            if (r != null) robot = r.transform;
            else Debug.LogWarning("[NavMapPublisher] ロボットが見つからない。ロボット自身も障害物として地図に入る");
        }

        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<OccupancyGridMsg>(Topic);

        if (floors == null || floors.Length == 0) floors = GetComponentsInChildren<Collider>();
        if (floors.Length == 0)
        {
            // MrukSceneColliders などが後から SetFloors で床を渡すまで待つ
            Debug.LogWarning("[NavMapPublisher] 床のコライダーがない。SetFloors で渡されるまで地図を送らない");
            enabled = false;
            return;
        }
        floorSet.UnionWith(floors);
    }

    /// <summary>床を入れ替える (MRUK の部屋を読み込んだ後など、実行中に床が決まる場合)。空を渡すと送信を止める</summary>
    public void SetFloors(IEnumerable<Collider> newFloors)
    {
        floors = new List<Collider>(newFloors).ToArray();
        floorSet.Clear();
        floorSet.UnionWith(floors);
        data = null;      // 次の Update で必ず作り直して送る
        nextCheck = 0f;
        enabled = floors.Length > 0;
    }

    void Update()
    {
        if (Time.time < nextCheck) return;
        nextCheck = Time.time + checkSeconds;

        var old = data;
        int oldW = width, oldH = height;
        float oldX = originX, oldY = originY;
        Build();

        bool changed = old == null || oldW != width || oldH != height || oldX != originX || oldY != originY
                       || !SameData(old, data);
        if (changed || Time.time >= nextHeartbeat)
        {
            Publish();
            nextHeartbeat = Time.time + heartbeatSeconds;
        }
    }

    /// <summary>今すぐ作り直して送る (床や障害物を動かした直後に呼んでもよい)</summary>
    public void PublishNow()
    {
        Build();
        Publish();
        nextHeartbeat = Time.time + heartbeatSeconds;
    }

    void Build()
    {
        // 床全体を囲む範囲 (ROS の x, y)。外周に 1 マスの「通れない」縁を付ける
        var b = floors[0].bounds;
        foreach (var f in floors) b.Encapsulate(f.bounds);
        floorTopY = b.max.y;

        float xMin = b.min.z - resolution, xMax = b.max.z + resolution;   // ROS x = Unity z
        float yMin = -b.max.x - resolution, yMax = -b.min.x + resolution; // ROS y = -Unity x
        originX = Mathf.Floor(xMin / resolution) * resolution;
        originY = Mathf.Floor(yMin / resolution) * resolution;
        width = Mathf.CeilToInt((xMax - originX) / resolution);
        height = Mathf.CeilToInt((yMax - originY) / resolution);
        if (data == null || data.Length != width * height) data = new sbyte[width * height];

        float rayTop = b.max.y + 1f;
        float rayLength = b.size.y + 2f;
        float bandCenter = (obstacleHeight.x + obstacleHeight.y) * 0.5f;
        var half = new Vector3(resolution * 0.5f, (obstacleHeight.y - obstacleHeight.x) * 0.5f, resolution * 0.5f);

        for (int j = 0; j < height; j++)
        for (int i = 0; i < width; i++)
        {
            float rx = originX + (i + 0.5f) * resolution;
            float ry = originY + (j + 0.5f) * resolution;
            float ux = -ry, uz = rx;

            // 床があるか (いちばん高い床面を使う)
            var ray = new Ray(new Vector3(ux, rayTop, uz), Vector3.down);
            bool onFloor = false;
            float floorY = float.NegativeInfinity;
            foreach (var f in floors)
            {
                if (f != null && f.enabled && f.Raycast(ray, out var hit, rayLength) && hit.point.y > floorY)
                {
                    floorY = hit.point.y;
                    onFloor = true;
                }
            }

            sbyte v = 100;
            if (onFloor)
            {
                var center = new Vector3(ux, floorY + bandCenter, uz);
                int n = Physics.OverlapBoxNonAlloc(center, half, hits, Quaternion.identity, obstacleMask,
                                                   QueryTriggerInteraction.Ignore);
                v = 0;
                for (int k = 0; k < n; k++)
                {
                    if (IsObstacle(hits[k])) { v = 100; break; }
                }
            }
            data[j * width + i] = v;
        }
    }

    bool IsObstacle(Collider c)
    {
        if (floorSet.Contains(c)) return false;
        if (robot != null && c.transform.IsChildOf(robot)) return false;
        var pickable = c.GetComponentInParent<MoveItPickable>();
        if (pickable != null && pickable.IsAttached) return false; // つかんでいる物はロボットと一緒に動く
        return true;
    }

    void Publish()
    {
        if (ros == null || data == null) return;
        var msg = new OccupancyGridMsg
        {
            header = new HeaderMsg { frame_id = "world" },
            info = new MapMetaDataMsg
            {
                map_load_time = new TimeMsg(),
                resolution = resolution,
                width = (uint)width,
                height = (uint)height,
                origin = new PoseMsg
                {
                    position = new PointMsg(originX, originY, 0),
                    orientation = new QuaternionMsg(0, 0, 0, 1),
                },
            },
            data = (sbyte[])data.Clone(),
        };
        ros.Publish(Topic, msg);
    }

    static bool SameData(sbyte[] a, sbyte[] b)
    {
        if (a == null || b == null || a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }

    void OnDrawGizmosSelected()
    {
        if (!drawGizmos || data == null) return;
        var size = new Vector3(resolution, 0.01f, resolution);
        Gizmos.color = new Color(1f, 0.2f, 0.2f, 0.6f);
        for (int j = 0; j < height; j++)
        for (int i = 0; i < width; i++)
        {
            if (data[j * width + i] == 0) continue;
            float rx = originX + (i + 0.5f) * resolution;
            float ry = originY + (j + 0.5f) * resolution;
            Gizmos.DrawCube(new Vector3(-ry, floorTopY + 0.01f, rx), size);
        }
    }
}
