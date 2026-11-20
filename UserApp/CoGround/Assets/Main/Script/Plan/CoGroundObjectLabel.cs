using UnityEngine;

/// <summary>物体に追従するテキストと引き出し線。サーバー通信には依存しない。</summary>
public class CoGroundObjectLabel : MonoBehaviour
{
    [SerializeField] TextMesh label;
    [SerializeField] LineRenderer leader;
    [SerializeField] Transform target;
    [SerializeField] Vector3 offset = new Vector3(0.12f, 0.22f, 0);
    [SerializeField] Font font;
    [SerializeField, Min(0.001f)] float lineWidth = 0.002f;

    Vector3 fallbackAnchor;
    Material lineMaterial;
    Color tint = Color.white;

    void Awake()
    {
        fallbackAnchor = transform.position;
        if (font == null) font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        label.font = font;
        label.GetComponent<MeshRenderer>().sharedMaterial = font.material;
        leader.useWorldSpace = true;
        leader.positionCount = 2;
        leader.startWidth = leader.endWidth = lineWidth;
        leader.numCapVertices = 4;
        leader.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        leader.receiveShadows = false;
        lineMaterial = FetchGhost.MakeMaterial(Color.white);
        leader.sharedMaterial = lineMaterial;
        SetColor(tint);
    }

    public void Bind(Transform objectTransform, Vector3 position, string text, Color color, float characterSize)
    {
        target = objectTransform;
        fallbackAnchor = position;
        label.text = text;
        label.characterSize = characterSize;
        SetColor(color);
        Refresh();
    }

    public void SetColor(Color color)
    {
        tint = color;
        label.color = color;
        if (lineMaterial != null) lineMaterial.color = color;
    }

    void LateUpdate() => Refresh();

    void Refresh()
    {
        var anchor = target != null ? target.position : fallbackAnchor;
        // Collider がある場合は、原点でなく物体の中心から線を出す。
        if (target != null && target.TryGetComponent<Collider>(out var collider))
            anchor = collider.bounds.center;
        transform.position = anchor;
        label.transform.position = anchor + offset;
        var cam = Camera.main;
        if (cam != null)
        {
            var direction = label.transform.position - cam.transform.position;
            if (direction.sqrMagnitude > 0.000001f)
                label.transform.rotation = Quaternion.LookRotation(direction, cam.transform.up);
        }
        leader.SetPosition(0, anchor);
        leader.SetPosition(1, label.transform.position);
    }

    void OnDestroy()
    {
        if (lineMaterial != null) Destroy(lineMaterial);
    }
}
