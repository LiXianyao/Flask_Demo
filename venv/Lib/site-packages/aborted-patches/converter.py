from pdfminer.converter import PDFLayoutAnalyzer
from pdfminer.utils import mult_matrix, apply_matrix_pt, get_bound
from pdfminer.layout import LTFigure
import six

def add_wh(attr):
    attr.update({
        "height": attr["y1"] - attr["y0"],
        "width": attr["x1"] - attr["x0"],
    })
    return attr

def render_image(self, name, stream):
    srcsize = (stream.get_any(("W", "Width")),
        stream.get_any(("H", "Height")))
    imagemask = stream.get_any(("IM", "ImageMask"))
    bits = stream.get_any(("BPC", "BitsPerComponent"), 1)
    colorspace = stream.get_any(("CS", "ColorSpace"))
    if not isinstance(colorspace, list):
        colorspace = [colorspace]

    item = {
        "name": name,
        "srcsize": srcsize,
        "imagemask": imagemask,
        "colorspace": colorspace,
        "bits": bits,
        "stream": stream,
        "x0": self.cur_item.x0,
        "y0": self.cur_item.y0,
        "x1": self.cur_item.x1,
        "y1": self.cur_item.y1,
        "object_type": "image",
    }
    self.cur_item.add(add_wh(item))
    return

PDFLayoutAnalyzer.render_image = render_image

def paint_path(self, gstate, stroke, fill, evenodd, path):
    shape = ''.join(x[0] for x in path)
    if shape == 'ml':
        # horizontal/vertical line
        (_, x0, y0) = path[0]
        (_, x1, y1) = path[1]
        (x0, y0) = apply_matrix_pt(self.ctm, (x0, y0))
        (x1, y1) = apply_matrix_pt(self.ctm, (x1, y1))
        if x0 == x1 or y0 == y1:
            x0, y0, x1, y1 = get_bound([ (x0, y0), (x1, y1) ])

            item = add_wh({
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "object_type": "line",
            })

            if self.interpreter.parse_styles:
                item.update({
                    "stroke_width": 0 if stroke is False else gstate.linewidth,
                    "stroke": None if stroke is False else (gstate.scolor_hex or "#000000"),
                    "fill": None if fill is False else (gstate.ncolor_hex or "#000000"),
                    "dash": gstate.dash,
                    "evenodd": evenodd,
                })

            self.cur_item.add(item)
            return

    if shape == 'mlllh':
        # rectangle
        (_, x0, y0) = path[0]
        (_, x1, y1) = path[1]
        (_, x2, y2) = path[2]
        (_, x3, y3) = path[3]
        (x0, y0) = apply_matrix_pt(self.ctm, (x0, y0))
        (x1, y1) = apply_matrix_pt(self.ctm, (x1, y1))
        (x2, y2) = apply_matrix_pt(self.ctm, (x2, y2))
        (x3, y3) = apply_matrix_pt(self.ctm, (x3, y3))
        if ((x0 == x1 and y1 == y2 and x2 == x3 and y3 == y0) or
            (y0 == y1 and x1 == x2 and y2 == y3 and x3 == x0)):
            y_min = min(y0, y1, y2, y3)
            y_max = max(y0, y1, y2, y3)
            x_min = min(x0, x1, x2, x3)
            x_max = max(x0, x1, x2, x3)
            item = add_wh({
                "x0": x_min,
                "y0": y_min,
                "x1": x_max,
                "y1": y_max,
                "object_type": "rect",
            })
            if self.interpreter.parse_styles:
                item.update({
                    "stroke_width": 0 if stroke is False else gstate.linewidth,
                    "stroke": None if stroke is False else (gstate.scolor_hex or "#000000"),
                    "fill": None if fill is False else (gstate.ncolor_hex or "#000000"),
                    "dash": gstate.dash,
                    "evenodd": evenodd,
                })
            self.cur_item.add(item)
            return
    # other shapes
    pts = []
    for p in path:
        for i in range(1, len(p), 2):
            pts.append(apply_matrix_pt(self.ctm, (p[i], p[i+1])))
    x0, y0, x1, y1 = get_bound(pts)

    item = add_wh({
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "points": pts,
        "path": path,
        "object_type": "curve"
    })

    if self.interpreter.parse_styles:
        item.update({
            "stroke_width": 0 if stroke is False else gstate.linewidth,
            "stroke": None if stroke is False else (gstate.scolor_hex or "#000000"),
            "fill": None if fill is False else (gstate.ncolor_hex or "#000000"),
            "dash": gstate.dash,
            "evenodd": evenodd,
        })

    self.cur_item.add(item)
    return

PDFLayoutAnalyzer.paint_path = paint_path

def render_char(self, matrix, font, fontsize, scaling, rise, cid):
    try:
        text = font.to_unichr(cid)
        assert isinstance(text, six.text_type), text
    except PDFUnicodeNotDefined:
        text = self.handle_undefined_char(font, cid)

    textwidth = font.char_width(cid)
    textdisp = font.char_disp(cid)
    adv = textwidth * fontsize * scaling

    # compute the boundary rectangle.
    if font.is_vertical():
        # vertical
        width = font.get_width() * fontsize
        (vx, vy) = textdisp
        if vx is None:
            vx = width * 0.5
        else:
            vx = vx * fontsize * .001
        vy = (1000 - vy) * fontsize * .001
        tx = -vx
        ty = vy + rise
        bll = (tx, ty+self.adv)
        bur = (tx+width, ty)
    else:
        # horizontal
        height = font.get_height() * fontsize
        descent = font.get_descent() * fontsize
        ty = descent + rise
        bll = (0, ty)
        bur = (adv, ty+height)
    (a, b, c, d, e, f) = matrix
    upright = (0 < a*d*scaling and b*c <= 0)
    (x0, y0) = apply_matrix_pt(matrix, bll)
    (x1, y1) = apply_matrix_pt(matrix, bur)
    if x1 < x0:
        (x0, x1) = (x1, x0)
    if y1 < y0:
        (y0, y1) = (y1, y0)

    if font.is_vertical():
        size = x1 - x0
    else:
        size = y1 - y0

    # cf. "Table 106 – Text rendering modes" of PDF 1.7 spec
    gs = self.interpreter.graphicstate
    r = self.interpreter.textstate.render
    if r in (0, 2, 4, 6):
        fill = gs.ncolor_hex
    else:
        fill = None
    if r in (1, 2, 5, 6):
        stroke = gs.scolor_hex
    else:
        stroke = None

    item = add_wh({
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "fontname": font.fontname,
        "size": size,
        "text": text,
        "object_type": "char",
    })

    if self.interpreter.parse_styles:
        item.update({
            "fill": fill,
            "stroke": stroke,
        })

    self.cur_item.add(item)
    return adv

PDFLayoutAnalyzer.render_char = render_char
