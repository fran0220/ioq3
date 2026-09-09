/*
===========================================================================
Copyright (C) 2011 James Canete (use.less01@gmail.com)

This file is part of Quake III Arena source code.

Quake III Arena source code is free software; you can redistribute it
and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 2 of the License,
or (at your option) any later version.

Quake III Arena source code is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Quake III Arena source code; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
===========================================================================
*/
// tr_extensions.c - extensions needed by the renderer not in sdl_glimp.c

#ifdef USE_INTERNAL_SDL_HEADERS
#	include "SDL.h"
#else
#	include <SDL.h>
#endif

#include "tr_local.h"
#include "tr_dsa.h"

// Called before GL_SetDefaultState: use raw bindings and restore them so the
// DSA cache and the caller's GL state are not changed by capability probes.
static qboolean GLimp_ProbeGLESFramebuffer(GLenum internalFormat, GLenum format, GLenum type)
{
	GLuint framebuffer = 0, textures[2] = { 0, 0 };
	GLint drawFramebuffer, readFramebuffer, texture;
	GLenum status, error;
	qboolean valid;

	qglGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &drawFramebuffer);
	qglGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &readFramebuffer);
	qglGetIntegerv(GL_TEXTURE_BINDING_2D, &texture);
	qglGenFramebuffers(1, &framebuffer);
	qglBindFramebuffer(GL_FRAMEBUFFER, framebuffer);
	qglGenTextures(2, textures);
	qglBindTexture(GL_TEXTURE_2D, textures[0]);
	qglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	qglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	qglTexImage2D(GL_TEXTURE_2D, 0, internalFormat, 4, 4, 0, format, type, NULL);
	qglFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, textures[0], 0);
	qglBindTexture(GL_TEXTURE_2D, textures[1]);
	qglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	qglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	qglTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, 4, 4, 0, GL_DEPTH_COMPONENT, GL_UNSIGNED_INT, NULL);
	qglFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, textures[1], 0);
	status = qglCheckFramebufferStatus(GL_FRAMEBUFFER);
	valid = framebuffer && textures[0] && textures[1] && status == GL_FRAMEBUFFER_COMPLETE;
	while ((error = qglGetError()) != GL_NO_ERROR)
	{
		ri.Printf(PRINT_WARNING, "...GLES framebuffer format 0x%X probe error 0x%X\n", internalFormat, error);
		valid = qfalse;
	}
	if (!valid)
		ri.Printf(PRINT_WARNING, "...GLES framebuffer format 0x%X unavailable (status 0x%X)\n", internalFormat, status);

	qglBindFramebuffer(GL_DRAW_FRAMEBUFFER, drawFramebuffer);
	qglBindFramebuffer(GL_READ_FRAMEBUFFER, readFramebuffer);
	qglBindTexture(GL_TEXTURE_2D, texture);
	qglDeleteTextures(2, textures);
	qglDeleteFramebuffers(1, &framebuffer);
	return valid;
}

