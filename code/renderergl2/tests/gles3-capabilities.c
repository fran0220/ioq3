/* Renderer-only integration test. Uses the production extension initializer,
 * DSA fallbacks and pixel converter with a real SDL GLES3/WebGL2 context.
 * Failure injection replaces only the indicated driver/loader result. */
#include <SDL.h>
#include <assert.h>
#include "../tr_local.h"
#include "../tr_dsa.h"

refimport_t ri;
glRefConfig_t glRefConfig;
int qglMajorVersion, qglMinorVersion, qglesMajorVersion, qglesMinorVersion;
#define GLE(ret, name, ...) name##proc *qgl##name;
QGL_1_1_PROCS;
QGL_DESKTOP_1_1_PROCS;
QGL_1_3_PROCS;
QGL_1_5_PROCS;
QGL_2_0_PROCS;
QGL_3_0_PROCS;
QGL_ARB_occlusion_query_PROCS;
QGL_ARB_framebuffer_object_PROCS;
QGL_ARB_vertex_array_object_PROCS;
QGL_EXT_direct_state_access_PROCS;
#undef GLE

#define CVAR(name) static cvar_t value_##name = { .integer = 1 }; cvar_t *name = &value_##name;
CVAR(r_allowExtensions)
CVAR(r_ext_framebuffer_object)
CVAR(r_ext_texture_float)
CVAR(r_arb_vertex_array_object)
CVAR(r_arb_seamless_cube_map)
CVAR(r_ext_compressed_textures)
CVAR(r_ext_direct_state_access)
#undef CVAR

static const char *missingProc;
static qboolean hideFloat, failStatus, failAllocation;
static int disabledEffects;
static CheckFramebufferStatusproc *realStatus;
static TexImage2Dproc *realImage;

static GLenum APIENTRY TestStatus(GLenum target)
{
	return failStatus ? GL_FRAMEBUFFER_UNSUPPORTED : realStatus(target);
}

static void APIENTRY TestImage(GLenum target, GLint level, GLint internalFormat,
	GLsizei width, GLsizei height, GLint border, GLenum format, GLenum type, const void *data)
{
	realImage(target, level, failAllocation ? 0 : internalFormat, width, height, border, format, type, data);
}

static void *TestGetProc(const char *name)
{
	if (missingProc && !strcmp(name, missingProc)) return NULL;
	if (!strcmp(name, "glCheckFramebufferStatus")) return (void *)TestStatus;
	return SDL_GL_GetProcAddress(name);
}

static SDL_bool TestExtension(const char *name)
{
	if (hideFloat && !strcmp(name, "GL_EXT_color_buffer_float")) return SDL_FALSE;
	return SDL_GL_ExtensionSupported(name);
}

#define SDL_GL_GetProcAddress TestGetProc
#define SDL_GL_ExtensionSupported TestExtension
#include "../tr_extensions.c"
#undef SDL_GL_GetProcAddress
#undef SDL_GL_ExtensionSupported

static void QDECL Print(int level, const char *format, ...)
{
	va_list args;
	(void)level;
	va_start(args, format);
	vprintf(format, args);
	va_end(args);
}

void QDECL Com_Error(int level, const char *format, ...)
{
	va_list args;
	(void)level;
	va_start(args, format);
	vfprintf(stderr, format, args);
	va_end(args);
	abort();
}

static void Set(const char *name, const char *value)
{
	assert(!strcmp(value, "0"));
	assert(!strcmp(name, "r_ssao") || !strcmp(name, "r_shadowBlur"));
	disabledEffects++;
}

static void Init(void)
{
	disabledEffects = 0;
	GLimp_InitExtraExtensions();
	assert(qglGetError() == GL_NO_ERROR);
}

int main(int argc, char **argv)
{
	SDL_Window *window;
	SDL_GLContext context;
	GLuint framebuffers[2], texture, renderbuffer, vao;
	GLint value;
	byte pixel[4];
	const byte source[8] = { 0, 51, 153, 255, 255, 102, 204, 0 };
	const float expected[8] = { 0, .2f, .6f, 1, 1, .4f, .8f, 0 };
	float converted[9];
	int i;
	(void)argc; (void)argv;
	assert(SDL_Init(SDL_INIT_VIDEO) == 0);
	SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
	SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
	SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
	SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 0);
	window = SDL_CreateWindow("GL2 capability test", 0, 0, 64, 64, SDL_WINDOW_OPENGL);
	assert(window);
	context = SDL_GL_CreateContext(window);
	assert(context);
#define GLE(ret, name, ...) qgl##name = (name##proc *) SDL_GL_GetProcAddress("gl" #name);
	QGL_1_1_PROCS;
	QGL_1_3_PROCS;
	QGL_1_5_PROCS;
	QGL_2_0_PROCS;
	QGL_ARB_framebuffer_object_PROCS;
	QGL_ARB_vertex_array_object_PROCS;
