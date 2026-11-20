using System.Collections;
using System.Collections.Generic;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// PushToTalkTranscriber の状態を見せる World Space パネル (Quest 向け)。
///   ・状態: 待機 / 録音中 (赤く点滅 + 経過時間) / 文字起こし中 (黄色)
///   ・波形: 録音中はマイク入力レベルを流れるバーで表示。小さすぎる・音割れも色と文言で知らせる
///   ・文字: 認識結果をタイプライター風に表示し、前の結果は下に薄く残す
///
/// UI の部品は Editor の「CoGround/Speech To Text (Quest) をセットアップ」で作る
/// (Assets/Main/Prefab/UI/SpeechToTextPanel.prefab)。表示だけなので Ray / Poke は不要。
/// </summary>
public class SpeechToTextPanel : MonoBehaviour
{
    [Tooltip("空ならシーンから探す")]
    [SerializeField] private PushToTalkTranscriber transcriber;
    [Tooltip("文字起こしを依頼として送る部品。空ならシーンから探す (無ければ依頼の表示は出さない)")]
    [SerializeField] private SpeechTaskRequester taskRequester;

    [Header("UI 部品")]
    [SerializeField] private Image statusDot;
    [SerializeField] private TMP_Text statusLabel;
    [SerializeField] private TMP_Text timerLabel;
    [SerializeField] private RectTransform waveformArea;
    [SerializeField] private Sprite barSprite;
    [SerializeField] private TMP_Text hintLabel;
    [SerializeField] private TMP_Text transcriptLabel;
    [SerializeField] private TMP_Text historyLabel;
    [SerializeField] private TMP_Text footerLabel;

    [Header("波形")]
    [SerializeField] private int barCount = 48;
    [SerializeField] private float barGap = 3f;
    [SerializeField] private float barMinHeight = 4f;
    [Tooltip("1 秒あたりのバーの流れる本数")]
    [SerializeField] private float barsPerSecond = 24f;
    [Tooltip("この dB 以下は無音扱い")]
    [SerializeField] private float silenceDb = -50f;
    [Tooltip("この dB でバーが最大")]
    [SerializeField] private float loudDb = -12f;

    [Header("文字")]
    [Tooltip("1 秒あたりに表示する文字数")]
    [SerializeField] private float typewriterCharsPerSecond = 40f;
    [SerializeField] private int historyLines = 3; // historyLabel が無ければ表示しない
    [Tooltip("操作のヒント (フッター)")]
    [SerializeField] private string controlHint = "Hold the right trigger to record / release to transcribe";

    [Header("色")]
    [SerializeField] private Color idleColor = new Color(0.45f, 0.85f, 0.55f);
    [SerializeField] private Color recordingColor = new Color(1f, 0.32f, 0.32f);
    [SerializeField] private Color transcribingColor = new Color(1f, 0.78f, 0.25f);
    [SerializeField] private Color quietBarColor = new Color(0.40f, 0.43f, 0.50f);
    [SerializeField] private Color goodBarColor = new Color(0.35f, 0.85f, 1f);
    [SerializeField] private Color clipBarColor = new Color(1f, 0.35f, 0.30f);
    [SerializeField] private Color hintColor = new Color(0.70f, 0.74f, 0.80f);
    [SerializeField] private Color warnColor = new Color(1f, 0.70f, 0.30f);
    [SerializeField] private Color errorColor = new Color(1f, 0.45f, 0.42f);

    const float QuietWarnSeconds = 1.2f;
    const float MessageSeconds = 4f;

    Image[] bars;
    float[] barValues;     // 0..1
    Color[] barColors;
    float barAccumulator;
    float quietTime;
    bool heardVoice;

    string transientMessage;
    Color transientColor;
    float transientUntil;

    float nextFooterUpdate;

    string fullTranscript = "";
    float revealStart;
    readonly List<string> history = new List<string>();

    void Awake()
    {
        if (transcriber == null) transcriber = FindAnyObjectByType<PushToTalkTranscriber>();
        if (taskRequester == null) taskRequester = FindAnyObjectByType<SpeechTaskRequester>();
        BuildBars();
        if (transcriptLabel != null) transcriptLabel.text = "";
        if (historyLabel != null) historyLabel.text = "";
    }