static void GLimp_InitGLES3Framebuffers(void)
{
	qboolean loaded = qtrue;
	GLenum error;
	GLuint vao = 0;
	GLint oldVao;

	glRefConfig.framebufferObject = qfalse;
	glRefConfig.framebufferBlit = qfalse;
	glRefConfig.framebufferMultisample = qfalse;
	glRefConfig.vertexArrayObject = qfalse;
	glRefConfig.textureFloat = qfalse;

	// A non-NULL proc address alone is not a GLES version/capability check.
	if (qglesMajorVersion < 3 || !r_allowExtensions->integer)
		return;

	while ((error = qglGetError()) != GL_NO_ERROR)
		ri.Printf(PRINT_WARNING, "...GL error before GLES3 capability probes: 0x%X\n", error);

#define GLE(ret, name, ...) qgl##name = (name##proc *) SDL_GL_GetProcAddress("gl" #name); if (!qgl##name) loaded = qfalse;
	QGL_ARB_vertex_array_object_PROCS;
#undef GLE
	if (loaded && r_arb_vertex_array_object->integer)
	{
		qglGetIntegerv(GL_VERTEX_ARRAY_BINDING, &oldVao);
		qglGenVertexArrays(1, &vao);
		qglBindVertexArray(vao);
		glRefConfig.vertexArrayObject = vao != 0;
		while ((error = qglGetError()) != GL_NO_ERROR)
			glRefConfig.vertexArrayObject = qfalse;
		qglBindVertexArray(oldVao);
		qglDeleteVertexArrays(1, &vao);
	}
	ri.Printf(PRINT_ALL, "...GLES3 VAO %s\n", glRefConfig.vertexArrayObject ? "enabled" : "disabled");

	loaded = qtrue;
#define GLE(ret, name, ...) qgl##name = (name##proc *) SDL_GL_GetProcAddress("gl" #name); if (!qgl##name) loaded = qfalse;
	QGL_ARB_framebuffer_object_PROCS;
#undef GLE
	if (loaded && r_ext_framebuffer_object->integer)
	{
		qglGetIntegerv(GL_MAX_RENDERBUFFER_SIZE, &glRefConfig.maxRenderbufferSize);
		qglGetIntegerv(GL_MAX_COLOR_ATTACHMENTS, &glRefConfig.maxColorAttachments);
		// FBO_t has sixteen color attachment slots.
		glRefConfig.maxColorAttachments = MIN(glRefConfig.maxColorAttachments, 16);
		glRefConfig.framebufferObject = GLimp_ProbeGLESFramebuffer(GL_RGBA8, GL_RGBA, GL_UNSIGNED_BYTE);
		glRefConfig.framebufferObject &= glRefConfig.maxRenderbufferSize > 0 && glRefConfig.maxColorAttachments > 0;
		glRefConfig.framebufferBlit = glRefConfig.framebufferObject;
	}
	ri.Printf(PRINT_ALL, "...GLES3 framebuffer/blit %s\n", glRefConfig.framebufferObject ? "enabled" : "disabled");

	// GLES3/WebGL2 float *textures* are core, float color renderability is not.
	// Require both formats used by this renderer, not just an extension string.
	if (glRefConfig.framebufferObject && r_ext_texture_float->integer &&
		SDL_GL_ExtensionSupported("GL_EXT_color_buffer_float"))
	{
		glRefConfig.textureFloat = GLimp_ProbeGLESFramebuffer(GL_RGBA16F, GL_RGBA, GL_FLOAT) &&
			GLimp_ProbeGLESFramebuffer(GL_R32F, GL_RED, GL_FLOAT);
	}
	ri.Printf(PRINT_ALL, "...GLES3 float render targets %s\n", glRefConfig.textureFloat ? "enabled" : "disabled (using RGBA8)");
	if (!glRefConfig.textureFloat)
	{
		// These effects allocate R32F even when HDR itself uses the RGBA8 fallback.
		ri.Cvar_Set("r_ssao", "0");
		ri.Cvar_Set("r_shadowBlur", "0");
	}
	// Do not infer format-specific MSAA counts from GL_MAX_SAMPLES. In
	// particular EXT_color_buffer_float does not guarantee float MSAA storage.
	ri.Printf(PRINT_ALL, "...GLES3 framebuffer MSAA disabled (format-specific sample validation required)\n");
}

