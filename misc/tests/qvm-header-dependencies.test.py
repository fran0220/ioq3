"""Real q3lcc/q3asm incremental builds must agree after a shared layout edit."""
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]


class QVMHeaderTest(unittest.TestCase):
    def test_shared_header_rebuilds_both_translation_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'src'
            build = Path(tmp) / 'build'
            code = source / 'code'
            code.mkdir(parents=True)
            (source / 'cmake').symlink_to(ROOT / 'cmake', target_is_directory=True)
            (code / 'tools').symlink_to(ROOT / 'code/tools', target_is_directory=True)
            header = code / 'contract.h'
            header.write_text('typedef struct { int prefix[1]; int media; } layout_t;\n')
            (code / 'entry.c').write_text('#include "contract.h"\nint vmMain(void) { return sizeof(layout_t); }\n')
            (code / 'reader.c').write_text('#include "contract.h"\nint readMedia(layout_t *p) { return p->media; }\n')
            # Exercise the unchanged production function with actual tools built
            # once, isolating header invalidation from ExternalProject timestamps.
            rules = (ROOT / 'cmake/utils/qvm_tools.cmake').read_text()
            (source / 'rules.cmake').write_text(rules[rules.index('function(add_qvm MODULE_NAME)'):])
            tools = Path(tmp) / 'tools'
            (source / 'CMakeLists.txt').write_text(f'''
cmake_minimum_required(VERSION 3.20)
project(qvm_header_probe C)
set(BUILD_GAME_QVMS ON)
set(SOURCE_DIR "${{CMAKE_CURRENT_SOURCE_DIR}}/code")
set(CMAKE_MODULE_PATH "{ROOT}/cmake")
set(Q3LCC "{tools}/Release/q3lcc")
set(Q3CPP "{tools}/Release/q3cpp")
set(Q3RCC "{tools}/Release/q3rcc")
set(Q3ASM "{tools}/Release/q3asm")
add_custom_target(qvm_tools)
include("${{CMAKE_CURRENT_SOURCE_DIR}}/rules.cmake")
add_qvm(probe SOURCES "${{SOURCE_DIR}}/entry.c" "${{SOURCE_DIR}}/reader.c")
''')
            def run(*args):
                subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            run('cmake', '-S', str(ROOT / 'cmake/tools'), '-B', str(tools), '-G', 'Ninja',
                '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_MINIMUM_REQUIRED_VERSION=3.20',
                f'-DSOURCE_DIR={ROOT}/code', f'-DCMAKE_MODULE_PATH={ROOT}/cmake')
            run('cmake', '--build', str(tools), '--parallel', '2')
            run('cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release')
            def compile():
                run('cmake', '--build', str(build), '--parallel', '2')
            compile()
            objects = [build / 'qvm.dir/probe' / (name + '.asm') for name in ('entry', 'reader')]
            before = [p.read_bytes() for p in objects]
            qvm = build / 'Release/probe.qvm'
            old_qvm = qvm.read_bytes()
            time.sleep(1.05)  # filesystems with coarse mtime granularity
            header.write_text('typedef struct { int prefix[7]; int media; } layout_t;\n')
            compile()
            for path, old in zip(objects, before):
                self.assertNotEqual(path.read_bytes(), old, f'{path.name} retained the old layout')
            self.assertNotEqual(qvm.read_bytes(), old_qvm)
            timestamps = [p.stat().st_mtime_ns for p in objects]
            compile()
            self.assertEqual([p.stat().st_mtime_ns for p in objects], timestamps,
                             'Unchanged headers should not trigger unnecessary VM recompilation')


if __name__ == '__main__':
    unittest.main()
