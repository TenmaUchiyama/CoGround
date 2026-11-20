using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 人の位置を表す目印。CoGroundPeopleReporter が、有効なものすべてを people.update で送る。
/// 家庭ルール R4「子供が 5 m 以内にいる間は、台車を止める」に使う。
///
/// ■ 使い方
///   人の位置になる Transform に付ける (シミュレーションなら人の代わりの物体、Quest なら頭 = カメラなど)。
///   Kind が Unknown の人が近くにいると、サーバーは「子供かどうか分からない」として台車を止める。
/// </summary>
public class CoGroundPerson : MonoBehaviour
{
    public enum PersonKind { Unknown, Child, Adult }

    [Tooltip("人物の ID。空なら GameObject の名前")]
    [SerializeField] string personId = "";
    [SerializeField] PersonKind kind = PersonKind.Child;

    static readonly List<CoGroundPerson> all = new List<CoGroundPerson>();
    /// <summary>有効な CoGroundPerson すべて</summary>
    public static IReadOnlyList<CoGroundPerson> All => all;

    public string Id => string.IsNullOrWhiteSpace(personId) ? name : personId.Trim();
    public PersonKind Kind { get => kind; set => kind = value; }
    /// <summary>サーバーに送る値 (child / adult / unknown)</summary>
    public string KindName => kind == PersonKind.Child ? "child" : kind == PersonKind.Adult ? "adult" : "unknown";

    void OnEnable() => all.Add(this);
    void OnDisable() => all.Remove(this);

#if UNITY_EDITOR
    void OnDrawGizmos()
    {
        Gizmos.color = kind == PersonKind.Child ? new Color(1f, 0.4f, 0.7f) : kind == PersonKind.Adult ? new Color(0.4f, 0.7f, 1f) : Color.gray;
        var p = transform.position;
        Gizmos.DrawWireSphere(new Vector3(p.x, 0.02f, p.z), 0.2f);
        UnityEditor.Handles.Label(p + Vector3.up * 0.1f, $"{Id} ({KindName})");
    }
#endif
}
