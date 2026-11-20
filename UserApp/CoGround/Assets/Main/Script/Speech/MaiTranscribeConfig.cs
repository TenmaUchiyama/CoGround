using System;
using UnityEngine;

/// <summary>
/// MAI-Transcribe-2 (Azure Speech Fast Transcription API の enhancedMode) の接続設定。
///
/// ■ 作り方
///   Project ウィンドウで Create > CoGround > MAI Transcribe Config。
///   Endpoint と Api Key に Azure ポータルの Foundry (Speech) リソースの値を入れる。
///
/// ■ キーの扱い
///   Api Key / Endpoint が空なら環境変数 AZURE_SPEECH_KEY / AZURE_SPEECH_ENDPOINT を使う (Editor 向け)。
///   キー入りのアセットは Assets/Main/Secrets/ に置く (.gitignore 済み)。
/// </summary>
[CreateAssetMenu(menuName = "CoGround/MAI Transcribe Config", fileName = "MaiTranscribeConfig")]
public class MaiTranscribeConfig : ScriptableObject
{
    public const string EndpointEnvVar = "AZURE_SPEECH_ENDPOINT";
    public const string ApiKeyEnvVar = "AZURE_SPEECH_KEY";

    [Header("Azure Speech リソース")]
    [Tooltip("例: https://<リソース名>.cognitiveservices.azure.com  (空なら環境変数 AZURE_SPEECH_ENDPOINT)")]
    public string endpoint = "";

    [Tooltip("Ocp-Apim-Subscription-Key に入れるキー (空なら環境変数 AZURE_SPEECH_KEY)")]
    public string apiKey = "";

    public string apiVersion = "2025-10-15";

    [Header("モデル")]
    [Tooltip("MAI-Transcribe-2 / MAI-Transcribe-1.5")]
    public string model = "MAI-Transcribe-2";

    [Tooltip("言語を固定する場合だけ指定 (例: ja, en)。空なら自動判定")]
    public string locale = "";

    [Tooltip("clean: フィラー (えー、あの) を除いた読みやすい文 / verbatim: 話したまま")]
    public MaiTranscribeStyle transcribeStyle = MaiTranscribeStyle.Clean;

    [Tooltip("認識させたい固有名詞・専門用語 (キーワードバイアス)")]
    public string[] phrases = Array.Empty<string>();

    [Header("通信")]
    [Tooltip("リクエストのタイムアウト秒数")]
    public int timeoutSeconds = 60;

    public string ResolveEndpoint() =>
        !string.IsNullOrWhiteSpace(endpoint) ? endpoint.Trim() : Environment.GetEnvironmentVariable(EndpointEnvVar)?.Trim();

    public string ResolveApiKey() =>
        !string.IsNullOrWhiteSpace(apiKey) ? apiKey.Trim() : Environment.GetEnvironmentVariable(ApiKeyEnvVar)?.Trim();
}

public enum MaiTranscribeStyle
{
    Clean,
    Verbatim,
}
