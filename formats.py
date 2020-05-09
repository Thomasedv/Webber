from collections import namedtuple

encoding = namedtuple('Encoding', ['ext', 'f', 'commands'])
passes = namedtuple('commandset', ['all', 'first', 'second'])
format_spec = {}

webm_params = passes([
    '-c:v', 'libvpx-vp9',
    '-tile-columns', '3',
    '-tile-rows', '2',
    '-threads', '12',
    '-row-mt', '1',
    '-static-thresh', '0',
    '-frame-parallel', '0',
    '-auto-alt-ref', '6',
    '-lag-in-frames', '25',
    '-g', '240',
    '-crf', '20',
    '-pix_fmt', 'yuv420p'
], [
    '-cpu-used', '1'
], [
    '-cpu-used', '0'
])

format_spec['webm'] = encoding('webm', 'webm', webm_params)

av1_params = passes([
    '-c:v', 'libaom-av1',
    '-tiles', '4x3',
    '-threads', '12',
    '-pix_fmt', 'yuv420p',
    '-row-mt', '1',
    '-auto-alt-ref', '1',
    '-lag-in-frames', '25',
    '-strict', 'experimental',
    '-crf', '30',
    '-static-thresh', '0',
    '-frame-parallel', '0',
], [
    '-cpu-used', '8',
], [
    '-cpu-used', '6',
])

format_spec['av1'] = encoding('mkv', 'matroska', av1_params)


class Tweaker:
    def __init__(self, spec):
        self.enc = format_spec[spec]
        self.all_pass = self.enc.commands.all
        self.first_pass = self.enc.commands.first
        self.second_pass = self.enc.commands.second

    def split(self):
        pass

    def make_encoding(self):
        p = passes(self.all_pass, self.first_pass, self.second_pass)
        return encoding(self.enc.ext, self.enc.f, p)
