using System;
using System.Diagnostics;
using UnityEngine;
#if UNITY_ANDROID && !UNITY_EDITOR
using UnityEngine.Android;
#endif
using Debug = UnityEngine.Debug;

/// <summary>
/// プッシュトゥトーク用のマイク録音。StartRecording() → StopRecording() で録った区間だけを返す。
///
/// ■ 仕組み
///   Microphone.Start / End は数百 ms メインスレッドを止めることがある (Quest だと砂時計が出る)。
///   なので起動時にマイクをループ録音で開きっぱなしにし、押している間だけリングバッファから
///   サンプルを取り出して溜める。押した瞬間にブロックしないうえ、押す少し前 (preRoll) から録れるので
///   話し始めが切れない。
///
/// Quest (Android) では初回にマイク権限 (RECORD_AUDIO) を要求し、許可されたらマイクを開く。
/// アプリが裏に回ったらマイクを閉じ、戻ったら開き直す。
/// </summary>
public class MicrophoneRecorder : MonoBehaviour
{
    [Tooltip("使うマイク (空なら既定のマイク)。Inspector ではドロップダウンで選べる")]
    [MicrophoneDevice]
    [SerializeField] private string deviceName = "";
    [Tooltip("録音のサンプリングレート (音声認識なら 16000 で十分)")]
    [SerializeField] private int sampleRate = 16000;
    [Tooltip("1 回の録音の最大秒数。超えると自動で止まる")]
    [SerializeField] private int maxSeconds = 60;
    [Tooltip("押す前の音をこの秒数だけ含める (話し始めの頭切れ対策)")]
    [SerializeField] private float preRollSeconds = 0.25f;
    [Tooltip("マイクのリングバッファの秒数 (フレームが止まってもこの秒数までは取りこぼさない)")]
    [SerializeField] private int ringSeconds = 4;
    [Tooltip("この ms を超えたマイク操作をログに出す (0 で出さない)")]
    [SerializeField] private float slowLogMs = 30f;

    public bool IsRecording { get; private set; }
    /// <summary>マイクを開いているか (録音していなくても開いている)</summary>
    public bool IsMicOpen => clip != null;
    /// <summary>録音開始からの秒数</summary>
    public float RecordingSeconds => IsRecording ? (float)recordedCount / Mathf.Max(1, channels * frequency) : 0f;
    /// <summary>直近の入力レベル (0..1, RMS)。メーター表示用</summary>
    public float Level { get; private set; }
    /// <summary>直近の最大振幅 (0..1)。1 に近いと音割れ</summary>
    public float Peak { get; private set; }

    /// <summary>maxSeconds に達して自動停止したときに呼ばれる (録れた音声)</summary>
    public event Action<RecordedAudio> AutoStopped;

    AudioClip clip;
    string activeDevice;
    int channels = 1;
    int frequency;
    int lastPosition;          // リング上で次に読む位置 (フレーム単位)
    bool paused;

    int chunkFrames;           // 10ms 単位で読む (毎フレーム配列を作らないため)
    float[] chunkBuffer = new float[0];
    float nextOpenAttempt;
    float[] recorded = new float[0];
    int recordedCount;         // recorded に溜まったサンプル数 (チャンネル込み)

    static string[] cachedDevices;

    // ---- デバイス一覧 (列挙は重いのでキャッシュ) ----

    /// <summary>接続されているマイク名の一覧 (キャッシュ。更新は RefreshDevices)</summary>
    public static string[] Devices => cachedDevices ??= Microphone.devices;

    /// <summary>マイク一覧を取り直す (一覧を開いたときなどに呼ぶ)</summary>
    public static string[] RefreshDevices() => cachedDevices = Microphone.devices;

    public bool HasMicrophone => Devices.Length > 0 || RefreshDevices().Length > 0;

