import struct
import unittest

from package import material, surfaces
from prepare_map import adapt


class EnvironmentTests(unittest.TestCase):
    def fixture(self):
        chunks = [b'entities unchanged',
                  struct.pack('<64sii', b'textures/gothic_block/blocks15', 123, 456),
                  b'planes unchanged'] + [b''] * 10 + [struct.pack('<i', 0) + bytes(100),
                  bytes([200, 10, 30, 12, 80, 70]), b'lightgrid unchanged', b'PVS unchanged']
        header = b'IBSP' + struct.pack('<i', 46)
        offset = 144
        for chunk in chunks:
            header += struct.pack('<ii', offset, len(chunk))
            offset += len(chunk)
        return header + b''.join(chunks)

    def test_visual_only_asymmetric_channels_and_preserved_flags(self):
        source = self.fixture()
        result, hashes = adapt(source)
        self.assertEqual(len(result), len(source))
        self.assertEqual(result[:144], source[:144])
        self.assertEqual([h['lump'] for h in hashes if not h['identical']], [1, 14])
        off, length = struct.unpack_from('<ii', result, 8 + 14 * 8)
        self.assertEqual(result[off:off + length], bytes([200, 200, 200, 80, 80, 80]))
        off, length = struct.unpack_from('<ii', result, 16)
        self.assertEqual(result[off + 64:off + 72], struct.pack('<ii', 123, 456))
        self.assertEqual(surfaces(result), [('textures/remaster_environment/ceramic', 1)])

    def test_effects_and_collision_not_replaced(self):
        for name in ['textures/common/clip', 'textures/common/caulk', 'textures/sfx/flame1side', 'noshader']:
            self.assertIsNone(material(name))
        self.assertEqual(material('textures/gothic_floor/xstairtop4'), 'tread')
        self.assertEqual(material('textures/gothic_floor/xstepborder3'), 'orange')
        self.assertEqual(material('textures/skies/tim_hell'), 'sky')

    def test_invalid_bsp_rejected(self):
        data = bytearray(self.fixture())
        data[4] = 47
        with self.assertRaises(ValueError):
            surfaces(data)
        data[4] = 46
        struct.pack_into('<i', data, 8, len(data) + 1)
        with self.assertRaises(ValueError):
            surfaces(data)


if __name__ == '__main__':
    unittest.main()
