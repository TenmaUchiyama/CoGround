// Diminished Reality: background from a scanned, textured mesh (e.g. the desk scan).
// Unlit texture (scan textures already contain the room's lighting), drawn only
// where stencil == _StencilRef, i.e. only inside the area a DR/StencilMask box marked.
// Everywhere else nothing is drawn, so passthrough stays visible.
//
// To make the patch less visible against passthrough:
//   - Edge feather: alpha falls off near the silhouette of the mask box, so the patch fades
//     into passthrough instead of ending with a hard cut. Needs DRMaskShaderGlobals on the
//     mask box (it sends the box transform). Without it, or with Feather Width 0, alpha is 1.
//   - Blur + grain: passthrough is soft and noisy, a sharp clean scan stands out.
//   - Brightness / contrast / saturation on top of the tint, to match passthrough colors.
Shader "DR/StencilReadTextured"
{
    Properties
    {
        _MainTex ("Texture", 2D) = "white" {}
        _Color ("Tint", Color) = (1, 1, 1, 1)
        [IntRange] _StencilRef ("Stencil Ref", Range(1, 255)) = 1

        [Header(Edge feather (needs DRMaskShaderGlobals on the mask box))]
        _FeatherWidth ("Feather Width (m, 0 = off)", Range(0, 0.2)) = 0.03

        [Header(Look like passthrough)]
        _BlurBias ("Blur (mip bias)", Range(0, 4)) = 1
        _Grain ("Grain", Range(0, 0.2)) = 0.03

        [Header(Color)]
        _Brightness ("Brightness", Range(0, 2)) = 1
        _Contrast ("Contrast", Range(0, 2)) = 1
        _Saturation ("Saturation", Range(0, 2)) = 1
    }

    SubShader
    {
        // Draw after DR/StencilMask (Geometry-10).
        Tags { "RenderType"="Opaque" "Queue"="Geometry+10" "IgnoreProjector"="True" }

        Pass
        {
            Cull Off
            // Alpha < 1 lets passthrough show through (Quest composites the eye buffer over passthrough by alpha).
            Blend SrcAlpha OneMinusSrcAlpha, One OneMinusSrcAlpha

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
            float _FeatherWidth;
            float _BlurBias;
            float _Grain;
            float _Brightness;
            float _Contrast;
            float _Saturation;

            // Set by DRMaskShaderGlobals (mask box transforms). _DRMaskCount = 0 when no box is active
            // (or there are more boxes than DR_MASK_MAX): then there is no feather.
            #define DR_MASK_MAX 8
            float4x4 _DRMaskWorldToLocal[DR_MASK_MAX];
            float _DRMaskCount;

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
                float3 worldPos : TEXCOORD1;
                float3 camPos : TEXCOORD2; // per eye, computed in the vertex stage where the eye index is set
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
                o.worldPos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.camPos = _WorldSpaceCameraPos;
                return o;
            }

            // Length (m) of the view ray's path through the mask box (a unit cube in its local space).
            // It goes to 0 at the box silhouette, so it works as a soft edge.
            float ChordThroughMask(float4x4 worldToLocal, float3 camPos, float3 worldPos)
            {
                float3 ro = mul(worldToLocal, float4(camPos, 1)).xyz;
                float3 p  = mul(worldToLocal, float4(worldPos, 1)).xyz;
                float3 rd = p - ro;
                // Avoid division by zero on axis-aligned rays.
                rd = sign(rd) * max(abs(rd), 1e-6) + (rd == 0) * 1e-6;
                float3 t1 = (-0.5 - ro) / rd;
                float3 t2 = ( 0.5 - ro) / rd;
                float3 tLo = min(t1, t2);
                float3 tHi = max(t1, t2);
                float tEnter = max(max(max(tLo.x, tLo.y), tLo.z), 0); // 0: camera inside the box
                float tExit  = min(min(tHi.x, tHi.y), tHi.z);
                // t is the same along the ray in local and world space (affine), so scale by the world length.
                return max(tExit - tEnter, 0) * length(worldPos - camPos);
            }

            float Hash(float2 p)
            {
                return frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453);
            }

            fixed4 frag (v2f i) : SV_Target
            {
                fixed3 c = tex2Dbias(_MainTex, float4(i.uv, 0, _BlurBias)).rgb * _Color.rgb;

                // Color: brightness, contrast around mid grey, saturation around luminance.
                c *= _Brightness;
                c = (c - 0.5) * _Contrast + 0.5;
                float luma = dot(c, float3(0.299, 0.587, 0.114));
                c = lerp(luma.xxx, c, _Saturation);

                // Grain that changes every frame, like camera noise.
                c += (Hash(i.pos.xy + frac(_Time.y * 7.13) * 100) - 0.5) * _Grain;

                float alpha = 1;
                int maskCount = (int)min(_DRMaskCount + 0.5, DR_MASK_MAX);
                if (maskCount > 0 && _FeatherWidth > 0)
                {
                    // Several boxes: the pixel is as opaque as the box that covers it best.
                    float chord = 0;
                    for (int m = 0; m < DR_MASK_MAX; m++)
                    {
                        if (m < maskCount)
                            chord = max(chord, ChordThroughMask(_DRMaskWorldToLocal[m], i.camPos, i.worldPos));
                    }
                    alpha = smoothstep(0, _FeatherWidth, chord);
                }

                return fixed4(saturate(c), alpha);
            }
            ENDCG
        }
    }
}
