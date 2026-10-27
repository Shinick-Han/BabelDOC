import unittest
from types import SimpleNamespace
import pymupdf
from babeldoc.format.pdf.document_il import Box, PdfStyle, PdfParagraph, PdfCharacter, PdfParagraphComposition
from babeldoc.format.pdf.document_il.midend.typesetting import Typesetting, TypesettingUnit
from babeldoc.format.pdf.document_il.midend.selected_paragraph_edit import edit_selected_paragraph

class StrictSelectionTests(unittest.TestCase):
    def setUp(self):
        self.font = pymupdf.Font('helv')
        self.style = PdfStyle(font_id='base', font_size=10)
        self.ts = Typesetting.__new__(Typesetting)
        self.ts.is_cjk = False
        self.ts.font_mapper = SimpleNamespace(base_font=self.font, map=lambda font, char: self.font)
        self.old = PdfParagraphComposition(pdf_character=PdfCharacter(char_unicode='old', pdf_style=self.style, box=Box(x=10,y=80,x2=20,y2=90)))
        self.para = PdfParagraph(box=Box(x=10,y=50,x2=110,y2=90), pdf_paragraph_composition=[self.old], pdf_style=self.style, unicode='old', xobj_id=-1)
        self.page = SimpleNamespace(cropbox=SimpleNamespace(box=Box(x=0,y=0,x2=120,y2=120)), pdf_paragraph=[self.para], pdf_character=[], pdf_figure=[], pdf_curve=[], pdf_form=[])
    def units(self, text):
        return [TypesettingUnit(unicode=c, font=self.font, font_size=10, style=self.style, xobj_id=-1) for c in text]
    def test_real_multiline_layout_at_original_size(self):
        result = self.ts.render_selected_paragraph_strict(self.para,self.page,self.units('alpha beta gamma delta epsilon zeta'))
        self.assertEqual(result['status'],'fitted')
        chars = [c.pdf_character for c in self.para.pdf_paragraph_composition]
        self.assertGreater(len({round(c.box.y, 2) for c in chars}),1)
        self.assertEqual({c.pdf_style.font_size for c in chars},{10})
        self.assertEqual(''.join(c.char_unicode for c in chars).replace(' ',''),'alphabetagammadeltaepsilonzeta')
    def test_hook_binds_text_and_geometry_and_only_mutates_on_fit(self):
        args = dict(before='old', after='alpha beta gamma delta epsilon zeta',
                    fonts={'base': object()}, expected_box=(10, 50, 110, 90))
        wrong = edit_selected_paragraph(self.ts, self.page, self.para, **{**args, 'before': 'other'})
        self.assertEqual(wrong['reason'], 'source-binding-mismatch')
        self.assertEqual(self.para.pdf_paragraph_composition, [self.old])
        result = edit_selected_paragraph(self.ts, self.page, self.para, **args)
        self.assertEqual(result['status'], 'fitted')
        self.assertEqual(self.para.unicode, args['after'])
        self.assertEqual({c.pdf_character.pdf_style.font_size for c in self.para.pdf_paragraph_composition}, {10})

    def test_hook_rejects_implicit_source_spacing(self):
        first = PdfCharacter(char_unicode='a', pdf_style=self.style, box=Box(x=10,y=80,x2=15,y2=90))
        second = PdfCharacter(char_unicode='b', pdf_style=self.style, box=Box(x=17,y=80,x2=22,y2=90))
        self.para.pdf_paragraph_composition = [PdfParagraphComposition(pdf_character=first), PdfParagraphComposition(pdf_character=second)]
        result = edit_selected_paragraph(self.ts, self.page, self.para, before='old', after='ab', fonts={'base': object()}, expected_box=(10, 50, 110, 90))
        self.assertEqual(result['reason'], 'implicit-source-spacing')

    def test_dropped_leading_space_is_rejected(self):
        result = self.ts.render_selected_paragraph_strict(self.para, self.page, self.units(' leading'))
        self.assertEqual(result['status'], 'unsupported')
        self.assertEqual(result['reason'], 'layout-dropped-units')
        self.assertEqual(self.para.pdf_paragraph_composition, [self.old])

    def test_missing_glyph_is_rejected_before_mutation(self):
        result = self.ts.render_selected_paragraph_strict(self.para, self.page, self.units('A\u4e2d'))
        self.assertEqual(result['status'], 'unsupported')
        self.assertEqual(result['reason'], 'missing-rendered-glyph')
        self.assertEqual(self.para.pdf_paragraph_composition, [self.old])

    def test_expansion_requires_all_ink_check(self):
        self.para.box = Box(x=10, y=70, x2=110, y2=90)
        original = self.para.box
        result = self.ts.render_selected_paragraph_strict(
            self.para, self.page, self.units('One two three four five six seven eight nine ten'))
        self.assertEqual(result['reason'], 'expansion-unverified')
        self.assertIs(self.para.box, original)
        self.assertEqual(self.para.pdf_paragraph_composition, [self.old])

    def test_overflow_does_not_mutate_selection(self):
        original_box = self.para.box
        result = self.ts.render_selected_paragraph_strict(self.para,self.page,self.units('long text ' * 150))
        self.assertEqual(result['status'],'overflow')
        self.assertEqual(self.para.pdf_paragraph_composition,[self.old])
        self.assertIs(self.para.box,original_box)
        self.assertEqual(self.page.pdf_curve,[])
        self.assertEqual(self.page.pdf_form,[])
        self.assertEqual(result['scale'],1.0)

if __name__ == '__main__': unittest.main()
