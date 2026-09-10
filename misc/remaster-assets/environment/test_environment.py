import struct
import unittest

from package import material, surfaces
from prepare_map import adapt, adapt_aas


class EnvironmentTests(unittest.TestCase):
    def fixture(self):
        chunks = [b'entities unchanged',
                  struct.pack('<64sii', b'textures/gothic_block/blocks15', 123, 456),
                  b'planes unchanged'] + [b''] * 10 + [struct.pack('<i', 0) + bytes(100),
                  bytes([200, 10, 30, 12, 80, 70]), b'lightgrid unchanged', b'PVS unchanged']
        chunks[10] = (struct.pack('<10f4B', 2, 3, 5, .1, .2, .3, .4, 0, 0, 1, 20, 200, 5, 17)
                      + struct.pack('<10f4B', 7, 11, 13, .6, .7, .8, .9, 0, 1, 0, 0, 0, 0, 251))
        chunks[15] = bytes([20, 60, 40, 180, 10, 50, 63, 247,
                            0, 0, 0, 0, 0, 0, 19, 37])
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
        self.assertEqual([h['lump'] for h in hashes if not h['identical']], [1, 10, 14, 15])
        off, length = struct.unpack_from('<ii', result, 8 + 14 * 8)
        self.assertEqual(result[off:off + length], bytes([200, 200, 200, 80, 80, 80]))
        off, length = struct.unpack_from('<ii', result, 16)
        self.assertEqual(result[off + 64:off + 72], struct.pack('<ii', 123, 456))
        self.assertEqual(surfaces(result), [('textures/remaster_environment/ceramic', 1)])

    def test_grid_and_vertex_color_match_lightmap_without_geometry_or_direction_change(self):
        source = self.fixture()
        result, _ = adapt(source)
        offset, length = struct.unpack_from('<ii', result, 8 + 10 * 8)
        self.assertEqual(result[offset + 40:offset + 44], bytes([200, 200, 200, 17]))
        self.assertEqual(result[offset + 84:offset + 88], bytes([0, 0, 0, 251]))
        for start in range(offset, offset + length, 44):
            self.assertEqual(result[start:start + 40], source[start:start + 40])
        offset, length = struct.unpack_from('<ii', result, 8 + 15 * 8)
        self.assertEqual(result[offset:offset + length], bytes([
            60, 60, 60, 180, 180, 180, 63, 247, 0, 0, 0, 0, 0, 0, 19, 37]))

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

    def test_aas_v4_v5_only_encoded_checksum_bytes_change(self):
        for version in (4, 5):
            header = bytearray(b'EAAS' + struct.pack('<II', version, 0x12345678))
            header += struct.pack('<ii', 124, 6) * 14
            if version == 5:
                for i in range(8, 124):
                    header[i] ^= ((i - 8) * 119) & 255
            source = bytes(header) + b'NAV123'
            result, report = adapt_aas(source, 0x12345678, 0xa1b2c3d4)
            self.assertEqual(result[8:12], bytes.fromhex('d4b45cc4' if version == 5 else 'd4c3b2a1'))
            self.assertEqual(result[:8] + result[12:], source[:8] + source[12:])
            self.assertEqual(report['changed_byte_offsets'], [8, 9, 10, 11])
            self.assertEqual(report['navigation_payload_before_sha256'], report['navigation_payload_after_sha256'])
            with self.assertRaises(ValueError):
                adapt_aas(source, 0x12345679, 0xa1b2c3d4)


if __name__ == '__main__':
    unittest.main()