    void OnEnable()
    {
        if (taskRequester != null)
        {
            taskRequester.Sent += OnTaskSent;
            taskRequester.SendFailed += OnFailed;
        }
        if (transcriber == null) return;
        transcriber.StateChanged += OnStateChanged;
        transcriber.Transcribed += OnTranscribed;
        transcriber.Failed += OnFailed;
    }

    void OnDisable()
    {
        if (taskRequester != null)
        {
            taskRequester.Sent -= OnTaskSent;
            taskRequester.SendFailed -= OnFailed;
        }
        if (transcriber == null) return;
        transcriber.StateChanged -= OnStateChanged;
        transcriber.Transcribed -= OnTranscribed;
        transcriber.Failed -= OnFailed;
    }

    void Start()
    {
        StartCoroutine(PrewarmGlyphs());
        if (transcriber == null)
            ShowMessage("No PushToTalkTranscriber in the scene", errorColor);
        else if (!transcriber.IsConfigured(out var reason))
            ShowMessage(reason, errorColor, float.PositiveInfinity);
    }

    /// <summary>
    /// 日本語の動的フォントは、初めて出る文字の SDF をその場で作るので重い (結果が出た瞬間にカクつく)。
    /// UI の定型文・かな・英数字を起動直後に少しずつ作っておく。漢字は出たときに作られる。
    /// </summary>
    IEnumerator PrewarmGlyphs()
    {
        var font = transcriptLabel != null ? transcriptLabel.font : null;
        if (font == null || font.atlasPopulationMode == AtlasPopulationMode.Static) yield break;

        var sb = new StringBuilder();
        sb.Append("待機中録音中文字起こし中話してください離すと送信声が届いていませんマイクを確認音が大きすぎます割れ");
        sb.Append("トリガーを押しながら右左既定聞き取れませんでした秒で音声に送信しています");
        sb.Append("で依頼を送る言い直す依頼しました送れませんサーバーにつながっていません");
        sb.Append(controlHint);
        sb.Append("0123456789:.-—…・、。「」（）()?!？！ ");
        for (char c = 'ぁ'; c <= 'ゖ'; c++) sb.Append(c);
        for (char c = 'ァ'; c <= 'ヺ'; c++) sb.Append(c);
        sb.Append('ー');
        for (char c = '!'; c <= '~'; c++) sb.Append(c);

        string all = sb.ToString();
        const int perFrame = 12; // 1 フレームに作る数 (多いとそのフレームが重くなる)
        for (int i = 0; i < all.Length; i += perFrame)
        {
            font.TryAddCharacters(all.Substring(i, Mathf.Min(perFrame, all.Length - i)));
            yield return null;
        }
    }

    // ---- イベント ----

    void OnStateChanged(PushToTalkTranscriber.TalkState s)
    {
        if (s == PushToTalkTranscriber.TalkState.Recording)
        {
            quietTime = 0f;
            heardVoice = false;
            transientMessage = null;
        }
    }

    void OnTranscribed(SpeechTranscriptResult r)
    {
        if (!string.IsNullOrEmpty(fullTranscript)) PushHistory(fullTranscript);
        fullTranscript = r.IsEmpty ? "<color=#8a909c>(Couldn't catch that)</color>" : r.Text;
        revealStart = Time.time;
        if (transcriptLabel != null)
        {
            transcriptLabel.text = fullTranscript;
            transcriptLabel.maxVisibleCharacters = 0;
        }
        ShowMessage($"Audio {r.AudioSeconds:0.0}s → transcribed in {r.ResponseSeconds:0.0}s", hintColor);
    }

    void OnFailed(string message) => ShowMessage(message, errorColor);

    void OnTaskSent(string text, Newtonsoft.Json.Linq.JToken result) => ShowMessage("Request sent", hintColor);

    void ShowMessage(string message, Color color, float seconds = MessageSeconds)
    {
        transientMessage = message;
        transientColor = color;
        transientUntil = Time.time + seconds;
    }

