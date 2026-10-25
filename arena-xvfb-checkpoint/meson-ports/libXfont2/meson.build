project(
  'libXfont2',
  'c',
  version : '2.0.9',
  license : 'MIT',
  meson_version : '>=0.61.0',
  default_options : [
    'c_std=gnu11',
    'warning_level=1',
  ],
)

# Minimal Meson port for the pinned libXfont2 2.0.9 source.
#
# It follows the source selection and preprocessor configuration in the
# upstream configure.ac/Makefile.am for this target subset:
#   enabled:  fontfile, bitmap, PCF, BDF, built-ins, gzip
#   disabled: FreeType, font-server client (fc), SNF, bzip2
#
# The replacement-function files are selected by the same kind of feature
# checks that AC_REPLACE_FUNCS performs; no source file is silently omitted.

cc = meson.get_compiler('c')

add_project_arguments(
  '-DHAVE_CONFIG_H',
  '-D_GNU_SOURCE',
  '-D_XOPEN_SOURCE',
  '-D_FILE_OFFSET_BITS=64',
  language : 'c',
)

conf = configuration_data()
conf.set('_GNU_SOURCE', 1)
conf.set('X_GZIP_FONT_COMPRESSION', 1)
conf.set('XFONT_BUILTINS', 1)
conf.set('XFONT_PCFFORMAT', 1)
conf.set('XFONT_BDFFORMAT', 1)
conf.set('XFONT_BITMAP', 1)
conf.set('XFONT_FONTFILE', 1)

foreach header : ['endian.h', 'poll.h', 'sys/poll.h', 'err.h', 'float.h']
  macro = 'HAVE_' + header.underscorify().to_upper()
  conf.set(macro, cc.has_header(header) ? 1 : false)
endforeach

function_checks = {
  'poll' : '#include <poll.h>',
  'readlink' : '#include <unistd.h>',
  'reallocarray' : '#include <stdlib.h>',
  'realpath' : '#include <stdlib.h>',
  'strlcat' : '#include <string.h>',
  'strlcpy' : '#include <string.h>',
}

have_function = {}
foreach function, prefix : function_checks
  result = cc.has_function(function, prefix : prefix, args : '-D_GNU_SOURCE')
  have_function += {function : result}
  conf.set('HAVE_' + function.to_upper(), result ? 1 : false)
endforeach

math_dep = cc.find_library('m', required : true)
hypot_probe = '''
#include <math.h>
int main(void) { return (int) hypot(3.0, 4.0); }
'''
if not cc.links(hypot_probe, dependencies : math_dep)
  error('libm/hypot is required by upstream configure.ac')
endif

xproto_dep = dependency('xproto', required : true)
xtrans_dep = dependency('xtrans', required : true)
fontsproto_dep = dependency('fontsproto', version : '>=2.1.3', required : true)
fontenc_dep = dependency('fontenc', required : true)
zlib_dep = dependency('zlib', required : true)

configure_file(
  output : 'config.h',
  configuration : conf,
)

root_inc = include_directories('.', 'include')

c_args = []
if cc.has_argument('-fvisibility=hidden')
  c_args += '-fvisibility=hidden'
endif

sources = files(
  'src/stubs/atom.c',
  'src/stubs/libxfontstubs.c',
  'src/util/fontaccel.c',
  'src/util/fontnames.c',
  'src/util/fontutil.c',
  'src/util/fontxlfd.c',
  'src/util/format.c',
  'src/util/miscutil.c',
  'src/util/patcache.c',
  'src/util/private.c',
  'src/util/utilbitmap.c',

  'src/fontfile/bitsource.c',
  'src/fontfile/bufio.c',
  'src/fontfile/decompress.c',
  'src/fontfile/defaults.c',
  'src/fontfile/dirfile.c',
  'src/fontfile/fileio.c',
  'src/fontfile/filewr.c',
  'src/fontfile/fontdir.c',
  'src/fontfile/fontfile.c',
  'src/fontfile/fontscale.c',
  'src/fontfile/gunzip.c',
  'src/fontfile/register.c',
  'src/fontfile/renderers.c',
  'src/fontfile/catalogue.c',

  'src/bitmap/bitmap.c',
  'src/bitmap/bitmapfunc.c',
  'src/bitmap/bitmaputil.c',
  'src/bitmap/bitscale.c',
  'src/bitmap/fontink.c',
  'src/bitmap/bdfread.c',
  'src/bitmap/bdfutils.c',
  'src/bitmap/pcfread.c',
  'src/bitmap/pcfwrite.c',

  'src/builtins/dir.c',
  'src/builtins/file.c',
  'src/builtins/fonts.c',
  'src/builtins/fpe.c',
  'src/builtins/render.c',
)

if not have_function['reallocarray']
  sources += files('src/util/reallocarray.c')
