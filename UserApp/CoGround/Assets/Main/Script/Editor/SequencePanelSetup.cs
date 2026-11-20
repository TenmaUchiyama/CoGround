using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// メニュー CoGround > シーケンス パネルを置く
/// 作業順序の確認・編集・実行のパネル (CoGroundSequencePanel) を、開いているシーンの Main Camera の正面に置く。
/// パネルの中身は Play のときに自分で組み立てるので、Prefab は作らない。
/// VR で押すには、置いた GameObject (Canvas) に ISDK の Ray / Poke を付ける (Before・After パネルと同じ)。
/// </summary>
public static class SequencePanelSetup
{
    const string PanelName = "SequencePanel";

    [MenuItem("CoGround/シーケンス パネルを置く")]
    public static void Place()
    {
        var old = GameObject.Find(PanelName);
        if (old != null) Object.DestroyImmediate(old);

        var go = new GameObject(PanelName, typeof(RectTransform), typeof(Canvas), typeof(UnityEngine.UI.CanvasScaler),
                                typeof(UnityEngine.UI.GraphicRaycaster), typeof(CoGroundSequencePanel));
        go.GetComponent<Canvas>().renderMode = RenderMode.WorldSpace;
        go.GetComponent<UnityEngine.UI.CanvasScaler>().dynamicPixelsPerUnit = 3;
        var rect = (RectTransform)go.transform;
        rect.sizeDelta = new Vector2(760, 600);
        rect.localScale = Vector3.one * 0.0005f; // 1 px = 0.5 mm → 幅 38 cm

        var cam = Camera.main;
        if (cam != null)
        {
            // カメラの 0.7 m 前、少し右。カメラの方を向ける (Canvas の表は -Z 側から見える)
            var forward = Vector3.ProjectOnPlane(cam.transform.forward, Vector3.up).normalized;
            if (forward.sqrMagnitude < 0.01f) forward = Vector3.forward;
            var right = Vector3.Cross(Vector3.up, forward);
            go.transform.position = cam.transform.position + forward * 0.7f + right * 0.35f;
            go.transform.rotation = Quaternion.LookRotation(forward, Vector3.up);
        }
        if (Object.FindAnyObjectByType<CoGroundAfterView>() == null)
            Debug.LogWarning("[SequencePanelSetup] このシーンに CoGroundAfterView が無い。時点ごとの予測 (Before / After 1 / …) は切り替わらない");
        Undo.RegisterCreatedObjectUndo(go, "シーケンス パネル");
        Selection.activeGameObject = go;
        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
    }
}
