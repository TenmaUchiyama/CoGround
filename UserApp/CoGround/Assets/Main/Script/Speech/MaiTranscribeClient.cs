using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// MAI-Transcribe-2 で音声を文字起こしするクライアント。
/// Azure Speech の Fast Transcription API (同期 REST) に enhancedMode.model = "MAI-Transcribe-2" を付けて投げる。
/// https://learn.microsoft.com/azure/ai-services/speech-service/mai-transcribe
///
/// ■ 使い方
///   var client = new MaiTranscribeClient(config);
///   MaiTranscription r = await client.TranscribeWavAsync(wavBytes);
///   Debug.Log(r.Text);
///
///   // AudioClip / float サンプルからでも可
///   await client.TranscribeAsync(clip);
///
/// ■ 制約 (プレビュー時点の公式ドキュメントより)
///   入力は WAV / MP3 / FLAC。ストリーミングではなく「録り終えてから送る」方式。
///   UnityWebRequest を使うので、メインスレッドから呼ぶこと。
/// </summary>
public class MaiTranscribeClient
{
    const string TranscribePath = "/speechtotext/transcriptions:transcribe";

    readonly MaiTranscribeConfig config;

    public MaiTranscribeClient(MaiTranscribeConfig config)
    {
        this.config = config != null ? config : ScriptableObject.CreateInstance<MaiTranscribeConfig>();
    }

    public MaiTranscribeConfig Config => config;

    /// <summary>エンドポイントとキーが揃っているか (揃っていなければ理由を返す)</summary>
    public bool IsConfigured(out string reason)
    {
        if (string.IsNullOrEmpty(config.ResolveEndpoint()))
        {
            reason = $"Endpoint is not set (Config or environment variable {MaiTranscribeConfig.EndpointEnvVar})";
            return false;
        }
        if (string.IsNullOrEmpty(config.ResolveApiKey()))
        {
            reason = $"Api Key is not set (Config or environment variable {MaiTranscribeConfig.ApiKeyEnvVar})";
            return false;
        }
        reason = null;
        return true;
    }

    public async Task<MaiTranscription> TranscribeAsync(AudioClip clip, CancellationToken ct = default)
    {
        var samples = new float[clip.samples * clip.channels];
        clip.GetData(samples, 0); // AudioClip はメインスレッドでしか触れない
        return await TranscribeAsync(samples, clip.channels, clip.frequency, ct);
    }

    public async Task<MaiTranscription> TranscribeAsync(float[] samples, int channels, int sampleRate, CancellationToken ct = default)
    {
        byte[] wav = await Task.Run(() => WavEncoder.FromSamples(samples, channels, sampleRate));
        return await TranscribeWavAsync(wav, ct);
    }

    /// <summary>音声ファイル (WAV / MP3 / FLAC) のバイト列を送って文字起こしする</summary>
    public async Task<MaiTranscription> TranscribeWavAsync(byte[] audio, CancellationToken ct = default,
        string fileName = "audio.wav", string contentType = "audio/wav")
    {
        if (!IsConfigured(out var reason)) throw new MaiTranscribeException(reason);
        if (audio == null || audio.Length == 0) throw new ArgumentException("audio が空です", nameof(audio));

        string url = config.ResolveEndpoint().TrimEnd('/') + TranscribePath + "?api-version=" + Uri.EscapeDataString(config.apiVersion);
        string definition = BuildDefinitionJson();
        string boundary = "----CoGroundBoundary" + Guid.NewGuid().ToString("N");
        byte[] body = BuildMultipartBody(boundary, definition, audio, fileName, contentType);

        using var req = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST)
        {
            uploadHandler = new UploadHandlerRaw(body) { contentType = "multipart/form-data; boundary=" + boundary },
            downloadHandler = new DownloadHandlerBuffer(),
            timeout = Mathf.Max(0, config.timeoutSeconds),
        };
        req.SetRequestHeader("Ocp-Apim-Subscription-Key", config.ResolveApiKey());

        await SendAsync(req, ct);

        string text = req.downloadHandler?.text;
        if (req.result != UnityWebRequest.Result.Success)
            throw new MaiTranscribeException($"HTTP {req.responseCode} {req.error}: {ExtractErrorMessage(text)}", req.responseCode, text);

