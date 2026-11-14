using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.Networking.PlayerConnection;
using UnityEngine;
using UnityEngine.Networking.PlayerConnection;


public class HelloWindow : EditorWindow {
    string lastAck = "-";
    CaptureRGB captureRGB;

    [MenuItem("Tools/Hello Remote")]
    static void Open() => GetWindow<HelloWindow>("Hello Remote");

    void OnEnable() {
        EditorConnection.instance.Initialize();
        EditorConnection.instance.Register(DebugMsg.Ack, OnAck);
        CaptureRGB[] buff = FindObjectsByType<CaptureRGB>(FindObjectsSortMode.None);

        if(buff.Length != 0)
        {
            captureRGB = buff[0];
        }
    }


    

    void OnDisable() => EditorConnection.instance.Unregister(DebugMsg.Ack, OnAck);

    void OnAck(MessageEventArgs e) {
        lastAck = Encoding.UTF8.GetString(e.data);
        Repaint();
    }

    void OnGUI() {
        GUILayout.Label($"接続中の実機: {EditorConnection.instance.ConnectedPlayers.Count} 台");

        if (GUILayout.Button("Hello", GUILayout.Height(40))) {
            EditorConnection.instance.Send(DebugMsg.Command, Encoding.UTF8.GetBytes("Hello"));
            captureRGB.onTrigger();
        }

        GUILayout.Label($"実機からの返事: {lastAck}");
    }
}
