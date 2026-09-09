/* Exercise the production header builder without a GL context or game data. */
#include <assert.h>
#include "../tr_glsl.c"

glconfig_t glConfig = { .vidWidth = 800, .vidHeight = 600 };
glRefConfig_t glRefConfig;
int qglesMajorVersion;
static cvar_t disabled;
cvar_t *r_pbr = &disabled, *r_cubeMapping = &disabled, *r_cubemapSize = &disabled;

void QDECL Com_Error(int level, const char *format, ...)
{
	abort();
}

int main(void)
{
	char header[8192];
	int stage;
	for (stage = 0; stage < 2; stage++)
	{
		GLenum type = stage ? GL_FRAGMENT_SHADER : GL_VERTEX_SHADER;
		qglesMajorVersion = 3;
		glRefConfig.glslMajorVersion = 3;
		glRefConfig.glslMinorVersion = 0;
		GLSL_GetShaderHeader(type, "#define TEST_EXTRA\n", header, sizeof(header));
		assert(strncmp(header, "#version 300 es\n#define TEST_EXTRA\n", 34) == 0);
		assert(strstr(header, "precision highp float;\n"));
		assert(!strstr(header, "precision mediump float;\n"));

		qglesMajorVersion = 2;
		glRefConfig.glslMajorVersion = 1;
		glRefConfig.glslMinorVersion = 0;
		GLSL_GetShaderHeader(type, NULL, header, sizeof(header));
		assert(strncmp(header, "#version 100\n", 13) == 0);
		assert(strstr(header, "precision mediump float;\n"));
		assert(!strstr(header, "precision highp float;\n"));

		qglesMajorVersion = 0;
		glRefConfig.glslMajorVersion = 1;
		glRefConfig.glslMinorVersion = 50;
		GLSL_GetShaderHeader(type, NULL, header, sizeof(header));
		assert(strncmp(header, "#version 150\n", 13) == 0);
		assert(!strstr(header, "precision "));
	}
	puts("PASS: ES3 vertex/fragment highp, ES2 mediump, desktop unchanged");
	return 0;
}
