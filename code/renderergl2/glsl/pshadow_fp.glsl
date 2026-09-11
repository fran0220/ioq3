uniform sampler2D u_ShadowMap;

uniform vec3      u_LightForward;
uniform vec3      u_LightUp;
uniform vec3      u_LightRight;
uniform vec4      u_LightOrigin;
uniform float     u_LightRadius;
varying vec3      var_Position;
varying vec3      var_Normal;

float SampleProjectedShadow(vec2 st)
{
#if defined(USE_PCF)
	// Interpolate coverage, not depth. Equal-weight nearest taps jump in 25%
	// steps as the receiver moves; texel-centred bilinear PCF uses the same
	// four fetches without those quantized dark fringes.
	vec2 texel = st * PSHADOW_MAP_SIZE - vec2(0.5);
	vec2 weight = fract(texel);
	vec2 base = (floor(texel) + vec2(0.5)) / PSHADOW_MAP_SIZE;
	float a = float(texture2D(u_ShadowMap, base).r != 1.0);
	float b = float(texture2D(u_ShadowMap, base + vec2(1.0, 0.0) / PSHADOW_MAP_SIZE).r != 1.0);
	float c = float(texture2D(u_ShadowMap, base + vec2(0.0, 1.0) / PSHADOW_MAP_SIZE).r != 1.0);
	float d = float(texture2D(u_ShadowMap, base + vec2(1.0, 1.0) / PSHADOW_MAP_SIZE).r != 1.0);
	return mix(mix(a, b, weight.x), mix(c, d, weight.x), weight.y);
#else
	return float(texture2D(u_ShadowMap, st).r != 1.0);
#endif
}

void main()
{
	vec3 lightToPos = var_Position - u_LightOrigin.xyz;
	vec2 st = vec2(-dot(u_LightRight, lightToPos), dot(u_LightUp, lightToPos));
	
	float fade = length(st);
	
#if defined(USE_DISCARD)
	if (fade >= 1.0)
	{
		discard;
	}
#endif

	fade = clamp(8.0 - fade * 8.0, 0.0, 1.0);
	
	st = st * 0.5 + vec2(0.5);

#if defined(USE_SOLID_PSHADOWS)
	float intensity = max(sign(u_LightRadius - length(lightToPos)), 0.0);
#else
	float intensity = clamp((1.0 - dot(lightToPos, lightToPos) / (u_LightRadius * u_LightRadius)) * 2.0, 0.0, 1.0);
#endif
	
	float lightDist = length(lightToPos);
	float dist;

#if defined(USE_DISCARD)
	if (dot(u_LightForward, lightToPos) <= 0.0)
	{
		discard;
	}

	if (dot(var_Normal, lightToPos) > 0.0)
	{
		discard;
	}
#else
	intensity *= max(sign(dot(u_LightForward, lightToPos)), 0.0);
	intensity *= max(sign(-dot(var_Normal, lightToPos)), 0.0);
#endif

	intensity *= fade;

	float part = SampleProjectedShadow(st);

	if (part <= 0.0)
	{
		discard;
	}

	intensity *= part;

	gl_FragColor.rgb = vec3(0);
	gl_FragColor.a = clamp(intensity, 0.0, 0.75);
}
