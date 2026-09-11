uniform vec4  u_LightOrigin;
uniform float u_LightRadius;

varying vec3  var_Position;

void main()
{
#if defined(USE_DEPTH)
	float depth = length(u_LightOrigin.xyz - var_Position) / u_LightRadius;
	// Exact UNORM8 byte packing, matching the radial cube reader. Encoding
	// fractions with /256 before RGBA8 quantization introduces carry errors.
	float distanceBits = floor(clamp(depth, 0.0, 1.0) * 16777215.0);
	vec3 bytes = mod(floor(distanceBits / vec3(65536.0, 256.0, 1.0)), 256.0);
	gl_FragColor = vec4(bytes / 255.0, 1.0);
#else
	gl_FragColor = vec4(0, 0, 0, 1);
#endif
}
