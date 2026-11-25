using System.IO;
using UnityEngine;

/// <summary>
/// Gaussian Splatting のモデルを部屋に合わせるためのオフセット。SplatOffsetPlacer が書き込む。
///
/// ■ 位置の基準
///   EnvironmentBoxLayout の箱と同じ「部屋の基準」(MRUK の部屋の床のアンカー) から見た値で持つ。
///   だから起動のたびにワールド座標がずれても、スプラットは部屋の同じ場所 (机に重なる位置) に戻る。
///   回転は真上まわりだけでなく全部持つ (スキャンの上下の向きを直すため)。大きさは縦横高さそろえた 1 つの倍率。
/// </summary>
[CreateAssetMenu(menuName = "CoGround/Splat Offset", fileName = "SplatOffset")]
public class SplatOffset : ScriptableObject
{
    [Tooltip("一度でも保存したか (false のあいだは、シーンに置いたままの位置を使う)")]
    public bool saved;
    [Tooltip("部屋の基準から見た位置 [m]")]
    public Vector3 position;
    [Tooltip("部屋の基準から見た回転")]
    public Quaternion rotation = Quaternion.identity;
    [Tooltip("大きさの倍率")]
    public float scale = 1f;

    [Tooltip("保存したときの MRUK の部屋の ID (部屋が無かったら空)")]
    public string roomUuid = "";
    [Tooltip("最後に保存したときの、部屋の基準のワールド位置")]
    public Vector3 originPosition;
    [Tooltip("最後に保存したときの、部屋の基準のワールドでの向き [deg]")]
    public float originYaw;

    static string DevicePath => Path.Combine(Application.persistentDataPath, "splat_offset.json");

    /// <summary>実機のアプリだけ: 前に実機で保存した値があれば、それで上書きする (エディタでは何もしない)</summary>
    public void LoadDeviceCopy()
    {
#if !UNITY_EDITOR
        if (File.Exists(DevicePath)) JsonUtility.FromJsonOverwrite(File.ReadAllText(DevicePath), this);
#endif
    }

    /// <summary>値を残す。エディタではこのアセットに、実機のアプリでは JSON に書く</summary>
    public void Persist()
    {
#if UNITY_EDITOR
        UnityEditor.EditorUtility.SetDirty(this);
        UnityEditor.AssetDatabase.SaveAssetIfDirty(this);
#else
        File.WriteAllText(DevicePath, JsonUtility.ToJson(this, true));
#endif
    }

    /// <summary>部屋の基準のワールド姿勢から、スプラットのワールド姿勢を出す</summary>
    public void ToWorld(Vector3 originPos, float originYawDeg, out Vector3 worldPosition, out Quaternion worldRotation)
    {
        var o = Quaternion.Euler(0f, originYawDeg, 0f);
        worldPosition = originPos + o * position;
        worldRotation = o * rotation;
    }

    /// <summary>スプラットのワールド姿勢を、部屋の基準から見た値にして持つ</summary>
    public void FromWorld(Vector3 originPos, float originYawDeg, Vector3 worldPosition, Quaternion worldRotation)
    {
        var inv = Quaternion.Inverse(Quaternion.Euler(0f, originYawDeg, 0f));
        position = inv * (worldPosition - originPos);
        rotation = inv * worldRotation;
    }
}
