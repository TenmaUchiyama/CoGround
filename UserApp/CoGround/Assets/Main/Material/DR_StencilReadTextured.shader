// Diminished Reality: background from a scanned, textured mesh (e.g. the desk scan).
// Unlit texture (scan textures already contain the room's lighting), drawn only
// where stencil == _StencilRef, i.e. only inside the area a DR/StencilMask box marked.
// Everywhere else nothing is drawn, so passthrough stays visible.
Shader "DR/StencilReadTextured"
{
    Properties
    {
        _MainTex ("Texture", 2D) = "white" {}
        _Color ("Tint", Color) = (1, 1, 1, 1)
        [IntRange] _StencilRef ("Stencil Ref", Range(1, 255)) = 1
    }

    SubShader
    {
        // Draw after DR/StencilMask (Geometry-10).
        Tags { "RenderType"="Opaque" "Queue"="Geometry+10" "IgnoreProjector"="True" }

        Pass
        {
            Cull Off

            Stencil
            {
                Ref [_StencilRef]
                Comp Equal
                Pass Keep
            }

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            float4 _MainTex_ST;
            fixed4 _Color;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert (appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = TRANSFORM_TEX(v.uv, _MainTex);
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                fixed4 c = tex2D(_MainTex, i.uv) * _Color;
                // Alpha 1 so it covers passthrough on Quest.
                return fixed4(c.rgb, 1);
            }
            ENDCG
        }
    }
}
