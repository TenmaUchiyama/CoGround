// Diminished Reality: draws a flat color only where stencil == _StencilRef,
// i.e. only inside the area a DR/StencilMask box has marked.
// Use it to check that the mask works, and as a stand-in for the real background
// (Gaussian Splat, captured texture, ...) until that is in place.
Shader "DR/StencilReadUnlit"
{
    Properties
    {
        _Color ("Color", Color) = (0.5, 0.5, 0.5, 1)
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

            fixed4 _Color;

            struct appdata
            {
                float4 vertex : POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert (appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                // Alpha 1 so it covers passthrough on Quest.
                return fixed4(_Color.rgb, 1);
            }
            ENDCG
        }
    }
}
