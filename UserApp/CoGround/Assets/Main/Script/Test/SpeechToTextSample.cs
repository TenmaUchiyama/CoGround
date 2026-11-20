using UnityEngine;

/// <summary>
/// エディタ / PC 確認用の画面オーバーレイ (OnGUI)。Quest のヘッドセット内には表示されない。
/// 録音・送信は PushToTalkTranscriber、入力は PushToTalkControllerInput が行い、ここは
///   ・Game ビュー左上に状態と最新の認識結果
///   ・マイクの切り替え
/// を出すだけ。Quest 用の表示は SpeechToTextPanel。
/// </summary>
[RequireComponent(typeof(PushToTalkTranscriber))]
public class SpeechToTextSample : MonoBehaviour
{
    [SerializeField] private bool showOverlay = true;
    [SerializeField] private Font font;
    [SerializeField] private int fontSize = 20;

    PushToTalkTranscriber transcriber;
    string lastText = "";
    string lastMessage = "";
    bool showMicList;
    GUIStyle labelStyle, buttonStyle;

    void Awake()
    {
        transcriber = GetComponent<PushToTalkTranscriber>();
        transcriber.Transcribed += r => { lastText = r.IsEmpty ? "(Couldn't catch that)" : r.Text; lastMessage = ""; };
        transcriber.Failed += m => lastMessage = "⚠ " + m;
    }

    void OnGUI()
    {
        if (!showOverlay) return;
        if (labelStyle == null)
        {
            labelStyle = new GUIStyle(GUI.skin.label) { fontSize = fontSize, wordWrap = true, richText = true };
            buttonStyle = new GUIStyle(GUI.skin.button) { fontSize = fontSize, alignment = TextAnchor.MiddleLeft };
            if (font != null) labelStyle.font = buttonStyle.font = font;
        }

        GUILayout.BeginArea(new Rect(12, 12, Mathf.Min(560, Screen.width - 24), Screen.height - 24), GUI.skin.box);

        string state = transcriber.State switch
        {
            PushToTalkTranscriber.TalkState.Recording => $"<color=#ff5050>● Recording {transcriber.RecordingSeconds:0.0}s</color>",
            PushToTalkTranscriber.TalkState.Transcribing => "<color=#ffd040>Transcribing…</color>",
            _ => "<color=#80ff80>Idle</color>  Hold space / trigger to record",
        };
        GUILayout.Label(state, labelStyle);
        if (!string.IsNullOrEmpty(lastMessage)) GUILayout.Label(lastMessage, labelStyle);

        var recorder = transcriber.Recorder;
        GUI.enabled = !recorder.IsRecording;
        if (GUILayout.Button((showMicList ? "▼ " : "▶ ") + "Mic: " + recorder.EffectiveDeviceName, buttonStyle))
        {
            showMicList = !showMicList;
            if (showMicList) MicrophoneRecorder.RefreshDevices(); // 列挙は重いので開いたときだけ
        }
        if (showMicList)
        {
            if (GUILayout.Button((string.IsNullOrEmpty(recorder.DeviceName) ? "● " : "   ") + "(default microphone)", buttonStyle))
                Select("");
            foreach (var d in MicrophoneRecorder.Devices)
                if (GUILayout.Button((recorder.DeviceName == d ? "● " : "   ") + d, buttonStyle))
                    Select(d);
        }
        GUI.enabled = true;

        if (!string.IsNullOrEmpty(lastText)) GUILayout.Label(lastText, labelStyle);
        GUILayout.EndArea();
    }

    void Select(string device)
    {
        transcriber.Recorder.DeviceName = device;
        showMicList = false;
    }
}
