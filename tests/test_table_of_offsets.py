from context import table_of_offsets

import unittest

class Test_TableOfOffsets(unittest.TestCase):

    def test_1(self):
        print(table_of_offsets.__version__)
        actual = table_of_offsets.TableOfOffsets()
        print(dir(actual))
        self.assertEqual('foo'.upper(), 'FOO')

    def test_offset2double(self):
        self.assertEqual(1.0, table_of_offsets.TableOfOffsets.offset2double("0-1-0"))
        self.assertEqual(1.0, table_of_offsets.TableOfOffsets.offset2double("0-1"))
        self.assertEqual(12.0, table_of_offsets.TableOfOffsets.offset2double("1-0"))

        self.assertEqual(0.1875, table_of_offsets.TableOfOffsets.offset2double("0-0-1+"))
        self.assertEqual(0.0625, table_of_offsets.TableOfOffsets.offset2double("0-0-1-"))

if __name__ == '__main__':
    unittest.main()