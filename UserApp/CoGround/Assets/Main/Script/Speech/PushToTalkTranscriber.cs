using System;
using System.Threading.Tasks;
using UnityEngine;

/// <summary>
/// プッシュトゥトークの本体 (UI も入力も持たない)。
/// BeginTalk() で録音開始 → EndTalk() で録音を止めて MAI-Transcribe-2 に送り、結果をイベントで通知する。
///
/// ■ 使い方
///   入力: PushToTalkControllerInput (Quest のトリガー / スペースキー) を同じ GameObject に付ける。
///         独自の UI ボタンから使うなら BeginTalk / EndTalk を呼ぶだけ。
///   表示: SpeechToTextPanel など、下のイベントとプロパティを見る。
///
///   transcriber.Transcribed += r => Debug.Log(r.Text);
/// </summary>
[RequireComponent(typeof(MicrophoneRecorder))]
public class PushToTalkTranscriber : MonoBehaviour
{
    public enum TalkState
    {
        Idle,
        Recording,
        Transcribing,
    }

    [SerializeField] private MaiTranscribeConfig config;
    [Tooltip("これより短い録音は送らない (誤操作対策)")]
    [SerializeField] private float minSeconds = 0.3f;
    [Tooltip("1 フレームがこの ms を超えたら、そのときの状態をログに出す (0 で無効)。砂時計が出る原因調査用")]
    [SerializeField] private float stallLogMs = 100f;

    public MicrophoneRecorder Recorder { get; private set; }
    public MaiTranscribeClient Client { get; private set; }

    public TalkState State { get; private set; } = TalkState.Idle;
    /// <summary>送信中のリクエスト数 (録音中でも前の結果待ちがありうる)</summary>
    public int PendingRequests { get; private set; }

    /// <summary>マイク入力レベル (0..1, RMS)</summary>
    public float Level => Recorder != null ? Recorder.Level : 0f;
    /// <summary>マイク入力の最大振幅 (0..1)</summary>
    public float Peak => Recorder != null ? Recorder.Peak : 0f;
    public float RecordingSeconds => Recorder != null ? Recorder.RecordingSeconds : 0f;

    /// <summary>状態が変わった</summary>
    public event Action<TalkState> StateChanged;
    /// <summary>録音を止めて送信を始めた (録音秒数)</summary>
    public event Action<float> RequestStarted;
    /// <summary>文字起こしが返ってきた</summary>
    public event Action<SpeechTranscriptResult> Transcribed;
    /// <summary>警告・エラー (表示用メッセージ)</summary>
    public event Action<string> Failed;

    void Awake()
    {
        Recorder = GetComponent<MicrophoneRecorder>();
        Client = new MaiTranscribeClient(config);
        Recorder.AutoStopped += audio => Send(audio);
    }

    void Update()
    {
        float ms = Time.unscaledDeltaTime * 1000f;
        if (stallLogMs > 0f && ms > stallLogMs && Time.frameCount > 10)
            Debug.LogWarning($"[PushToTalk] フレームが {ms:0} ms 止まりました (状態: {State}, 送信待ち: {PendingRequests})");
    }

    /// <summary>エンドポイント/キーが設定されているか</summary>
    public bool IsConfigured(out string reason) => Client.IsConfigured(out reason);

    /// <summary>録音を始める。始められなければ false (理由は Failed で通知)</summary>
    public bool BeginTalk()
    {
        if (State == TalkState.Recording) return true;
        if (!Client.IsConfigured(out var reason))
        {
            Failed?.Invoke(reason);
            return false;
        }
        if (!Recorder.StartRecording())
        {
            Failed?.Invoke("Can't start the microphone (check permission / connection)");
            return false;
        }
        SetState(TalkState.Recording);
        return true;
    }

    /// <summary>録音を止めて送信する</summary>
    public void EndTalk()
    {
        if (!Recorder.IsRecording) return;
        Send(Recorder.StopRecording());
    }

    /// <summary>録音を止めて捨てる (送信しない)</summary>
    public void CancelTalk()
    {
        if (!Recorder.IsRecording) return;
        Recorder.StopRecording();
        SetState(PendingRequests > 0 ? TalkState.Transcribing : TalkState.Idle);
    }

    async void Send(RecordedAudio audio)
    {
        if (audio == null || audio.DurationSeconds < minSeconds)
        {
            SetState(PendingRequests > 0 ? TalkState.Transcribing : TalkState.Idle);
            Failed?.Invoke("Recording too short. Keep holding the trigger while you speak");
            return;
        }

        PendingRequests++;
        SetState(TalkState.Transcribing);
        RequestStarted?.Invoke(audio.DurationSeconds);
        float t0 = Time.realtimeSinceStartup;

        try
        {
            // WAV 変換は別スレッドで (長い録音でもメインスレッドを止めない)
            byte[] wav = await Task.Run(() => audio.ToWav());
            var result = await Client.TranscribeWavAsync(wav, destroyCancellationToken);
            var r = new SpeechTranscriptResult(result.Text, audio.DurationSeconds, Time.realtimeSinceStartup - t0, result);
            Debug.Log($"[PushToTalk] \"{r.Text}\" (音声 {r.AudioSeconds:0.0}s / 応答 {r.ResponseSeconds:0.00}s)");
            Transcribed?.Invoke(r);
        }
        catch (OperationCanceledException)
        {
            return;
        }
        catch (Exception e)
        {
            Debug.LogError("[PushToTalk] " + e);
            Failed?.Invoke(e.Message);
        }
        finally
        {
            PendingRequests--;
        }

        if (State == TalkState.Transcribing && PendingRequests == 0) SetState(TalkState.Idle);
    }

    void SetState(TalkState s)
    {
        if (State == s) return;
        State = s;
        StateChanged?.Invoke(s);
    }
}

/// <summary>1 回分の文字起こし結果</summary>
public class SpeechTranscriptResult
{
    public readonly string Text;
    public readonly float AudioSeconds;
    public readonly float ResponseSeconds;
    public readonly MaiTranscription Raw;
    public readonly DateTime Time = DateTime.Now;

    public SpeechTranscriptResult(string text, float audioSeconds, float responseSeconds, MaiTranscription raw)
    {
        Text = text ?? "";
        AudioSeconds = audioSeconds;
        ResponseSeconds = responseSeconds;
        Raw = raw;
    }

    public bool IsEmpty => string.IsNullOrWhiteSpace(Text);
}