#undef GLE
	printf("GL_VERSION=%s\n", qglGetString(GL_VERSION));
	assert(strstr((const char *)qglGetString(GL_VERSION), "OpenGL ES 3"));
	qglesMajorVersion = 3;
	realStatus = qglCheckFramebufferStatus;
	realImage = qglTexImage2D;
	qglTexImage2D = TestImage;
	ri.Printf = Print;
	ri.Error = Com_Error;
	ri.Cvar_Set = Set;

	// Distinct read/draw and nonzero texture/VAO bindings detect incomplete
	// state restoration; default-zero bindings would hide this bug.
	qglGenFramebuffers(2, framebuffers);
	qglGenTextures(1, &texture);
	qglGenVertexArrays(1, &vao);
	qglBindFramebuffer(GL_DRAW_FRAMEBUFFER, framebuffers[0]);
	qglBindFramebuffer(GL_READ_FRAMEBUFFER, framebuffers[1]);
	qglBindTexture(GL_TEXTURE_2D, texture);
	qglBindVertexArray(vao);
	Init();
	assert(glRefConfig.framebufferObject && glRefConfig.framebufferBlit && glRefConfig.vertexArrayObject);
	assert(!glRefConfig.framebufferMultisample);
	qglGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &value); assert(value == (GLint)framebuffers[0]);
	qglGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &value); assert(value == (GLint)framebuffers[1]);
	qglGetIntegerv(GL_TEXTURE_BINDING_2D, &value); assert(value == (GLint)texture);
	qglGetIntegerv(GL_VERTEX_ARRAY_BINDING, &value); assert(value == (GLint)vao);

	converted[8] = 12345;
	R_ConvertTextureFormat(source, 1, 2, GL_RGBA, GL_FLOAT, (byte *)converted);
	for (i = 0; i < 8; i++) assert(fabsf(converted[i] - expected[i]) < .00001f);
	assert(converted[8] == 12345);
	if (glRefConfig.textureFloat)
	{
		qglTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, 1, 2, 0, GL_RGBA, GL_FLOAT, converted);
		qglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
		qglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
		qglFramebufferTexture2D(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0);
		assert(qglCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE);
		assert(qglGetError() == GL_NO_ERROR);
	}

	// Exercise the actual DSA renderbuffer wrappers and core blit, then read
	// back asymmetric color bytes. Capability flags alone are not the test.
	GL_BindNullFramebuffers();
	qglGenRenderbuffers(1, &renderbuffer);
	qglNamedRenderbufferStorageEXT(renderbuffer, GL_RGBA8, 4, 4);
	qglNamedFramebufferRenderbufferEXT(framebuffers[0], GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, renderbuffer);
	assert(qglCheckNamedFramebufferStatusEXT(framebuffers[0], GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE);
	qglClearColor(.2f, .4f, .8f, 1);
	qglClear(GL_COLOR_BUFFER_BIT);
	GL_BindFramebuffer(GL_READ_FRAMEBUFFER, framebuffers[0]);
	GL_BindFramebuffer(GL_DRAW_FRAMEBUFFER, 0);
	qglBlitFramebuffer(0, 0, 4, 4, 0, 0, 64, 64, GL_COLOR_BUFFER_BIT, GL_NEAREST);
	GL_BindFramebuffer(GL_READ_FRAMEBUFFER, 0);
	qglReadPixels(32, 32, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
	assert(abs(pixel[0] - 51) <= 1 && abs(pixel[1] - 102) <= 1 && abs(pixel[2] - 204) <= 1 && pixel[3] == 255);
	assert(qglGetError() == GL_NO_ERROR);

	hideFloat = qtrue; Init();
	assert(glRefConfig.framebufferObject && !glRefConfig.textureFloat && disabledEffects == 2);
	hideFloat = qfalse;
	failStatus = qtrue; Init();
	assert(!glRefConfig.framebufferObject && !glRefConfig.framebufferBlit && !glRefConfig.textureFloat);
	failStatus = qfalse;
	failAllocation = qtrue; Init();
	assert(!glRefConfig.framebufferObject && !glRefConfig.textureFloat);
	failAllocation = qfalse;
	missingProc = "glFramebufferTexture2D"; Init();
	assert(!glRefConfig.framebufferObject && glRefConfig.vertexArrayObject);
	missingProc = "glBindVertexArray"; Init();
	assert(glRefConfig.framebufferObject && !glRefConfig.vertexArrayObject);
	missingProc = NULL;
	r_ext_texture_float->integer = 0; Init();
	assert(glRefConfig.framebufferObject && !glRefConfig.textureFloat);
	r_ext_texture_float->integer = 1;
	r_ext_framebuffer_object->integer = 0; Init();
	assert(!glRefConfig.framebufferObject && !glRefConfig.textureFloat);
	r_ext_framebuffer_object->integer = 1;
	r_arb_vertex_array_object->integer = 0; Init();
	assert(!glRefConfig.vertexArrayObject && glRefConfig.framebufferObject);
	r_arb_vertex_array_object->integer = 1;
	r_allowExtensions->integer = 0; Init();
	assert(!glRefConfig.framebufferObject && !glRefConfig.vertexArrayObject && !glRefConfig.textureFloat);
	r_allowExtensions->integer = 1;
	// Version gate: an ES2 context must never run the new core ES3 probes.
	qglesMajorVersion = 2;
	GLimp_InitGLES3Framebuffers();
	assert(!glRefConfig.framebufferObject && !glRefConfig.vertexArrayObject && !glRefConfig.textureFloat);
	qglesMajorVersion = 3;
	Init();
	qglDeleteFramebuffers(2, framebuffers);
	qglDeleteRenderbuffers(1, &renderbuffer);
	qglDeleteTextures(1, &texture);
	qglDeleteVertexArrays(1, &vao);
	printf("PASS: GLES3 capabilities, bindings, float conversion, DSA/blit/readback and failure fallbacks\n");
	SDL_GL_DeleteContext(context);
	SDL_DestroyWindow(window);
	SDL_Quit();
	return 0;
}
