using Meta.XR;
using Meta.XR.EnvironmentDepth;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// メニュー CoGround > 検出 (Perception) を配置
/// 開いているシーン (ARRobotSim など) に、カメラで認識した物体を scene.update に入れる部品を置く。
///
///   PassthroughCameraAccess ─ RGB
///   EnvironmentDepthManager ─ 深度
///      ▼
///   CoGroundFrameSender      ─ POST /perception/frame (サーバーが検出して 3D にする)
///      ▼
///   CoGroundPerceivedObjects ─ CoGroundSceneReporter の Extra Sources に入り、scene.update で送られる
///
/// 何度実行してもよい (あるものは作り直さない)。
/// 送るボタンは左の X (A は SplatOffsetPlacer、B は SpeechTaskRequester が使う)。
/// Endpoint は CoGroundServerClient の接続先から作る (ws://host:port/ws → http://host:port)。
/// </summary>
public static class PerceptionSetup
{
    const string RootName = "Perception";
    const string Undo_ = "Perception Setup";

    [MenuItem("CoGround/検出 (Perception) を配置")]
    static void Setup()
    {
        var reporter = Object.FindAnyObjectByType<CoGroundSceneReporter>(FindObjectsInactive.Include);
        if (reporter == null)
        {
            EditorUtility.DisplayDialog("Perception", "CoGroundSceneReporter がシーンに無い。先に置いてから実行する", "OK");
            return;
        }

        // 1. 置き場所
        var sender = Object.FindAnyObjectByType<CoGroundFrameSender>(FindObjectsInactive.Include);
        GameObject root;
        if (sender != null) root = sender.gameObject;
        else
        {
            root = GameObject.Find(RootName);
            if (root == null)
            {
                root = new GameObject(RootName);
                Undo.RegisterCreatedObjectUndo(root, Undo_);
            }
        }

        // 2. カメラ (RGB) と深度
        var camera = Object.FindAnyObjectByType<PassthroughCameraAccess>(FindObjectsInactive.Include);
        if (camera == null)
        {
            camera = Undo.AddComponent<PassthroughCameraAccess>(root);
            var camSo = new SerializedObject(camera);
            var res = camSo.FindProperty("RequestedResolution");
            if (res != null) res.vector2IntValue = new Vector2Int(1280, 960); // ObjectDetection.unity と同じ
            camSo.ApplyModifiedProperties();
        }
        var depth = Object.FindAnyObjectByType<EnvironmentDepthManager>(FindObjectsInactive.Include);
        if (depth == null) depth = Undo.AddComponent<EnvironmentDepthManager>(root);

        // 3. フレームを送る
        if (sender == null) sender = Undo.AddComponent<CoGroundFrameSender>(root);
        var so = new SerializedObject(sender);
        so.FindProperty("cameraAccess").objectReferenceValue = camera;
        so.FindProperty("depthManager").objectReferenceValue = depth;
        var shader = Shader.Find("Hidden/CoGround/DepthCopy");
        if (shader != null) so.FindProperty("depthCopyShader").objectReferenceValue = shader;
        so.FindProperty("sendButton").intValue = (int)OVRInput.Button.Three; // 左 X
        var endpoint = HttpEndpointFromServerClient();
        if (endpoint != null) so.FindProperty("endpoint").stringValue = endpoint;
        so.ApplyModifiedProperties();

        // 4. 認識した物体を scene.update へ
        var perceived = root.GetComponent<CoGroundPerceivedObjects>();
        if (perceived == null) perceived = Object.FindAnyObjectByType<CoGroundPerceivedObjects>(FindObjectsInactive.Include);
        if (perceived == null) perceived = Undo.AddComponent<CoGroundPerceivedObjects>(root);
        var pso = new SerializedObject(perceived);
        pso.FindProperty("frameSender").objectReferenceValue = sender;
        pso.FindProperty("reporter").objectReferenceValue = reporter;
        pso.ApplyModifiedProperties();

        EditorSceneManager.MarkSceneDirty(root.scene);
        Selection.activeObject = root;
        Debug.Log($"[PerceptionSetup] {root.name} に PassthroughCameraAccess / EnvironmentDepthManager / CoGroundFrameSender (endpoint {so.FindProperty("endpoint").stringValue}, 左 X で送信) / CoGroundPerceivedObjects を置いた。シーンを保存すること", root);

        // 机 (place_zone 付きの CoGroundSceneObject) は Reporter が真値として送る。アクティブなものが無いと「机の上」が決まらない
        bool hasTable = false;
        foreach (var o in Object.FindObjectsByType<CoGroundSceneObject>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            if (o.isActiveAndEnabled) { hasTable = true; break; }
        if (!hasTable)
            Debug.LogWarning("[PerceptionSetup] アクティブな CoGroundSceneObject が無い。机 (place_zone 付き) を部屋の机に合わせて置かないと「机の上」の物体が決まらない", root);
        var mock = Object.FindAnyObjectByType<MockSimulatedObjects>(FindObjectsInactive.Exclude);
        if (mock != null && mock.isActiveAndEnabled)
            Debug.LogWarning("[PerceptionSetup] MockSimulatedObjects が有効。検出と両方の物体が送られるので、使わないなら無効にする", mock);
    }

    static string HttpEndpointFromServerClient()
    {
        var client = Object.FindAnyObjectByType<CoGroundServerClient>(FindObjectsInactive.Include);
        if (client == null) return null;
        var url = new SerializedObject(client).FindProperty("serverUrl")?.stringValue;
        if (string.IsNullOrEmpty(url) || !System.Uri.TryCreate(url, System.UriKind.Absolute, out var uri)) return null;
        var scheme = uri.Scheme == "wss" ? "https" : "http";
        return $"{scheme}://{uri.Host}:{uri.Port}";
    }
}
