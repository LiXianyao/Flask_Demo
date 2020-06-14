import pdfminer

#def list_value(x):
#    x = pdfminer.pdftypes.resolve1(x)
#    if not isinstance(x, (list, tuple)):
#        print(x, type(x))
#        return []
#    return x
#
#pdfminer.pdffont.list_value = list_value

#pdfminer.settings.STRICT = False
#pdfminer.pdftypes.STRICT = False
pdfminer.pdfinterp.STRICT = False