    void PushHistory(string text)
    {
        history.Insert(0, text);
        while (history.Count > historyLines) history.RemoveAt(history.Count - 1);
        if (historyLabel == null) return;
        var sb = new StringBuilder();
        for (int i = 0; i < history.Count; i++)
        {
            if (i > 0) sb.Append('\n');
            sb.Append(history[i]);
        }
        historyLabel.text = sb.ToString();
    }

    // ---- 毎フレーム ----

    void Update()
    {
        var state = transcriber != null ? transcriber.State : PushToTalkTranscriber.TalkState.Idle;
        UpdateStatus(state);
        UpdateWaveform(state);
        UpdateHint(state);
        UpdateTypewriter();
    }

    void UpdateStatus(PushToTalkTranscriber.TalkState state)
    {
        Color c;
        string label;
        string timer = "";
        float pulse = 1f;

        switch (state)
        {
            case PushToTalkTranscriber.TalkState.Recording:
                c = recordingColor;
                label = "Recording";
                pulse = 0.55f + 0.45f * Mathf.Abs(Mathf.Sin(Time.time * 4f));
                float t = transcriber.RecordingSeconds;
                timer = $"{(int)t / 60}:{t % 60f:00.0}";
                break;
            case PushToTalkTranscriber.TalkState.Transcribing:
                c = transcribingColor;
                label = "Transcribing" + new string('.', 1 + (int)(Time.time * 3f) % 3);
                break;
            default:
                c = idleColor;
                label = "Idle";
                break;
        }

        if (statusDot != null)
        {
            statusDot.color = new Color(c.r, c.g, c.b, pulse);
            float s = state == PushToTalkTranscriber.TalkState.Recording ? 1f + 0.15f * pulse : 1f;
            statusDot.rectTransform.localScale = new Vector3(s, s, 1f);
        }
        if (statusLabel != null)
        {
            statusLabel.text = label;
            statusLabel.color = c;
        }
        if (timerLabel != null) timerLabel.text = timer;
        // マイク名の取得は重めなので 1 秒ごと
        if (footerLabel != null && Time.unscaledTime >= nextFooterUpdate)
        {
            nextFooterUpdate = Time.unscaledTime + 1f;
            var hint = taskRequester != null ? $"{controlHint}\n{taskRequester.ButtonLabel} button: send request" : controlHint;
            footerLabel.text = transcriber != null
                ? $"{hint}\nMic: {transcriber.Recorder.EffectiveDeviceName}"
                : hint;
        }
    }

    void BuildBars()
    {
        if (waveformArea == null) return;
        bars = new Image[barCount];
        barValues = new float[barCount];
        barColors = new Color[barCount];
        float width = waveformArea.rect.width;
        float barWidth = Mathf.Max(1f, (width - barGap * (barCount - 1)) / barCount);

        for (int i = 0; i < barCount; i++)
        {
            var go = new GameObject("Bar" + i, typeof(RectTransform), typeof(Image));
            go.transform.SetParent(waveformArea, false);
            var rt = (RectTransform)go.transform;
            rt.anchorMin = rt.anchorMax = new Vector2(0f, 0.5f);
            rt.pivot = new Vector2(0f, 0.5f);
            rt.anchoredPosition = new Vector2(i * (barWidth + barGap), 0f);
            rt.sizeDelta = new Vector2(barWidth, barMinHeight);
            var img = go.GetComponent<Image>();
            img.sprite = barSprite;
            img.type = barSprite != null ? Image.Type.Sliced : Image.Type.Simple;
            img.raycastTarget = false;
            img.color = quietBarColor;
            bars[i] = img;
            barColors[i] = quietBarColor;
        }
    }