    /// <summary>使うマイク名 (空/null なら既定のマイク)。変えるとマイクを開き直す (録音中は次の録音から)</summary>
    public string DeviceName
    {
        get => deviceName;
        set
        {
            value ??= "";
            if (value == deviceName) return;
            deviceName = value;
            if (IsMicOpen && !IsRecording)
            {
                CloseMic();
                OpenMic();
            }
        }
    }

    /// <summary>実際に使われるマイク名 (既定のマイクのときは一覧の先頭)</summary>
    public string EffectiveDeviceName
    {
        get
        {
            if (!string.IsNullOrEmpty(deviceName)) return deviceName;
            var devices = Devices;
            return devices.Length > 0 ? devices[0] + " (default)" : "(no microphone)";
        }
    }

    // ---- ライフサイクル ----

    void Start()
    {
#if UNITY_ANDROID && !UNITY_EDITOR
        if (!Permission.HasUserAuthorizedPermission(Permission.Microphone))
        {
            Permission.RequestUserPermission(Permission.Microphone);
            return; // 許可されたら Update で開く
        }
#endif
        OpenMic();
    }

    void OnApplicationPause(bool pause)
    {
        paused = pause;
        if (pause)
        {
            if (IsRecording) StopRecording();
            CloseMic();
        }
    }

    void OnDisable() => CloseMic();

    bool HasPermission()
    {
#if UNITY_ANDROID && !UNITY_EDITOR
        return Permission.HasUserAuthorizedPermission(Permission.Microphone);
#else
        return true;
#endif
    }

    bool OpenMic()
    {
        if (IsMicOpen) return true;
        if (!HasPermission() || !HasMicrophone) return false;

        activeDevice = string.IsNullOrEmpty(deviceName) ? null : deviceName;
        if (activeDevice != null && Array.IndexOf(Devices, activeDevice) < 0)
        {
            Debug.LogWarning($"[MicrophoneRecorder] マイク \"{activeDevice}\" が見つからないので既定のマイクを使います");
            activeDevice = null;
        }

        var sw = Stopwatch.StartNew();
        clip = Microphone.Start(activeDevice, true, Mathf.Max(2, ringSeconds), sampleRate);
        LogIfSlow("Microphone.Start", sw);
        if (clip == null) return false;

        channels = clip.channels;
        frequency = clip.frequency;
        chunkFrames = Mathf.Max(1, frequency / 100);
        if (chunkBuffer.Length != chunkFrames * channels) chunkBuffer = new float[chunkFrames * channels];
        lastPosition = Microphone.GetPosition(activeDevice);
        return true;
    }

    void CloseMic()
    {
        if (!IsMicOpen) return;
        IsRecording = false;
        var sw = Stopwatch.StartNew();
        Microphone.End(activeDevice);
        LogIfSlow("Microphone.End", sw);
        Destroy(clip);
        clip = null;
        Level = Peak = 0f;
    }

    // ---- 録音 ----

    public bool StartRecording()
    {
        if (IsRecording) return true;
        if (!HasPermission())
        {
#if UNITY_ANDROID && !UNITY_EDITOR
            Permission.RequestUserPermission(Permission.Microphone);
#endif
            Debug.LogWarning("[MicrophoneRecorder] マイク権限がありません");
            return false;
        }
        if (!OpenMic())
        {
            Debug.LogWarning("[MicrophoneRecorder] マイクを開けません");
            return false;
        }

        // バッファ確保 (初回だけ)
        int capacity = Mathf.Max(1, maxSeconds) * frequency * channels;
        if (recorded.Length < capacity) recorded = new float[capacity];
        recordedCount = 0;

        // 直前の preRoll 分をリングから取り出して先頭に入れる
        int ringFrames = clip.samples;
        int pre = Mathf.Clamp(Mathf.RoundToInt(preRollSeconds * frequency), 0, ringFrames - frequency / 10);
        if (pre > 0)
        {
            int start = ((lastPosition - pre) % ringFrames + ringFrames) % ringFrames;
            var preBuffer = new float[pre * channels]; // 押した瞬間に 1 回だけ
            clip.GetData(preBuffer, start);
            Append(preBuffer, preBuffer.Length);
        }

        IsRecording = true;
        return true;
    }

