using System;
using System.Collections;
using System.IO;
using Meta.XR.MRUtilityKit;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// いま読み込まれている MRUK の部屋 (Scene Data) を JSON ファイルに保存する。
///
///   - Quest: 右コントローラの A ボタン (button で変更可)。保存できたら短く振動する
///   - エディタ / PC: S キー、またはこのコンポーネントの右クリック メニュー「部屋を JSON に保存」
///
/// 保存先
///   - エディタ: Assets/Main/SceneData/room_日時.json (そのまま MRUK の Scene Jsons に入れられる)
///   - 実機    : Application.persistentDataPath/SceneData/room_日時.json
///               (Quest では /sdcard/Android/data/パッケージ名/files/SceneData/)
///
/// 保存した JSON は、MRUK の Data Source を Json にして Scene Jsons に入れるとエディタで読める。
/// </summary>
public class SceneDataSaver : MonoBehaviour
{
    [Tooltip("保存に使うコントローラのボタン (既定は右手の A)")]
    [SerializeField] OVRInput.Button button = OVRInput.Button.One;
    [Tooltip("S キーでも保存できるようにする (エディタ確認用)")]
    [SerializeField] bool allowKeyboard = true;
    [Tooltip("Global Mesh (部屋全体の三角形メッシュ) も入れる。ファイルが大きくなる")]
    [SerializeField] bool includeGlobalMesh = true;
    [SerializeField] string filePrefix = "room";

    /// <summary>最後に保存したファイルのパス (まだなら空)</summary>
    public string LastSavedPath { get; private set; } = "";

    void Update()
    {
        if (OVRInput.GetDown(button) || (allowKeyboard && SaveKeyDown())) Save();
    }

    /// <summary>今の部屋を JSON に保存する。保存したパスを返す (失敗したら null)</summary>
    [ContextMenu("部屋を JSON に保存")]
    public string Save()
    {
        if (MRUK.Instance == null || MRUK.Instance.Rooms == null || MRUK.Instance.Rooms.Count == 0)
        {
            Debug.LogWarning("[SceneDataSaver] 部屋がまだ読み込まれていない (Play 中に、部屋が出てから押すこと)");
            return null;
        }

        try
        {
            string json = MRUK.Instance.SaveSceneToJsonString(includeGlobalMesh);
            string dir = SaveDirectory();
            Directory.CreateDirectory(dir);
            string path = Path.Combine(dir, $"{filePrefix}_{DateTime.Now:yyyyMMdd_HHmmss}.json");
            File.WriteAllText(path, json);
            LastSavedPath = path;
            Debug.Log($"[SceneDataSaver] 保存した: {path} (部屋 {MRUK.Instance.Rooms.Count} 個、{json.Length / 1024} KB)");

#if UNITY_EDITOR
            UnityEditor.AssetDatabase.Refresh(); // Project ウィンドウにすぐ出す
#endif
            StartCoroutine(Pulse());
            return path;
        }
        catch (Exception e)
        {
            Debug.LogError($"[SceneDataSaver] 保存に失敗: {e.Message}");
            return null;
        }
    }

    static string SaveDirectory()
    {
#if UNITY_EDITOR
        return Path.Combine(Application.dataPath, "Main", "SceneData");
#else
        return Path.Combine(Application.persistentDataPath, "SceneData");
#endif
    }

    static bool SaveKeyDown()
    {
#if ENABLE_INPUT_SYSTEM
        return Keyboard.current != null && Keyboard.current.sKey.wasPressedThisFrame;
#else
        return Input.GetKeyDown(KeyCode.S);
#endif
    }

    IEnumerator Pulse()
    {
        OVRInput.SetControllerVibration(1f, 0.5f, OVRInput.Controller.RTouch);
        yield return new WaitForSecondsRealtime(0.15f);
        OVRInput.SetControllerVibration(0f, 0f, OVRInput.Controller.RTouch);
    }
}
