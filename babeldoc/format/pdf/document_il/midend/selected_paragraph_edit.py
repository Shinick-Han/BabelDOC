"""Experimental selected-IR edit hook; no PDF I/O or translation.

The caller must bind the source hash, paragraph geometry and exact text to the
original document, and independently verify any produced PDF. This narrow
hook refuses formulas and mixed styles rather than flattening them.
"""
import copy

from babeldoc.format.pdf.document_il import il_version_1 as il


def edit_selected_paragraph(typesetter, page, paragraph, *, before, after, fonts,
                            expected_box, expansion_is_clear=None):
    """Mutate only a bound, single-style paragraph after strict fit succeeds."""
    if not any(p is paragraph for p in page.pdf_paragraph) or paragraph.box is None:
        return {"status": "invalid", "reason": "paragraph-not-on-page"}
    actual_box = (paragraph.box.x, paragraph.box.y, paragraph.box.x2, paragraph.box.y2)
    if tuple(expected_box) != actual_box or paragraph.unicode != before:
        return {"status": "invalid", "reason": "source-binding-mismatch"}
    if not after or '\n' in after or '\r' in after or paragraph.vertical:
        return {"status": "unsupported", "reason": "text-or-orientation"}
    if not paragraph.pdf_style or not paragraph.pdf_paragraph_composition:
        return {"status": "unsupported", "reason": "missing-style"}
    source_chars = []
    for comp in paragraph.pdf_paragraph_composition:
        if comp.pdf_formula or comp.pdf_same_style_unicode_characters:
            return {"status": "unsupported", "reason": "formula-or-existing-unicode"}
        chars = ([comp.pdf_character] if comp.pdf_character else
                 comp.pdf_line.pdf_character if comp.pdf_line else
                 comp.pdf_same_style_characters.pdf_character if comp.pdf_same_style_characters else [])
        if not chars or any(c.pdf_style != paragraph.pdf_style for c in chars):
            return {"status": "unsupported", "reason": "mixed-or-unknown-composition"}
        source_chars.extend(chars)
    # Source PDFs can express a word boundary as a positional gap rather than
    # a space character. Rebuilding text alone would collapse that visible gap.
    # Until the writer carries source advances, conservatively refuse it.
    if any(not c.box for c in source_chars):
        return {"status": "unsupported", "reason": "missing-source-geometry"}
    for left, right in zip(source_chars, source_chars[1:]):
        size = paragraph.pdf_style.font_size or 0
        same_line = abs(left.box.y - right.box.y) < size * 0.25
        if (same_line and left.char_unicode and right.char_unicode
                and not left.char_unicode.isspace() and not right.char_unicode.isspace()
                and right.box.x - left.box.x2 > size * 0.08):
            return {"status": "unsupported", "reason": "implicit-source-spacing"}
    staged = copy.copy(paragraph)
    staged.pdf_paragraph_composition = [il.PdfParagraphComposition(
        pdf_same_style_unicode_characters=il.PdfSameStyleUnicodeCharacters(
            unicode=after, pdf_style=copy.deepcopy(paragraph.pdf_style)))]
    units = typesetter.create_typesetting_units(staged, fonts)
    if ''.join(u.try_get_unicode() or '' for u in units) != after:
        return {"status": "unsupported", "reason": "font-mapping-dropped-text"}
    result = typesetter.render_selected_paragraph_strict(
        paragraph, page, units, expansion_is_clear=expansion_is_clear)
    if result['status'] == 'fitted':
        paragraph.unicode = after
    return result
