using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

/// <summary>
/// VR で置いた箱 (置き場所の候補) の一覧。EnvironmentBoxPlacer が書き込む。
/// Editor ではこのアセットを選び、Boxes の Name に名前 (trash_bin など) を入れる。あとでルールの行き先に使う。
///
/// ■ 位置の基準
///   箱の位置と向きは「部屋の基準」から見た値で持つ。部屋の基準は MRUK の部屋の床のアンカー
///   (位置 = 床のアンカーの位置、向き = 床のアンカーを水平にした向き)。
///   Unity のワールド座標は起動のたびにずれることがあるが、部屋の床のアンカーは同じ部屋なら変わらないので、
///   箱は部屋の同じ場所に戻る。MRUK の部屋が無いときは、基準はワールドの原点になる。
///   Origin Position / Origin Yaw は、最後に保存したときの基準のワールド姿勢 (Editor で枠を描くために使う)。
/// </summary>
[CreateAssetMenu(menuName = "CoGround/Environment Box Layout", fileName = "EnvironmentBoxes")]
public class EnvironmentBoxLayout : ScriptableObject
{
    [Serializable]
    public class Box
    {
        [Tooltip("Editor で付ける名前 (例: trash_bin)。空なら「box 番号」で表示する")]
        public string name = "";
        [Tooltip("置き場所の種類。入れ物は storage_box か trash_bin、上に置く面は table か shelf")]
        public CoGroundCategory category = CoGroundCategory.storage_box;
        [Tooltip("箱の中心 (部屋の基準から見た位置。y は床からの高さ) [m]")]
        public Vector3 position;
        [Tooltip("箱の向き (部屋の基準から見た、真上まわりの角度) [deg]")]
        public float yaw;
        [Tooltip("箱の大きさ (左右, 高さ, 前後) [m]")]
        public Vector3 size = new Vector3(0.3f, 0.3f, 0.3f);
    }

    [Tooltip("保存したときの MRUK の部屋の ID (部屋が無かったら空)")]
    public string roomUuid = "";
    [Tooltip("最後に保存したときの、部屋の基準のワールド位置")]
    public Vector3 originPosition;
    [Tooltip("最後に保存したときの、部屋の基準のワールドでの向き [deg]")]
    public float originYaw;
    public List<Box> boxes = new List<Box>();

    /// <summary>表示用の名前 (名前が空なら「box 番号」)</summary>
    public string LabelOf(int index)
    {
        if (index < 0 || index >= boxes.Count) return "";
        var n = boxes[index].name;
        return string.IsNullOrWhiteSpace(n) ? $"box {index + 1}" : n.Trim();
    }

    static string DevicePath => Path.Combine(Application.persistentDataPath, "environment_boxes.json");

    /// <summary>実機のアプリだけ: 前に実機で保存した一覧があれば、それで上書きする (エディタでは何もしない)</summary>
    public void LoadDeviceCopy()
    {
#if !UNITY_EDITOR
        if (File.Exists(DevicePath)) JsonUtility.FromJsonOverwrite(File.ReadAllText(DevicePath), this);
#endif
    }

    /// <summary>一覧を残す。エディタではこのアセットに、実機のアプリでは JSON に書く</summary>
    public void Persist()
    {
#if UNITY_EDITOR
        UnityEditor.EditorUtility.SetDirty(this);
        UnityEditor.AssetDatabase.SaveAssetIfDirty(this);
#else
        File.WriteAllText(DevicePath, JsonUtility.ToJson(this, true));
#endif
    }

    /// <summary>部屋の基準から見た姿勢を、ワールドの姿勢に直す</summary>
    public static void ToWorld(Vector3 originPosition, float originYaw, Vector3 position, float yaw,
        out Vector3 worldPosition, out Quaternion worldRotation)
    {
        worldPosition = originPosition + Quaternion.Euler(0f, originYaw, 0f) * position;
        worldRotation = Quaternion.Euler(0f, originYaw + yaw, 0f);
    }

    /// <summary>ワールドの姿勢を、部屋の基準から見た姿勢に直す</summary>
    public static void ToLocal(Vector3 originPosition, float originYaw, Vector3 worldPosition, float worldYaw,
        out Vector3 position, out float yaw)
    {
        position = Quaternion.Euler(0f, -originYaw, 0f) * (worldPosition - originPosition);
        yaw = Mathf.DeltaAngle(originYaw, worldYaw);
    }
}
