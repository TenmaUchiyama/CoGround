using System;
using System.Collections;
using Newtonsoft.Json.Linq;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// 音声の文字起こし (PushToTalkTranscriber) を、片付けの依頼 (task.request) として送る。
///
///   トリガーを押しながら話す → 離すと文字起こし → 「送信待ち」になる (言い直せば置き換わる)
///   B ボタン (右コントローラ。エディタでは Enter キー) → CoGroundHomeCommands.RequestTask で送る
///
/// ■ 使い方
///   PushToTalkTranscriber と同じ GameObject に付ける。CoGroundServerClient がシーンに要る (接続先のサーバー)。
///   CoGroundHomeCommands が無ければ、この GameObject に自動で付ける。
///   表示は SpeechToTextPanel が見る (送信待ちの文と「B で送信」、送信の結果)。
///
/// ■ 依頼の言葉の扱い
///   Interpret (既定 オン) なら、言葉から対象の物体をサーバーの LLM に決めさせる (数秒かかる)。
///   オフなら言葉は記録だけで、Source Region (空なら机) にある物すべてが対象になる。
/// </summary>
[RequireComponent(typeof(PushToTalkTranscriber))]
public class SpeechTaskRequester : MonoBehaviour
{
    public enum SendState
    {
        /// <summary>送る文が無い</summary>
        Idle,
        /// <summary>送信待ちの文がある</summary>
        Ready,
        Sending,
    }

    public enum Hand { Right, Left, Either }

    [Tooltip("空なら同じシーンから探し、無ければこの GameObject に付ける")]
    [SerializeField] CoGroundHomeCommands homeCommands;

    [Header("依頼 (task.request)")]
    [Tooltip("依頼の言葉から対象の物体を LLM に決めさせる (数秒かかる)")]
    [SerializeField] bool interpret = true;
    [Tooltip("依頼者の人物 ID。空なら渡さない (「私が頼んだときだけ」のルールは未確定になる)")]
    [SerializeField] string requester = "";
    [Tooltip("Interpret がオフのとき、この領域にある物すべてを対象にする。空なら机")]
    [SerializeField] string sourceRegion = "";

    [Header("送信ボタン")]
    [Tooltip("どちらの手の上のボタン (右 = B / 左 = Y) で送るか")]
    [SerializeField] Hand hand = Hand.Right;
    [Tooltip("Enter キーでも送れるようにする (エディタ確認用)")]
    [SerializeField] bool allowKeyboard = true;
    [SerializeField] bool haptics = true;

    PushToTalkTranscriber transcriber;

    public SendState State { get; private set; } = SendState.Idle;
    /// <summary>送信待ちの依頼の文 (無ければ空)</summary>
    public string PendingText { get; private set; } = "";
    /// <summary>最後に送った文</summary>
    public string LastSentText { get; private set; } = "";

    /// <summary>状態か送信待ちの文が変わった</summary>
    public event Action Changed;
    /// <summary>送れた (送った文, サーバーの応答)</summary>
    public event Action<string, JToken> Sent;
    /// <summary>送れなかった (表示用メッセージ)</summary>
    public event Action<string> SendFailed;

    /// <summary>ボタンの名前 (表示用)</summary>
    public string ButtonLabel => hand == Hand.Left ? "Y" : hand == Hand.Right ? "B" : "B / Y";

    void Awake()
    {
        transcriber = GetComponent<PushToTalkTranscriber>();
        if (homeCommands == null) homeCommands = FindAnyObjectByType<CoGroundHomeCommands>();
        if (homeCommands == null) homeCommands = gameObject.AddComponent<CoGroundHomeCommands>();
    }

    void OnEnable() => transcriber.Transcribed += OnTranscribed;
    void OnDisable() => transcriber.Transcribed -= OnTranscribed;

    void OnTranscribed(SpeechTranscriptResult r)
    {
        if (r.IsEmpty || State == SendState.Sending) return;
        PendingText = r.Text.Trim();
        SetState(SendState.Ready);
    }

    void Update()
    {
        if (State != SendState.Ready) return;
        // 録音中は押し間違いを避けるため送らない
        if (transcriber.State == PushToTalkTranscriber.TalkState.Recording) return;
        var pressed = ButtonDown();
        if (pressed != OVRInput.Controller.None || (allowKeyboard && EnterDown()))
        {
            Pulse(pressed);
            Send();
        }
    }

    /// <summary>送信待ちの文を依頼として送る</summary>
    public async void Send()
    {
        if (State != SendState.Ready || string.IsNullOrWhiteSpace(PendingText)) return;
        var text = PendingText;
        if (CoGroundServerClient.Instance == null)
        {
            SendFailed?.Invoke("Not connected to the server (no CoGroundServerClient)");
            return;
        }

        SetState(SendState.Sending);
        JToken result = null;
        try
        {
            result = await homeCommands.RequestTask(text, requester, sourceRegion, interpret);
        }
        catch (Exception e)
        {
            Debug.LogWarning("[SpeechTaskRequester] " + e.Message, this);
        }
        if (this == null) return;

        if (result == null)
        {
            // 送れなかった文は残す (もう一度ボタンで送り直せる)
            SetState(SendState.Ready);
            SendFailed?.Invoke("Couldn't send the request (check the server connection and logs)");
            return;
        }
        LastSentText = text;
        PendingText = "";
        SetState(SendState.Idle);
        Debug.Log($"[SpeechTaskRequester] 依頼した: 「{text}」", this);
        Sent?.Invoke(text, result);
    }

    /// <summary>送信待ちの文を捨てる</summary>
    public void Clear()
    {
        if (State == SendState.Sending) return;
        PendingText = "";
        SetState(SendState.Idle);
    }

    void SetState(SendState s)
    {
        State = s;
        Changed?.Invoke();
    }

    OVRInput.Controller ButtonDown()
    {
        if (hand != Hand.Left && OVRInput.GetDown(OVRInput.Button.Two, OVRInput.Controller.RTouch)) return OVRInput.Controller.RTouch;
        if (hand != Hand.Right && OVRInput.GetDown(OVRInput.Button.Two, OVRInput.Controller.LTouch)) return OVRInput.Controller.LTouch;
        return OVRInput.Controller.None;
    }

    void Pulse(OVRInput.Controller controller)
    {
        if (haptics && controller != OVRInput.Controller.None) StartCoroutine(PulseRoutine(controller));
    }

    static IEnumerator PulseRoutine(OVRInput.Controller controller)
    {
        OVRInput.SetControllerVibration(1f, 0.6f, controller);
        yield return new WaitForSecondsRealtime(0.08f);
        OVRInput.SetControllerVibration(0f, 0f, controller);
    }

    static bool EnterDown()
    {
#if ENABLE_INPUT_SYSTEM
        return Keyboard.current != null && (Keyboard.current.enterKey.wasPressedThisFrame || Keyboard.current.numpadEnterKey.wasPressedThisFrame);
#else
        return Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter);
#endif
    }
}