endif
if not have_function['realpath']
  sources += files('src/util/realpath.c')
endif
if not have_function['strlcat']
  sources += files('src/util/strlcat.c')
endif
if not have_function['strlcpy']
  sources += files('src/util/strlcpy.c')
endif

link_args = []
if host_machine.system() != 'windows'
  no_undefined = '-Wl,--no-undefined'
  if cc.has_link_argument(no_undefined)
    link_args += no_undefined
  endif
endif

libxfont2 = library(
  'Xfont2',
  sources,
  version : '2.0.0',
  include_directories : root_inc,
  dependencies : [
    xproto_dep,
    xtrans_dep,
    fontsproto_dep,
    fontenc_dep,
    zlib_dep,
    math_dep,
  ],
  c_args : c_args,
  link_args : link_args,
  install : true,
)

install_headers(
  'include/X11/fonts/libxfont2.h',
  subdir : 'X11' / 'fonts',
)

pkg = import('pkgconfig')
pkg.generate(
  libxfont2,
  name : 'Xfont2',
  description : 'X font Library version 2',
  filebase : 'xfont2',
  version : meson.project_version(),
  requires : ['xproto', 'fontsproto'],
  requires_private : ['fontenc', 'zlib'],
  libraries_private : [math_dep],
)

xfont2_dep = declare_dependency(
  link_with : libxfont2,
  include_directories : include_directories('include'),
  dependencies : [xproto_dep, fontsproto_dep],
)
meson.override_dependency('xfont2', xfont2_dep)

# Upstream noinst utility and PCF security-regression programs.  They are
# built only for the test stage and are not installed.
lsfontdir = executable(
  'lsfontdir',
  files(
    'test/utils/lsfontdir.c',
    'test/utils/font-test-utils.c',
  ),
  include_directories : root_inc,
  dependencies : [xproto_dep, fontsproto_dep],
  link_with : libxfont2,
  build_by_default : false,
)
test('lsfontdir-built-ins', lsfontdir, args : ['built-ins'])

pcf_tests = {
  'repad' : ['test-pcf-repad', 'test/test-pcf-repad.c', 'test/gen_evil_pcf_repad.py', 'evil-repad.pcf', false],
  'props' : ['test-pcf-props', 'test/test-pcf-props.c', 'test/gen_evil_pcf_props.py', 'evil-props.pcf', false],
  'scale' : ['test-pcf-bitmapscale', 'test/test-pcf-bitmapscale.c', 'test/gen_evil_pcf_bitmapscale.py', 'evil-scale.pcf', true],
  'encoding' : ['test-pcf-encoding', 'test/test-pcf-encoding.c', 'test/gen_evil_pcf_encoding.py', 'evil-encoding.pcf', false],
  'norepad' : ['test-pcf-norepad', 'test/test-pcf-norepad.c', 'test/gen_evil_pcf_norepad.py', 'evil-norepad.pcf', false],
}

python3 = find_program('python3', required : true)
foreach dirname, info : pcf_tests
  test_name = info[0]
  test_source = info[1]
  generator = info[2]
  pcf_name = info[3]
  has_scale = info[4]

  # Meson does not allow path segments in custom_target outputs.  Track the
  # generated directory with a stamp file while the official generator
  # creates the PCF and fonts.dir/fonts.scale files at the absolute paths
  # expected by the upstream test programs.  (pcf_name and has_scale are
  # retained above as documentation of the generator's output contract.)
  data = custom_target(
    'pcf-data-' + dirname,
    input : files(generator),
    output : 'pcf-data-' + dirname + '.stamp',
    command : [
      python3,
      '-c',
      'import pathlib, runpy, sys; script, outdir, stamp = sys.argv[1:]; sys.argv = [script, outdir]; runpy.run_path(script, run_name="__main__"); pathlib.Path(stamp).touch()',
      '@INPUT@',
      meson.project_build_root() / 'test' / 'data' / dirname,
      '@OUTPUT@',
    ],
    build_by_default : false,
    build_always_stale : false,
  )

  exe = executable(
    test_name,
    files(
      test_source,
      'test/pcf-test-common.c',
      'test/utils/font-test-utils.c',
    ),
    include_directories : root_inc,
    dependencies : [xproto_dep, fontsproto_dep],
    link_with : libxfont2,
    build_by_default : false,
  )

  test(
    test_name,
    exe,
    env : {'builddir' : meson.project_build_root()},
    depends : data,
  )
endforeach

summary(
  {
    'source files (including replacements)' : sources.length(),
    'FreeType' : false,
    'font-server client (fc)' : false,
    'built-ins' : true,
    'PCF' : true,
    'BDF' : true,
    'SNF' : false,
    'gzip' : true,
    'bzip2' : false,
  },
  section : 'libXfont2 Meson port',
)