    /// <summary>録音を止めて、録れた区間を返す (何も録れていなければ null)</summary>
    public RecordedAudio StopRecording()
    {
        if (!IsRecording) return null;
        Pump();             // 離した瞬間までの分を取り込む
        IsRecording = false;
        Level = Peak = 0f;
        if (recordedCount <= 0) return null;

        var samples = new float[recordedCount];
        Array.Copy(recorded, samples, recordedCount);
        return new RecordedAudio(samples, channels, frequency);
    }

    void Update()
    {
        if (paused) return;
        if (!IsMicOpen)
        {
            // 権限が後から許可された / 戻ってきた (列挙が重いので 1 秒おき)
            if (Time.unscaledTime >= nextOpenAttempt)
            {
                nextOpenAttempt = Time.unscaledTime + 1f;
                if (HasPermission())
                {
                    if (Devices.Length == 0) RefreshDevices();
                    OpenMic();
                }
            }
            return;
        }
        if (!Microphone.IsRecording(activeDevice))
        {
            // デバイスが抜けた等
            Debug.LogWarning("[MicrophoneRecorder] マイクが止まりました。開き直します");
            bool wasRecording = IsRecording;
            var audio = wasRecording ? StopRecording() : null;
            CloseMic();
            RefreshDevices();
            OpenMic();
            if (audio != null) AutoStopped?.Invoke(audio);
            return;
        }

        Pump();

        if (IsRecording && recordedCount >= recorded.Length)
        {
            var audio = StopRecording();
            if (audio != null) AutoStopped?.Invoke(audio);
        }
    }

    /// <summary>リングバッファの新しい分を 10ms ずつ読み、レベルを更新し、録音中なら溜める</summary>
    void Pump()
    {
        int pos = Microphone.GetPosition(activeDevice);
        int ringFrames = clip.samples;
        int frames = (pos - lastPosition + ringFrames) % ringFrames;
        if (frames < chunkFrames) return;

        float sum = 0f, peak = 0f;
        int n = 0;
        while (frames >= chunkFrames)
        {
            clip.GetData(chunkBuffer, lastPosition); // 端は折り返して読まれる
            lastPosition = (lastPosition + chunkFrames) % ringFrames;
            frames -= chunkFrames;

            if (IsRecording) Append(chunkBuffer, chunkBuffer.Length);
            for (int i = 0; i < chunkBuffer.Length; i++)
            {
                float v = chunkBuffer[i];
                sum += v * v;
                float a = Mathf.Abs(v);
                if (a > peak) peak = a;
            }
            n += chunkBuffer.Length;
        }
        Level = Mathf.Sqrt(sum / n);
        Peak = peak;
    }

    void Append(float[] src, int count)
    {
        int n = Mathf.Min(count, recorded.Length - recordedCount);
        if (n <= 0) return;
        Array.Copy(src, 0, recorded, recordedCount, n);
        recordedCount += n;
    }

    void LogIfSlow(string what, Stopwatch sw)
    {
        if (slowLogMs > 0f && sw.Elapsed.TotalMilliseconds > slowLogMs)
            Debug.LogWarning($"[MicrophoneRecorder] {what} に {sw.Elapsed.TotalMilliseconds:0} ms かかりました");
    }
}

/// <summary>録音結果 (インターリーブされた float PCM)</summary>
public class RecordedAudio
{
    public readonly float[] Samples;
    public readonly int Channels;
    public readonly int SampleRate;

    public RecordedAudio(float[] samples, int channels, int sampleRate)
    {
        Samples = samples;
        Channels = channels;
        SampleRate = sampleRate;
    }

    public float DurationSeconds => (float)Samples.Length / Channels / SampleRate;

    public byte[] ToWav() => WavEncoder.FromSamples(Samples, Channels, SampleRate);
}
