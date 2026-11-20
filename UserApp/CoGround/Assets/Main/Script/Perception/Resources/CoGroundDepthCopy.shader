// 環境深度（Meta の EnvironmentDepthManager が出す _EnvironmentDepthTexture、左目）を、CPU で読める float のテクスチャに写す。
// CoGroundFrameSender が使う。
//
// 出力は画素ごとに (深度の値 0..1, 読んだ位置 u, 読んだ位置 v, 1)。
// 読んだ位置も一緒に書くのは、テクスチャの上下の向き（Vulkan で反転するかどうか）に左右されないようにするため。
// サーバーは u, v と深度の値を Meta の occlusion シェーダーと同じ約束（uv = (NDC.xy + 1) / 2）で逆にたどって、
// ワールド座標の点に戻す（Backend/grounding_server/coground_server/perception/frame.py）。
Shader "Hidden/CoGround/DepthCopy"
{
    SubShader
    {
        Pass
        {
            ZTest Always Cull Off ZWrite Off

            CGPROGRAM
            #pragma target 4.5
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            Texture2DArray_float _EnvironmentDepthTexture;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            v2f vert(appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                uint w, h, layers;
                _EnvironmentDepthTexture.GetDimensions(w, h, layers);
                uint2 texel = min(uint2(i.uv * float2(w, h)), uint2(w - 1, h - 1));
                // 補間しないで、その画素の値をそのまま読む（左目 = 0 枚目）
                float depth = _EnvironmentDepthTexture.Load(int4(texel, 0, 0));
                // その画素を Sample で読むときの uv（画素の中心）
                float2 uv = (float2(texel) + 0.5) / float2(w, h);
                return float4(depth, uv.x, uv.y, 1.0);
            }
            ENDCG
        }
    }
}
