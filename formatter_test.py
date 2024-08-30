"""Unit tests for string formatter."""

import unittest
import i3blocks_mpris


class TestFormatter(unittest.TestCase):

    def test_regular_strings_are_left_untouched(self):
        formatter = i3blocks_mpris.Formatter()

        self.assertEqual('regular_string', formatter.format('regular_string'))

    def test_status_icon_is_replaced(self):
        formatter = i3blocks_mpris.Formatter(
            status_icons={
                'one': 'uno',
                'two': 'dos',
                'three': 'tres',
                'four': 'cuatro',
            }
        )

        self.assertEqual('uno', formatter.format('{status:icon}', status='one'))
        self.assertEqual('dos', formatter.format('{status:icon}', status='two'))
        self.assertEqual('tres', formatter.format('{status:icon}', status='three'))
        self.assertEqual('cuatro', formatter.format('{status:icon}', status='four'))

    def test_undefined_status_icons_is_replaced_with_question_mark(self):
        formatter = i3blocks_mpris.Formatter(status_icons={})

        self.assertEqual('?', formatter.format('{status:icon}', status='Undefined'))

    def test_upper_case(self):
        formatter = i3blocks_mpris.Formatter()

        self.assertEqual(
            'HELLO WORLD',
            formatter.format('{salutation:upper}', salutation='HelLO wORlD'),
        )

    def test_lower_case(self):
        formatter = i3blocks_mpris.Formatter()

        self.assertEqual(
            'hello world',
            formatter.format('{salutation:lower}', salutation='HelLO wORlD'),
        )

    def test_capitalize(self):
        formatter = i3blocks_mpris.Formatter()

        self.assertEqual(
            'Hello world',
            formatter.format('{salutation:capitalize}', salutation='HelLO wORlD'),
        )

    def test_title_case(self):
        formatter = i3blocks_mpris.Formatter()

        self.assertEqual(
            'Hello World',
            formatter.format('{salutation:title}', salutation='HelLO wORlD'),
        )

    def test_markup_escape_off_does_not_escape_html_characters(self):
        formatter = i3blocks_mpris.Formatter(markup_escape=False)

        self.assertEqual(
            '<hola>mundo</hola>',
            formatter.format('{salutation}', salutation='<hola>mundo</hola>'),
        )

    def test_markup_escape_on_escapes_html_characters(self):
        formatter = i3blocks_mpris.Formatter(markup_escape=True)

        self.assertEqual(
            '&lt;hola&gt;mundo&lt;/hola&gt;',
            formatter.format('{salutation}', salutation='<hola>mundo</hola>'),
        )

    def test_sanitize_unicode_on_leaves_format_chars_untouched(self):
        formatter = i3blocks_mpris.Formatter(sanitize_unicode=True)

        self.assertEqual(
            '\u00AD\u0660\u200B',
            formatter.format('{foo}', foo='\u00AD\u0660\u200B'),
        )

    def test_sanitize_unicode_on_removes_non_format_chars(self):
        formatter = i3blocks_mpris.Formatter(sanitize_unicode=True)

        self.assertEqual(
            '',
            formatter.format(
                '{foo}',
                #     Cc    Cc    Co    Co    Cs    Cs    Cn    Cn
                foo='\u0000\u0013\uFDEF\uFDD0\uD800\uDFFF\u0378\U000E0000',
            ),
        )

    def test_sanitize_unicode_off_does_not_remove_non_format_chars(self):
        formatter = i3blocks_mpris.Formatter(sanitize_unicode=False)

        self.assertEqual(
            '\u0000\u0013\uFDEF\uFDD0\uD800\uDFFF\u0378\U000E0000',
            formatter.format(
                '{foo}',
                #     Cc    Cc    Co    Co    Cs    Cs    Cn    Cn
                foo='\u0000\u0013\uFDEF\uFDD0\uD800\uDFFF\u0378\U000E0000',
            ),
        )

    def test_base_formatting_options_are_respected(self):
        formatter = i3blocks_mpris.Formatter()

        self.assertEqual(
            '0042',
            formatter.format(
                '{pad_with_zeros:04d}',
                pad_with_zeros=42,
            ),
        )

        self.assertEqual(
            'hello w',
            formatter.format(
                '{truncate_string:.7}',
                truncate_string='hello world',
            ),
        )

        self.assertEqual(
            'hello world    ',
            formatter.format(
                '{pad_right_with_spaces:<15}', pad_right_with_spaces='hello world'
            ),
        )

        self.assertEqual(
            '         hello world          ',
            formatter.format('{centered:^30}', centered='hello world'),
        )

        self.assertEqual(
            '    hello world',
            formatter.format(
                '{pad_left_with_spaces:>15}', pad_left_with_spaces='hello world'
            ),
        )

        self.assertEqual(
            '    hello world',
            formatter.format(
                '{pad_left_with_var_spaces:>{var}}',
                pad_left_with_var_spaces='hello world',
                var=15,
            ),
        )


if __name__ == '__main__':
    unittest.main()
