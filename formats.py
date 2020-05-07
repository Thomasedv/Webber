from collections import namedtuple

encoding = namedtuple('Encoding', ['ext', 'f', 'commands'])
format_spec = {}

webm_params = [
    '-c:v', 'libvpx-vp9',
    '-tile-columns', '6',
    '-threads', '12',
    '-static-thresh', '0',
    '-frame-parallel', '0',
    '-auto-alt-ref', '1',
    '-lag-in-frames', '25',
    '-g', '288',
    '-pix_fmt', 'yuv420p'
]

format_spec['webm'] = encoding('webm', 'webm', webm_params)

av1_params = [
    '-c:v', 'libaom-av1',
    '-tile-columns', '6',
    '-threads', '12',
    '-row-mt', '1',
    '-static-thresh', '0',
    '-frame-parallel', '0',
    '-auto-alt-ref', '1',
    '-lag-in-frames', '25',
    '-g', '288',
    '-pix_fmt', 'yuv420p',
    '-strict', 'experimental'
]

format_spec['av1'] = encoding('mkv', 'matroska', webm_params)