void GLimp_InitExtraExtensions(void)
{
	char *extension;
	const char* result[3] = { "...ignoring %s\n", "...using %s\n", "...%s not found\n" };
	qboolean q_gl_version_at_least_3_0;
	qboolean q_gl_version_at_least_3_2;

	q_gl_version_at_least_3_0 = QGL_VERSION_ATLEAST( 3, 0 );
	q_gl_version_at_least_3_2 = QGL_VERSION_ATLEAST( 3, 2 );

	// Check if we need Intel graphics specific fixes.
	glRefConfig.intelGraphics = qfalse;
	if (strstr((char *)qglGetString(GL_RENDERER), "Intel"))
		glRefConfig.intelGraphics = qtrue;

	if (qglesMajorVersion)
	{
		glRefConfig.vaoCacheGlIndexType = GL_UNSIGNED_SHORT;
		glRefConfig.vaoCacheGlIndexSize = sizeof(unsigned short);
	}
	else
	{
		glRefConfig.vaoCacheGlIndexType = GL_UNSIGNED_INT;
		glRefConfig.vaoCacheGlIndexSize = sizeof(unsigned int);
	}

	// set DSA fallbacks
#define GLE(ret, name, ...) qgl##name = GLDSA_##name;
	QGL_EXT_direct_state_access_PROCS;
#undef GLE

	// GL function loader, based on https://gist.github.com/rygorous/16796a0c876cf8a5f542caddb55bce8a
#define GLE(ret, name, ...) qgl##name = (name##proc *) SDL_GL_GetProcAddress("gl" #name);

	//
	// OpenGL ES extensions
	//
	if (qglesMajorVersion)
	{
		GLimp_InitGLES3Framebuffers();
		if (!r_allowExtensions->integer)
			goto done;

		extension = "GL_EXT_occlusion_query_boolean";
		if (qglesMajorVersion >= 3 || SDL_GL_ExtensionSupported(extension))
		{
			glRefConfig.occlusionQuery = qtrue;
			glRefConfig.occlusionQueryTarget = GL_ANY_SAMPLES_PASSED;

			if (qglesMajorVersion >= 3) {
				QGL_ARB_occlusion_query_PROCS;
			} else {
				// GL_EXT_occlusion_query_boolean uses EXT suffix
#undef GLE
#define GLE(ret, name, ...) qgl##name = (name##proc *) SDL_GL_GetProcAddress("gl" #name "EXT");

				QGL_ARB_occlusion_query_PROCS;

#undef GLE
#define GLE(ret, name, ...) qgl##name = (name##proc *) SDL_GL_GetProcAddress("gl" #name);
			}

			ri.Printf(PRINT_ALL, result[glRefConfig.occlusionQuery], extension);
		}
		else
		{
			ri.Printf(PRINT_ALL, result[2], extension);
		}

		// GL_NV_read_depth
		extension = "GL_NV_read_depth";
		if (SDL_GL_ExtensionSupported(extension))
		{
			glRefConfig.readDepth = qtrue;
			ri.Printf(PRINT_ALL, result[glRefConfig.readDepth], extension);
		}
		else
		{
			ri.Printf(PRINT_ALL, result[2], extension);
		}

		// GL_NV_read_stencil
		extension = "GL_NV_read_stencil";
		if (SDL_GL_ExtensionSupported(extension))
		{
			glRefConfig.readStencil = qtrue;
			ri.Printf(PRINT_ALL, result[glRefConfig.readStencil], extension);
		}
		else
		{
			ri.Printf(PRINT_ALL, result[2], extension);
		}

		// GL_EXT_shadow_samplers
		extension = "GL_EXT_shadow_samplers";
		if (qglesMajorVersion >= 3 || SDL_GL_ExtensionSupported(extension))
		{
			glRefConfig.shadowSamplers = qtrue;
			ri.Printf(PRINT_ALL, result[glRefConfig.shadowSamplers], extension);
		}
		else
		{
			ri.Printf(PRINT_ALL, result[2], extension);
		}

		// GL_OES_standard_derivatives
		extension = "GL_OES_standard_derivatives";
		if (qglesMajorVersion >= 3 || SDL_GL_ExtensionSupported(extension))
		{
			glRefConfig.standardDerivatives = qtrue;
			ri.Printf(PRINT_ALL, result[glRefConfig.standardDerivatives], extension);
		}
		else
		{
			ri.Printf(PRINT_ALL, result[2], extension);
		}

		// GL_OES_element_index_uint
		extension = "GL_OES_element_index_uint";
		if (qglesMajorVersion >= 3 || SDL_GL_ExtensionSupported(extension))
		{
			glRefConfig.vaoCacheGlIndexType = GL_UNSIGNED_INT;
			glRefConfig.vaoCacheGlIndexSize = sizeof(unsigned int);
			ri.Printf(PRINT_ALL, result[1], extension);
		}
		else
		{
			ri.Printf(PRINT_ALL, result[2], extension);
		}

		goto done;
	}

	// OpenGL 1.5 - GL_ARB_occlusion_query
	glRefConfig.occlusionQuery = qtrue;
	glRefConfig.occlusionQueryTarget = GL_SAMPLES_PASSED;
	QGL_ARB_occlusion_query_PROCS;

	// OpenGL 3.0 - GL_ARB_framebuffer_object
	extension = "GL_ARB_framebuffer_object";
	glRefConfig.framebufferObject = qfalse;
	glRefConfig.framebufferBlit = qfalse;
	glRefConfig.framebufferMultisample = qfalse;
	if (q_gl_version_at_least_3_0 || SDL_GL_ExtensionSupported(extension))
	{
		glRefConfig.framebufferObject = !!r_ext_framebuffer_object->integer;
		glRefConfig.framebufferBlit = qtrue;
		glRefConfig.framebufferMultisample = qtrue;

		qglGetIntegerv(GL_MAX_RENDERBUFFER_SIZE, &glRefConfig.maxRenderbufferSize);
		qglGetIntegerv(GL_MAX_COLOR_ATTACHMENTS, &glRefConfig.maxColorAttachments);

		QGL_ARB_framebuffer_object_PROCS;

		ri.Printf(PRINT_ALL, result[glRefConfig.framebufferObject], extension);
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

	// OpenGL 3.0 - GL_ARB_vertex_array_object
	extension = "GL_ARB_vertex_array_object";
	glRefConfig.vertexArrayObject = qfalse;
	if (q_gl_version_at_least_3_0 || SDL_GL_ExtensionSupported(extension))
	{
		if (q_gl_version_at_least_3_0)
		{
			// force VAO, core context requires it
			glRefConfig.vertexArrayObject = qtrue;
		}
		else
		{
			glRefConfig.vertexArrayObject = !!r_arb_vertex_array_object->integer;
		}

		QGL_ARB_vertex_array_object_PROCS;

		ri.Printf(PRINT_ALL, result[glRefConfig.vertexArrayObject], extension);
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

	// OpenGL 3.0 - GL_ARB_texture_float
	extension = "GL_ARB_texture_float";
	glRefConfig.textureFloat = qfalse;
	if (q_gl_version_at_least_3_0 || SDL_GL_ExtensionSupported(extension))
	{
		glRefConfig.textureFloat = !!r_ext_texture_float->integer;

		ri.Printf(PRINT_ALL, result[glRefConfig.textureFloat], extension);
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

	// OpenGL 3.2 - GL_ARB_depth_clamp
	extension = "GL_ARB_depth_clamp";
	glRefConfig.depthClamp = qfalse;
	if (q_gl_version_at_least_3_2 || SDL_GL_ExtensionSupported(extension))
	{
		glRefConfig.depthClamp = qtrue;

		ri.Printf(PRINT_ALL, result[glRefConfig.depthClamp], extension);
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

	// OpenGL 3.2 - GL_ARB_seamless_cube_map
	extension = "GL_ARB_seamless_cube_map";
	glRefConfig.seamlessCubeMap = qfalse;
	if (q_gl_version_at_least_3_2 || SDL_GL_ExtensionSupported(extension))
	{
		glRefConfig.seamlessCubeMap = !!r_arb_seamless_cube_map->integer;

		ri.Printf(PRINT_ALL, result[glRefConfig.seamlessCubeMap], extension);
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

	glRefConfig.memInfo = MI_NONE;

	// GL_NVX_gpu_memory_info
	extension = "GL_NVX_gpu_memory_info";
	if( SDL_GL_ExtensionSupported( extension ) )
	{
		glRefConfig.memInfo = MI_NVX;

		ri.Printf(PRINT_ALL, result[1], extension);
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

	// GL_ATI_meminfo
	extension = "GL_ATI_meminfo";
	if( SDL_GL_ExtensionSupported( extension ) )
	{
		if (glRefConfig.memInfo == MI_NONE)
		{
			glRefConfig.memInfo = MI_ATI;

			ri.Printf(PRINT_ALL, result[1], extension);
		}
		else
		{
			ri.Printf(PRINT_ALL, result[0], extension);
		}
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

	glRefConfig.textureCompression = TCR_NONE;

	// GL_ARB_texture_compression_rgtc
	extension = "GL_ARB_texture_compression_rgtc";
	if (SDL_GL_ExtensionSupported(extension))
	{
		qboolean useRgtc = r_ext_compressed_textures->integer >= 1;

		if (useRgtc)
			glRefConfig.textureCompression |= TCR_RGTC;

		ri.Printf(PRINT_ALL, result[useRgtc], extension);
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

	glRefConfig.swizzleNormalmap = r_ext_compressed_textures->integer && !(glRefConfig.textureCompression & TCR_RGTC);

	// GL_ARB_texture_compression_bptc
	extension = "GL_ARB_texture_compression_bptc";
	if (SDL_GL_ExtensionSupported(extension))
	{
		qboolean useBptc = r_ext_compressed_textures->integer >= 2;

		if (useBptc)
			glRefConfig.textureCompression |= TCR_BPTC;

		ri.Printf(PRINT_ALL, result[useBptc], extension);
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

	// GL_EXT_direct_state_access
	extension = "GL_EXT_direct_state_access";
	glRefConfig.directStateAccess = qfalse;
	if (SDL_GL_ExtensionSupported(extension))
	{
		glRefConfig.directStateAccess = !!r_ext_direct_state_access->integer;

		// QGL_*_PROCS becomes several functions, do not remove {}
		if (glRefConfig.directStateAccess)
		{
			QGL_EXT_direct_state_access_PROCS;
		}

		ri.Printf(PRINT_ALL, result[glRefConfig.directStateAccess], extension);
	}
	else
	{
		ri.Printf(PRINT_ALL, result[2], extension);
	}

done:

	// Determine GLSL version
	if (1)
	{
		char version[256], *version_p;

		Q_strncpyz(version, (char *)qglGetString(GL_SHADING_LANGUAGE_VERSION), sizeof(version));

		// Skip leading text such as "OpenGL ES GLSL ES "
		version_p = version;
		while ( *version_p && !isdigit( *version_p ) )
		{
			version_p++;
		}

		sscanf(version_p, "%d.%d", &glRefConfig.glslMajorVersion, &glRefConfig.glslMinorVersion);

		ri.Printf(PRINT_ALL, "...using GLSL version %s\n", version);
	}

#undef GLE
}