        try
        {
            // 解析は別スレッドで
            var result = await Task.Run(() => JsonConvert.DeserializeObject<MaiTranscription>(text)) ?? new MaiTranscription();
            result.RawJson = text;
            return result;
        }
        catch (JsonException e)
        {
            throw new MaiTranscribeException("応答 JSON を解釈できません: " + e.Message, req.responseCode, text);
        }
    }

    /// <summary>multipart の definition フィールドに入れる JSON</summary>
    public string BuildDefinitionJson()
    {
        var modelOptions = new JObject
        {
            ["transcribeStyle"] = config.transcribeStyle == MaiTranscribeStyle.Clean ? "clean" : "verbatim",
        };
        var def = new JObject
        {
            ["enhancedMode"] = new JObject
            {
                ["enabled"] = true,
                ["model"] = string.IsNullOrWhiteSpace(config.model) ? "MAI-Transcribe-2" : config.model.Trim(),
                ["modelOptions"] = modelOptions,
            },
        };
        if (!string.IsNullOrWhiteSpace(config.locale))
            def["locales"] = new JArray(config.locale.Trim());

        var phrases = new List<string>();
        if (config.phrases != null)
            foreach (var p in config.phrases)
                if (!string.IsNullOrWhiteSpace(p)) phrases.Add(p.Trim());
        if (phrases.Count > 0)
            def["phraseList"] = new JObject { ["phrases"] = new JArray(phrases) };

        return def.ToString(Formatting.None);
    }

    static byte[] BuildMultipartBody(string boundary, string definitionJson, byte[] audio, string fileName, string contentType)
    {
        using var ms = new MemoryStream(audio.Length + 1024);
        void Write(string s) { var b = Encoding.UTF8.GetBytes(s); ms.Write(b, 0, b.Length); }

        Write($"--{boundary}\r\n");
        Write("Content-Disposition: form-data; name=\"definition\"\r\n");
        Write("Content-Type: application/json\r\n\r\n");
        Write(definitionJson);
        Write("\r\n");

        Write($"--{boundary}\r\n");
        Write($"Content-Disposition: form-data; name=\"audio\"; filename=\"{fileName}\"\r\n");
        Write($"Content-Type: {contentType}\r\n\r\n");
        ms.Write(audio, 0, audio.Length);
        Write("\r\n");

        Write($"--{boundary}--\r\n");
        return ms.ToArray();
    }

    static Task SendAsync(UnityWebRequest req, CancellationToken ct)
    {
        var tcs = new TaskCompletionSource<bool>();
        var op = req.SendWebRequest();
        CancellationTokenRegistration reg = default;
        if (ct.CanBeCanceled)
            reg = ct.Register(() =>
            {
                // UnityWebRequest.Abort はメインスレッドから呼ぶ前提 (Unity の SynchronizationContext 上で await している想定)
                if (!req.isDone) req.Abort();
                tcs.TrySetCanceled(ct);
            }, useSynchronizationContext: true);
        op.completed += _ =>
        {
            reg.Dispose();
            tcs.TrySetResult(true);
        };
        return tcs.Task;
    }

    static string ExtractErrorMessage(string body)
    {
        if (string.IsNullOrEmpty(body)) return "(no body)";
        try
        {
            var j = JObject.Parse(body);
            var msg = j.SelectToken("error.message") ?? j.SelectToken("message");
            var code = j.SelectToken("error.code") ?? j.SelectToken("code");
            if (msg != null) return code != null ? $"[{code}] {msg}" : msg.ToString();
        }
        catch (JsonException) { }
        return body.Length > 500 ? body.Substring(0, 500) + "..." : body;
    }
}

/// <summary>Fast Transcription API の応答</summary>
[Serializable]
public class MaiTranscription
{
    public long durationMilliseconds;
    public List<MaiCombinedPhrase> combinedPhrases = new List<MaiCombinedPhrase>();
    public List<MaiPhrase> phrases = new List<MaiPhrase>();

    /// <summary>受信した JSON そのまま (デバッグ用)</summary>
    [JsonIgnore] public string RawJson;

    /// <summary>全文 (combinedPhrases を連結)</summary>
    [JsonIgnore]
    public string Text
    {
        get
        {
            if (combinedPhrases == null || combinedPhrases.Count == 0) return "";
            if (combinedPhrases.Count == 1) return combinedPhrases[0].text ?? "";
            var sb = new StringBuilder();
            foreach (var c in combinedPhrases)
            {
                if (sb.Length > 0) sb.Append('\n');
                sb.Append(c.text);
            }
            return sb.ToString();
        }
    }
}

[Serializable]
public class MaiCombinedPhrase
{
    public int? channel;
    public string text;
}

[Serializable]
public class MaiPhrase
{
    public int? channel;
    public int? speaker;
    public long offsetMilliseconds;
    public long durationMilliseconds;
    public string text;
    public string locale;
    public float confidence;
    public List<MaiWord> words;
}

[Serializable]
public class MaiWord
{
    public string text;
    public long offsetMilliseconds;
    public long durationMilliseconds;
}

public class MaiTranscribeException : Exception
{
    public long StatusCode { get; }
    public string ResponseBody { get; }

    public MaiTranscribeException(string message, long statusCode = 0, string responseBody = null) : base(message)
    {
        StatusCode = statusCode;
        ResponseBody = responseBody;
    }
}
