// Diminished Reality: mask box.
// Draws no color and no depth. It only writes _StencilRef into the stencil
// buffer for the pixels this mesh covers, so passthrough stays visible here
// until a later shader (e.g. DR/StencilReadUnlit) draws where stencil == _StencilRef.
Shader "DR/StencilMask"
{
    Properties
    {
        [IntRange] _StencilRef ("Stencil Ref", Range(1, 255)) = 1
    }

    SubShader
    {
        // Draw before normal geometry so later passes can test against the stencil.
        Tags { "RenderType"="Opaque" "Queue"="Geometry-10" "IgnoreProjector"="True" }

        Pass
        {
            ColorMask 0   // write no color: the box itself is invisible
            ZWrite Off    // write no depth: do not occlude anything
            Cull Off      // front and back faces, so it still works with the head inside the box

            Stencil
            {
                Ref [_StencilRef]
                Comp Always
                Pass Replace
            }

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"

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
                return 0;
            }
            ENDCG
        }
    }
}
