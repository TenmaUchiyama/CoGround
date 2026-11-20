using System;
using System.IO;
using System.Text;
using UnityEngine;

/// <summary>
/// float PCM (-1..1) を 16bit PCM の WAV バイト列にする。
/// </summary>
public static class WavEncoder
{
    public static byte[] FromAudioClip(AudioClip clip)
    {
        var samples = new float[clip.samples * clip.channels];
        clip.GetData(samples, 0);
        return FromSamples(samples, clip.channels, clip.frequency);
    }

    /// <param name="samples">インターリーブされたサンプル</param>
    public static byte[] FromSamples(float[] samples, int channels, int sampleRate, int sampleCount = -1)
    {
        if (sampleCount < 0) sampleCount = samples.Length;
        const int bitsPerSample = 16;
        int blockAlign = channels * bitsPerSample / 8;
        int dataSize = sampleCount * bitsPerSample / 8;

        using var ms = new MemoryStream(44 + dataSize);
        using var w = new BinaryWriter(ms);

        w.Write(Encoding.ASCII.GetBytes("RIFF"));
        w.Write(36 + dataSize);
        w.Write(Encoding.ASCII.GetBytes("WAVE"));

        w.Write(Encoding.ASCII.GetBytes("fmt "));
        w.Write(16);                          // fmt チャンクサイズ
        w.Write((short)1);                    // PCM
        w.Write((short)channels);
        w.Write(sampleRate);
        w.Write(sampleRate * blockAlign);     // byte rate
        w.Write((short)blockAlign);
        w.Write((short)bitsPerSample);

        w.Write(Encoding.ASCII.GetBytes("data"));
        w.Write(dataSize);
        for (int i = 0; i < sampleCount; i++)
        {
            float s = Mathf.Clamp(samples[i], -1f, 1f);
            w.Write((short)Math.Round(s * short.MaxValue));
        }

        w.Flush();
        return ms.ToArray();
    }
}
