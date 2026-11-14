using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.Networking.PlayerConnection;

public class HelloReceiver : MonoBehaviour {
    [SerializeField] TMP_Text label;  // カメラ前に置いた World Space の TextMeshPro

    void OnEnable()  => PlayerConnection.instance.Register(DebugMsg.Command, OnCommand);
    void OnDisable() => PlayerConnection.instance.Unregister(DebugMsg.Command, OnCommand);

    void OnCommand(MessageEventArgs e) {
        var msg = Encoding.UTF8.GetString(e.data);

        Debug.Log($"[Remote] {msg}");        // logcat / エディタ Console に出る
        if (label != null) label.text = msg;  // VR 内に表示

        PlayerConnection.instance.Send(DebugMsg.Ack, Encoding.UTF8.GetBytes($"received: {msg}"));
    }
}
