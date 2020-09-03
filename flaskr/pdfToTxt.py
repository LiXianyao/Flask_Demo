#-*-encoding:utf8-*-#

from pdfminer3k.pdfparser import PDFParser, PDFDocument
from pdfminer3k.pdfinterp import PDFResourceManager, PDFPageInterpreter, PDFTextExtractionNotAllowed
from pdfminer3k.converter import PDFPageAggregator
from pdfminer3k.layout import LTTextBoxHorizontal, LAParams
import re
import os
#from consoleLogger import logger
import datetime
from pdfTablesExtractor2 import PdfTablesExtractor

result = []
class Pdf2TxtManager:
    def __init__(self, type="dev", storeToFile=True):
        # 控制是否输出页分割行的使能, 是否按页数对txt文件进行分割
        self.storeToFile = storeToFile
        self.txtMaxPageNum = 100 if type == "dev" else 10000
        self.isNumber = lambda c: '0' <= c <='9'
        self.isCharacter = lambda c: 'A' <= c <= 'Z' or 'a' <= c <= 'z'
        self.isEngComa = lambda c: c in ['.', ',', ' ', ':', ';', '(', ')', '/', '-']

    u"""
    按照长度规则，判断输入的文本是否可以按照pattern进行分割
    （场景是为了解决一些句子里的分号；和冒号：分隔开的不是句子，而是短语/词，不应该分开，故加了这个判断）
    """
    def judgeSplitable(self, text, pattern):
        sentences = re.split(pattern, text)
        llen = list(map(len, sentences))
        judgeLen = lambda x: False if x in range(20) else True  # 分裂后的小句长度太短，说明不该分
        return False not in list(map(judgeLen, llen[:-1]))  # 最后一节可能是句号

    u"""尝试对pdf文件进行解码（若失败则直接失败）"""

    def decrypt_pdf_file(self, fileName, dir):
        formFileName = lambda name: os.path.join(dir, name)
        #logger.info(u"尝试解析文件{}... ...".format(fileName))
        res_file.write(u"--------- PDF-Transfer INFO:尝试解析文件{}... ...\n".format(fileName))
        # 打开指定的pdf，若是加密（密码为空），尝试解密后再打开
        newFileName = formFileName(fileName.replace(".pdf", "_dec.pdf"))  # 直接尝试对pdf进行解码操作
        os.system('qpdf --password="" --decrypt %s %s' % (formFileName(fileName), newFileName))
        self.pdfName = newFileName

        try:
            file, praser, self.doc = self.openPdfDoc(newFileName)  # 创建一个pdf文档
        except:
            if not os.path.exists(newFileName):
                #logger.error(u"指示的文件%s不存在，请检查" % (formFileName(fileName)))
                res_file.write(u"--------- PDF-Transfer ERROR：指示的文件%s不存在，请检查\n" % (formFileName(fileName)))
            else:
                #logger.error(u"有非空密码加密的pdf文件，不可解，转化失败，文件名：{}".format(newFileName))
                res_file.write(u"--------- PDF-Transfer ERROR：有非空密码加密的pdf文件，不可解，转化失败，文件名：{}\n".format(newFileName))
            return False

        self.doc.initialize()
        #logger.info(u"文件{}解析成功！开始读取数据......".format(fileName))
        res_file.write(u"--------- PDF-Transfer INFO：文件{}解析成功！尝试获取文件资源......\n".format(fileName))
        # 逐页读取pdf的内容，解析每一页的layout，对段落进行还原，将跨页的段落进行拼接
        if not self.doc.is_extractable:  # 检测文档是否提供txt转换
            raise PDFTextExtractionNotAllowed  # 使用raise显示地引发异常，后续不再执行
        else:
            try:
                pdfRsrcmgr = PDFResourceManager()  # PDF资源管理器
                laparmas = LAParams()
                self.device = PDFPageAggregator(pdfRsrcmgr, laparams=laparmas)  # 创建一个PDF设备对象
                self.interpreter = PDFPageInterpreter(pdfRsrcmgr, self.device)  # PDF解释器对象
                self.page_num = 0
                self.start_time_s = datetime.datetime.now()
                for _ in self.doc.get_pages():
                    self.page_num += 1

                end_time_s = datetime.datetime.now()
                cost_time_s = (end_time_s - self.start_time_s).seconds + 1.
                if (self.page_num / cost_time_s) < 1.:
                    res_file.write(u"--------- PDF-Transfer ERROR：文件资源获取异常，单页资源获取时间 > 1s，平均耗时{}页/秒，文件不可解\n".format(
                        self.page_num / cost_time_s))
                    return False
                res_file.write(u"--------- PDF-Transfer INFO：文件资源获取完毕，平均耗时{}页/秒\n".format(
                    self.page_num / cost_time_s))
            except:
                #logger.error(u"文件资源获取失败，不可解，转化失败，文件名：{},错误：{}".format(newFileName, traceback.format_exc()))
                res_file.write(u"--------- PDF-Transfer ERROR：文件资源获取失败，不可解读\n")
                return False
            res_file.flush()
        return True

    u"""
    1、打开并读取pdf的所有内容
    2、根据分页参数，将pdf的内容写入一个或者多个txt文件。同时完成句号分割等
    """
    def changePdfToTxt(self, fileName, dir="../pdf", resDir = "../result", page_range=None):
        extractable = self.decrypt_pdf_file(fileName, dir)
        self.page_range = page_range if page_range is not None else range(1000000)
        if not extractable:
            return False, [], {}, {}, ""  # 不可解析的文件

        try:
            self.pdftableExtractor = PdfTablesExtractor(self.page_num, self.pdfName)
            self.pdftableExtractor.load_pdf_tables()
            pageNum, page_context, common_head = self.readPdfInPages()  # 打开并读取pdf的所有内容
        except:
            self.pdftableExtractor.faild = True
            self.pdftableExtractor.checkAndWaitThreadEnd()   # 等待表格线程回收
            #logger.error(u"文件{}解析失败！无法读取内容，跳过...".format(fileName))
            #logger.error(u"失败原因：{}".format(traceback.format_exc()))
            res_file.write(u"--------- PDF-Transfer ERROR：文件{}解析失败！无法读取内容，跳过...\n".format(fileName))
            pageNum = 0
        if not pageNum:
            return False, [], {}, {}, ""

        result_dict = {}
        for pageNo in range(self.page_num):
            result_dict[str(pageNo + 1)] = []
            for paragraph in page_context[pageNo]:
                ##logger.info("paragraph=%s" % (paragraph))
                paragraph_split_sen = self.writeAParagraph(paragraph)
                result_dict[str(pageNo + 1)].extend(paragraph_split_sen)
        self.pdftableExtractor.checkAndWaitThreadEnd()
        self.pdftableExtractor.clean_with_tables_data(result_dict)

        result_file_name = []
        res_file.seek(0)
        res_file.truncate()
        if self.storeToFile:  # 写入文件的模式
            file_num = pageNum // self.txtMaxPageNum
            if pageNum % self.txtMaxPageNum > 0: file_num += 1
            for i in range(file_num):
                lowb = i * self.txtMaxPageNum
                upb = min((i + 1) * self.txtMaxPageNum + 2, pageNum)
                # #logger.info(lowb, upb)
                for pageNo in range(lowb, upb):
                    for sen in result_dict[str(pageNo + 1)]:
                        res_file.write(str(sen["origin"]) + '\n')
                    res_file.write(">>>>>>>>>>>>>>>>>>>>>>>第 %d 页结束>>>>>>>>>>>>>>>>>>>>>>>\n" % (pageNo + 1))
                    res_file.flush()

        return True, result_file_name, result_dict, self.pdftableExtractor.page_tables, common_head

    u"""
    向文件中写入当前的段落，段落试图按。！；：进行分割，在一些长度阈值的限制下，可能不会按；：分割
    返回当前段落的所有分割句子
    """
    def writeAParagraph(self, paragraph):
        #段落试图按。！；进行分割，在一些长度阈值的限制下，可能不会按；分割
        if self.judgeSplitable(paragraph, pattern=u"[。；！]"):
            sentences = re.split(u"[。；！]", paragraph)
        else:  # 不合适，只按。！划分
            sentences = re.split(u"[。！]", paragraph)

        #if len(sentences) == 1 and sentences[0].find(u"：") == -1:  # 跳过所有不含。；！：的句子（若是一个句子，split后至少会有第二元为空字符）
        #    return []

        # #logger.info("has sentence %d" % len(sentences))
        paragraph_split_sen = []
        for s in sentences:
            s = s.strip()
            sen = [s]
            if self.judgeSplitable(s, pattern=u"："):
                sen = s.split(u"：")
            for str in sen:
                if len(str) < 1 or len(str) > 1200:  # 若这里还出现长度小于10的子句，说明不是被：分出来的，要么是。分开的东西，要不就是不带标点的小标题
                    continue
                paragraph_split_sen.append({"origin": str})
        return paragraph_split_sen

    u"""
    根据给定的路径打开一个pdf文档，返回其操作对象
    """
    def openPdfDoc(self, fileName):
        file = open(fileName, 'rb')  # 二进制读
        praser = PDFParser(file)  # 创建pdf文档分析器
        doc = PDFDocument()  # 创建一个pdf文档
        praser.set_document(doc)
        doc.set_parser(praser)
        return file, praser, doc

    u"""
    1、打开指定的pdf，若是加密（密码为空），尝试解密后再打开
    2、遍历一定页码（此处定为30页），确定pdf的页眉
    3、逐页读取pdf的内容，解析每一页的layout，对段落进行还原，将跨页的段落进行拼接
    """
    def readPdfInPages(self):
        # 遍历60页，查找pdf的公共页眉
        page_commen_head = self.get_common_head()
        #logger.info(u"文件公共页眉为：%s" % "".join(page_commen_head))

        pages_context = []  # 准备按页缓存数据
        #  遍历列表，每次处理一个page的内容
        pagecnt = 0
        last_page_endl = True  # 前一页的内容正常结束
        last_row_endl = True  # 本页前一行正常结束
        for page in self.doc.get_pages():
            pages_context.append([])  # a new page
            if pagecnt not in self.page_range: continue
            self.interpreter.process_page(page)  # 接受该页的LTPage对象
            layout = self.device.get_result()  # 这里layout是一个LTPage对象 里面存放着 这个page解析出的各种对象 一般包括
            # LTTextBox, LTFigure, LTImage, LTTextBoxHorizontal 等等 想要获取文本就获得对象的text属性

            layout_cnt = 0
            layout_max = 0
            text_layout = []
            for x in layout:  # 去除页眉： 规则：凡是layout与页眉layout一致的都去掉
                if isinstance(x, LTTextBoxHorizontal):
                    text = "".join(x.get_text().split())
                    if text.strip().replace(" ", "") in page_commen_head:
                        # print("页眉命中， {}".format(page))
                        continue
                    layout_max += 1
                    text_layout.append(x)

            for x in text_layout:  # 处理页眉以外的正文
                layout_cnt += 1
                text = x.get_text()
                if self.has_meaning_str(text):  # 只处理句子中至少含有一个汉字的数据（达到去掉一些表格项和无中文页码的作用）
                    if text.find(" \n"):  # 包含某段话的结尾（观察数据发现，只要是段落尾，就会在换行符前多一个空格）
                        texts = text.split(" \n")  # 一个layout里可能有多个段落，拆分开处理
                        for idx in range(len(texts)):
                            # 显然，一个layout里的多个段落，除最后一个以外一定是完备的
                            endl = False if idx == len(texts) - 1 else True
                            # 根据两个标识位，可能追加到上一个的结尾，也可能自成一段
                            last_row_endl, last_page_endl = self.addNewSentence(texts[idx], last_row_endl,
                                                            last_page_endl, pagecnt, pages_context, endl)
                    else:  # 若一个layout里不存在这样一个段落结尾，只能认为他是一段没有结束的话
                        last_row_endl, last_page_endl = self.addNewSentence(text, last_row_endl,
                                                                            last_page_endl, pagecnt, pages_context,
                                                                            endl=False)
                if layout_cnt == layout_max:  # 本页文本扫完，根据当前最后一行的情况设置当前页的正文是否结束
                    last_page_endl = last_row_endl

            # #logger.info(layout_cnt, layout_max)
            # #logger.info("page %d finish" % (pagecnt + 1))
            pagecnt += 1
            if pagecnt % 1 == 0:
                #logger.info(u"已扫描读取%d页数据 " % (pagecnt))
                res_file.write(u"--------- PDF-Transfer INFO：已扫描读取%d页数据 \n" % (pagecnt))
                res_file.flush()
                #break
            #if pagecnt == 20:
            #    break
        return pagecnt, pages_context, page_commen_head[0]

    u"""
    根据上一页/行是否已经结束。对可能跨页的段落句子进行合并
    """
    def addNewSentence(self, text, last_row_endl, last_page_endl, pagecnt, pages_context, endl):
        split_text = text.split("\n")
        ## 对于长度
        #print(split_text, list(map(len, split_text)), last_row_endl)
        split_text = [unit for unit in split_text if self.has_meaning_str(unit)]
        text = "".join(split_text)
        text = text.strip()
        if not self.has_meaning_str(text):  #视作结束了一行
            return last_row_endl, last_page_endl
        # #logger.info("Page%d" % pagecnt, x.get_text(), last_row_endl, last_page_endl)

        if last_row_endl:  # 上一行结束了，当前格可能是多个表格之类的值，长度比较小
            # 遍历split_text，所有长度<一个段落第一行最小长度的句子都被视作独立一小节
            idx = 0
            while idx < len(split_text) and len(split_text[idx]) < self.first_row_len:
                #unit_len = list(map(len, split_text[idx].split(" ")))
                #if 1 not in unit_len:  # 会拆出单字的话就不拆了
                #for unit in split_text[idx].split(" "):
                #    pages_context[pagecnt].append(unit)
                #    last_row_endl = True
                #else:
                pages_context[pagecnt].append(split_text[idx].replace(" ", ""))
                last_row_endl = True
                idx += 1

            if idx < len(split_text):  # 还有剩的，说明还有一段的一部分或者完整
                text = "".join(split_text[idx:]).strip()
                """
                if len(split_text[idx]) - self.countNumberAndEng(split_text[idx]) >= self.row_max_len: #这一行的长度显然应该不是新一行
                    last_page_endl = self.addSentenceAftarLastRow(last_page_endl, pages_context, pagecnt, text, endl)
                else:"""
                pages_context[pagecnt].append(text)  ##新起一行
                last_row_endl = endl
        else:  #  上一行没结束，在没遇到下一个段落结束符号的情况下，当前layout一定是拼上一行
            last_row_endl = endl
            last_page_endl = self.addSentenceAftarLastRow(last_page_endl, pages_context, pagecnt, text, endl)
        return last_row_endl, last_page_endl

    def countNumberAndEng(self, str):
        count = 0
        for ch in str:
            if self.isNumber(ch) or self.isCharacter(ch) or self.isEngComa(ch):
                count += 1
        return count / 2.0

    def addSentenceAftarLastRow(self, last_page_endl, pages_context, pagecnt, text, endl):
        if last_page_endl:  # 上一行没结束但是上一页结束了
            pages_context[pagecnt][-1] += text
        else:  ##上一页的最后一行没结束
            try:
                pages_context[self.lastPage(pages_context, pagecnt)][-1] += text
            except:
                res_file.write("--------- PDF-Transfer ERROR：error occur! page={}, text={}\n".format(pagecnt, text))
                exit(0)
            last_page_endl = endl
        return last_page_endl

    u"""
        找到最近的可以补上内容的一页（有时可能因为中间
    """
    def lastPage(self, pages_context, pagecnt):
        while pagecnt >= 1:
            pagecnt -= 1
            if len(pages_context[pagecnt]):
                return pagecnt
        for i in range(len(pages_context)):
            #logger.info
            res_file.write("Page %d has rows %d\n" % (i, len(pages_context[i])))

    u"""
    判断是否为汉字字符串
    存在汉字，判断为汉字字符串
    """
    def isChina(self, _str):
        for ch in _str:
            if u'\u4e00' <= ch <= u'\u9fff':
                return True
        return False

    def isEng(self, _str):
        for ch in _str:
            if 'a' <= ch <= 'z' or 'A' <= ch <= 'Z':
                return True
        return False

    # 获得中文\英文字符串
    def has_meaning_str(self, _str):
        if len(_str) < 3: return False
        for i in _str:
            if self.isChina(i) or self.isEng(i):
                return True
        return False

    # 确定是否有公共文件页眉
    def get_common_head(self):
        common_head_cnt = dict()  # 对多个页首部layout的拼接头进行枚举计数
        common_head_dict = dict()  # 对多个页首部的layout拼接头的实际进行保存，后续要用来消除页眉
        pagecnt = 0
        row_len_cnt = {}
        for page in self.doc.get_pages():
            self.interpreter.process_page(page)
            ##接受该页的LTPage对象
            pagecnt += 1
            layout = self.device.get_result()
            layout_buffer = []
            for x in layout:
                if (isinstance(x, LTTextBoxHorizontal)):  # 获取每页第一个layout
                    ## 一个layout里可能有多行PDF数据（注意是按PDF视觉上的一行插入的\n）
                    ##挑选其中的众数作为这个PDF一行可能的实际字数
                    text_split = [ "".join(row.split()) for row in x.get_text().split("\n")]
                    if len(text_split) == 2 and not len(text_split[-1]):  # 算一下一行满能有多长
                        row = text_split[0]
                        if len(row) not in row_len_cnt: row_len_cnt[len(row)] = 0
                        row_len_cnt[len(row)] += 1 if len(row) > 25 else 0

                    text = "".join(x.get_text().split())
                    layout_buffer.append(text)
                    text = "".join(layout_buffer)
                    if text not in common_head_cnt:
                        common_head_cnt[text] = 0
                        common_head_dict[text] = layout_buffer[:]
                    common_head_cnt[text] += 1
                    if len(layout_buffer) == 10:  # 认为页眉最多分散到5个layout里
                        break
            del layout_buffer[:]
            if pagecnt == 60:
                break
        common_head_cnt = sorted(common_head_cnt.items(), key=lambda x: (x[1], len(x[0])), reverse=True)
        assert(len(common_head_cnt))

        common_head, cnt = common_head_cnt[0]
        common_head_list = [head.strip().replace(" ", "") for head in common_head_dict[common_head]]
        # 因为页眉可能占地很多，要去掉他的长度
        for head in common_head_dict[common_head]:
            if len(head.replace('\n', '')) in row_len_cnt:
                row_len_cnt[len(head.replace('\n', ''))] -= cnt
        row_len_cnt = sorted(row_len_cnt.items(), key=lambda x: (x[1], x[0]), reverse=True)
        self.row_max_len, self.first_row_len = [row_len_cnt[0][0], row_len_cnt[0][0] - 2] if len(row_len_cnt) else [25, 23]

        return common_head_list

if __name__=="__main__":
    import getopt
    import sys
    opts, args = getopt.getopt(sys.argv[1:], "f:", ["file="])
    pdfName = "P020180829537984246089.pdf"
    for opt,arg in opts:
        if opt in ("-f","--file"):
            pdfName = arg

    dir = "./static/pdf/"
    task = Pdf2TxtManager(type="test")
    res_file = open("static/txt/{}.txt".format(pdfName.replace(".pdf", "")), "a", encoding="utf-8")
    try:
        success, result_file_name, result_dict, _, common_head = task.changePdfToTxt(fileName=pdfName, dir=dir, page_range=range(50), resDir="./static/txt/")
        if not success:
            res_file.writelines(["--------- ERRO: 不可解的文件，解析失败！"])
    except:
        res_file.writelines(["--------- ERRO: 解析期间发生意外，"])
    res_file.close()
