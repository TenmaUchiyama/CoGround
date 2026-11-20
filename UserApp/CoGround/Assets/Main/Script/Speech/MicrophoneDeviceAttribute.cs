using UnityEngine;

/// <summary>
/// string フィールドに付けると、Inspector で接続中のマイク一覧からドロップダウンで選べるようになる。
/// 描画は Editor/MicrophoneDeviceDrawer.cs。
/// </summary>
public class MicrophoneDeviceAttribute : PropertyAttribute
{
}