    void UpdateWaveform(PushToTalkTranscriber.TalkState state)
    {
        if (bars == null) return;
        float maxHeight = waveformArea.rect.height;

        if (state == PushToTalkTranscriber.TalkState.Recording)
        {
            // 入力レベル (dB) を 0..1 に
            float level = transcriber.Level;
            float db = level > 1e-6f ? 20f * Mathf.Log10(level) : -100f;
            float v = Mathf.InverseLerp(silenceDb, loudDb, db);
            bool clipping = transcriber.Peak > 0.97f;
            Color col = clipping ? clipBarColor : Color.Lerp(quietBarColor, goodBarColor, Mathf.InverseLerp(0.05f, 0.35f, v));

            if (v > 0.2f) heardVoice = true;
            quietTime = v < 0.08f ? quietTime + Time.deltaTime : 0f;

            // 一定間隔で左へ流す。右端が最新
            barAccumulator += Time.deltaTime * barsPerSecond;
            while (barAccumulator >= 1f)
            {
                barAccumulator -= 1f;
                for (int i = 0; i < barCount - 1; i++)
                {
                    barValues[i] = barValues[i + 1];
                    barColors[i] = barColors[i + 1];
                }
            }
            // 最新バーはその瞬間の値で滑らかに
            int last = barCount - 1;
            barValues[last] = Mathf.Max(v, Mathf.Lerp(barValues[last], v, 0.5f));
            barColors[last] = col;
        }
        else
        {
            for (int i = 0; i < barCount; i++)
            {
                float target;
                Color col;
                if (state == PushToTalkTranscriber.TalkState.Transcribing)
                {
                    // 送信中: 左から右へ流れる波
                    float phase = i * 0.35f - Time.time * 6f;
                    target = 0.12f + 0.18f * (0.5f + 0.5f * Mathf.Sin(phase));
                    col = transcribingColor;
                }
                else
                {
                    // 待機: ゆっくり呼吸
                    target = 0.03f + 0.03f * (0.5f + 0.5f * Mathf.Sin(Time.time * 1.5f + i * 0.2f));
                    col = quietBarColor;
                }
                barValues[i] = Mathf.Lerp(barValues[i], target, Time.deltaTime * 8f);
                barColors[i] = Color.Lerp(barColors[i], col, Time.deltaTime * 8f);
            }
        }

        for (int i = 0; i < barCount; i++)
        {
            var rt = bars[i].rectTransform;
            rt.sizeDelta = new Vector2(rt.sizeDelta.x, Mathf.Max(barMinHeight, barValues[i] * maxHeight));
            bars[i].color = barColors[i];
        }
    }

    void UpdateHint(PushToTalkTranscriber.TalkState state)
    {
        if (hintLabel == null) return;

        if (transientMessage != null && Time.time < transientUntil && state != PushToTalkTranscriber.TalkState.Recording)
        {
            hintLabel.text = transientMessage;
            hintLabel.color = transientColor;
            return;
        }

        switch (state)
        {
            case PushToTalkTranscriber.TalkState.Recording:
                if (transcriber.Peak > 0.97f)
                {
                    hintLabel.text = "Too loud (clipping)";
                    hintLabel.color = errorColor;
                }
                else if (quietTime > QuietWarnSeconds && !heardVoice)
                {
                    hintLabel.text = "Can't hear you (check the microphone)";
                    hintLabel.color = warnColor;
                }
                else
                {
                    hintLabel.text = "Speak now… release to send";
                    hintLabel.color = hintColor;
                }
                break;
            case PushToTalkTranscriber.TalkState.Transcribing:
                    hintLabel.text = "Sending…";
                hintLabel.color = hintColor;
                break;
            default:
                if (taskRequester != null && taskRequester.State == SpeechTaskRequester.SendState.Sending)
                {
                    hintLabel.text = "Sending request…";
                    hintLabel.color = hintColor;
                }
                else if (taskRequester != null && taskRequester.State == SpeechTaskRequester.SendState.Ready)
                {
                    hintLabel.text = $"Press {taskRequester.ButtonLabel} to send the request / trigger to say it again";
                    hintLabel.color = warnColor;
                }
                else
                {
                    hintLabel.text = "Hold the trigger while you speak";
                    hintLabel.color = hintColor;
                }
                break;
        }
    }

    void UpdateTypewriter()
    {
        if (transcriptLabel == null || string.IsNullOrEmpty(fullTranscript)) return;
        // 表示文字数を時間とともに増やす (TMP がタグを除いた文字数で切ってくれる)
        float elapsed = Time.time - revealStart;
        transcriptLabel.maxVisibleCharacters = elapsed * typewriterCharsPerSecond > 100000f
            ? 99999
            : Mathf.FloorToInt(elapsed * typewriterCharsPerSecond);
    }
}
