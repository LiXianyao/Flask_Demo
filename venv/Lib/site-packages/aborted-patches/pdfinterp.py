from pdfminer.pdfinterp import (
    PDFGraphicState,
    PDFPageInterpreter,
    PDFInterpreterError,
)

from pdfminer.pdfcolor import (
    LITERAL_DEVICE_GRAY,
    LITERAL_DEVICE_RGB,
    LITERAL_DEVICE_CMYK,
)

from ..utils import decode_psl_list

import spectra

def pdfcolor_to_hex(c, cs_name):
    if c is None:
        # Per PDF 1.7 spec, default is black
        return "#000000"
    if isinstance(c, (tuple, list)):
        c = decode_psl_list(c) 
    else:
        c = decode_psl_list([ c ])[0] 
        if type(c) is str and c[0] == "P":
            c = c[1:]

    if cs_name in (None, "DeviceGray"):
        # Per PDF 1.7 spec, default is DeviceGray
        s = spectra.rgb(c, c, c)
    elif cs_name == "DeviceRGB":
        s = spectra.rgb(*c)
    elif cs_name == "DeviceCMYK":
        s = spectra.cmyk(*c)
    else:
        raise ValueError("Cannot handle '{}' color space. Try parsing wth parse_colors=False".format(cs_name))

    return s.hexcode

# PDFGraphicState
def __init__(self):
    self.linewidth = 0
    self.linecap = None
    self.linejoin = None
    self.miterlimit = None
    self.dash = None
    self.intent = None
    self.flatness = None

    # stroking color
    self.scolor = None
    self.scs = None

    # non stroking color
    self.ncolor = None
    self.ncs = None
    return

def copy(self):
    obj = PDFGraphicState()
    obj.linewidth = self.linewidth
    obj.linecap = self.linecap
    obj.linejoin = self.linejoin
    obj.miterlimit = self.miterlimit
    obj.dash = self.dash
    obj.intent = self.intent
    obj.flatness = self.flatness
    obj.scolor = self.scolor
    obj.scs = self.scs
    obj.ncolor = self.ncolor
    obj.ncs = self.ncs
    return obj

@property
def scolor_hex(self):
    cs_name = "DeviceGray" if self.scs is None else self.scs.name
    return pdfcolor_to_hex(self.scolor, cs_name)

@property
def ncolor_hex(self):
    cs_name = "DeviceGray" if self.ncs is None else self.ncs.name 
    return pdfcolor_to_hex(self.ncolor, cs_name)
    
PDFGraphicState.__init__ = __init__
PDFGraphicState.copy = copy
PDFGraphicState.scolor_hex = scolor_hex
PDFGraphicState.ncolor_hex = ncolor_hex

# PDFPageInterpreter

# setgray-stroking
def do_G(self, gray):
    self.graphicstate.scolor = gray
    self.do_CS(LITERAL_DEVICE_GRAY)
    return

# setgray-non-stroking
def do_g(self, gray):
    self.graphicstate.ncolor = gray
    self.do_cs(LITERAL_DEVICE_GRAY)
    return

# setrgb-stroking
def do_RG(self, r, g, b):
    self.graphicstate.scolor = (r, g, b)
    self.do_CS(LITERAL_DEVICE_RGB)
    return

# setrgb-non-stroking
def do_rg(self, r, g, b):
    self.graphicstate.ncolor = (r, g, b)
    self.do_cs(LITERAL_DEVICE_RGB)
    return

# setcmyk-stroking
def do_K(self, c, m, y, k):
    self.graphicstate.scolor = (c, m, y, k)
    self.do_CS(LITERAL_DEVICE_CMYK)
    return

# setcmyk-non-stroking
def do_k(self, c, m, y, k):
    self.graphicstate.ncolor = (c, m, y, k)
    self.do_cs(LITERAL_DEVICE_CMYK)
    return

# setcmyk-non-stroking
def do_k(self, c, m, y, k):
    self.graphicstate.ncolor = (c, m, y, k)
    self.do_cs(LITERAL_DEVICE_CMYK)
    return

# setcolor
def do_SCN(self):
    if self.scs:
        n = self.scs.ncomponents
    else:
        if settings.STRICT:
            raise PDFInterpreterError('No colorspace specified!')
        n = 1
    self.graphicstate.scolor = self.pop(n)
    return

def do_scn(self):
    if self.ncs:
        n = self.ncs.ncomponents
    else:
        if settings.STRICT:
            raise PDFInterpreterError('No colorspace specified!')
        n = 1
    self.graphicstate.ncolor = self.pop(n)
    return

def __init__(self, rsrcmgr, device, parse_styles=False):
    self.rsrcmgr = rsrcmgr
    self.device = device
    self.device.interpreter = self
    self.parse_styles = parse_styles
#
#    if parse_styles:
#        self.do_G = do_G
#        self.do_g = do_g
#        self.do_RG = do_RG
#        self.do_rg = do_rg
#        self.do_K = do_K
#        self.do_k = do_k
#        self.do_SCN = do_SCN
#        self.do_scn = do_scn

PDFPageInterpreter.__init__ = __init__
