using UnityEditor;
using UnityEngine;

/// <summary>FetchRobotModeInfo のインスペクタ: 本物のロボットを使うときに無効にするコンポーネントの一覧と、今の状態</summary>
[CustomEditor(typeof(FetchRobotModeInfo))]
public class FetchRobotModeInfoEditor : Editor
{
    public override void OnInspectorGUI()
    {
        DrawDefaultInspector();
        var info = (FetchRobotModeInfo)target;

        EditorGUILayout.Space();
        EditorGUILayout.HelpBox(info.UseRealRobot
            ? "本物のロボット: Play 開始時にこの Fetch を隠し (当たり判定も切る)、下のコンポーネントを無効にする。"
            : "シミュレーション: この Fetch が本物の代わり。下のコンポーネントで ROS の値どおりに動く。",
            MessageType.Info);
        EditorGUILayout.LabelField("本物のロボットを使うときに無効にするもの", EditorStyles.boldLabel);

        foreach (var (type, reason) in FetchRobotModeInfo.DisableForRealRobot)
        {
            var c = info.GetComponent(type) as Behaviour;
            string state = c == null ? "付いていない" : c.enabled ? "有効" : "無効";
            EditorGUILayout.BeginHorizontal();
            EditorGUILayout.LabelField(type.Name, GUILayout.Width(170));
            EditorGUILayout.LabelField(state, EditorStyles.boldLabel, GUILayout.Width(80));
            EditorGUILayout.EndHorizontal();
            EditorGUILayout.LabelField(reason, EditorStyles.wordWrappedMiniLabel);
        }
        EditorGUILayout.LabelField("(状態はシーンに保存されている値。本物のロボットのときは Play 中だけ無効になる)", EditorStyles.miniLabel);
    }
}
