import pdfplumber
import threading
import datetime
#from consoleLogger import logger
import traceback
import re

class PdfTablesExtractor:

    def __init__(self, page_num, pdf_name, max_thread=10):
        self.page_num = page_num
        self.pdf_name = pdf_name
        self.pdf_obj = pdfplumber.open(pdf_name)
        self.max_thread = max_thread
        self.thread = []
        self.debug = {}
        self.faild = False
        self.faild_flag = False

    def load_pdf_tables(self):
        # 预先读取pdf，获取每一页的内容。然后用tabula逐页读取表格内容，对比后，筛选每个表格前面那句话
        self.start_time_s = datetime.datetime.now()
        self.page_tables = {}
        previous_table = None
        try:
            for pid in range(self.page_num):
                self.page_tables[str(pid + 1)] = []
                for table in self.pdf_obj.pages[pid].extract_tables():
                    if len(table) == 0:
                        continue
                    elif len(table) <= 3:  # 太短了要不就和前面或者后面合并，要不就是丢了
                        if previous_table:
                            flag, table_merge = self.is_table_mergeable(previous_table, table)
                            if flag:
                                previous_table.extend(table_merge)
                        continue
                    self.page_tables[str(pid + 1)].append(table)
                    previous_table = table
        except:
            print(traceback.format_exc())
            exit(0)

    def is_table_mergeable(self, table1, table2):
        # 首先是列数相等
        def isNumber(str_):
            try:
                float(str_.replace(",", "").replace("，", ""))
            except:
                return False
            return True

        def isPercent(str_):
            if len(str_) < 2: return False
            return str_[-1] == "%"

        if len(table1[0]) != len(table2[0]): return False, table2
        if table1[0] == table2[0]: return True, table2[1:]
        flag = True
        for data, data_ in zip(table1[-1], table2[0]):
            if data is None and data_ is None:
                continue
            if data is None or data_ is None:
                flag = False
                break

            dn, dn_ = isNumber(data), isNumber(data_)
            pn, pn_ = isPercent(data), isPercent(data_)
            if dn != dn_:  # 必须同时是数字
                flag = False
                break
            if pn != pn_:  # 或者同时是百分比
                flag = False
                break
            # 此时他们要么同时是数字/百分比, 要么同时 既不是数字，也不是百分比（即同时是普通字符串）
        return flag, table2




    def checkAndWaitThreadEnd(self):
        print("--------- PDF-Transfer INFO：等待pdf表格逐页解析结果... ...")
        for i in range(len(self.thread)):
            self.thread[i].join()
        end_time_s = datetime.datetime.now()
        cost_time_s = (end_time_s - self.start_time_s).seconds
        print("--------- PDF-Transfer INFO：pdf表格解读完毕,总耗时{}处理{}页".format(cost_time_s, self.page_num))
        print("--------- PDF-Transfer INFO：平均耗时{}页/秒".format(self.page_num / cost_time_s + 1))

    def tablesdata2Set(self, tabula_res, table_range):  # 输入参数：tabula的解析结果，处理几个表
        page_tables = []
        union_set = set()
        for table_num in table_range:
            table_data = tabula_res[table_num]
            page_tables.append([])
            for row in range(len(table_data)):
                # print(len(table_data[row]),table_data[row])
                for column in range(len(table_data[row])):
                    if table_data[row][column] is None: continue
                    data_unit = table_data[row][column].replace(" ", "")
                    if not len(data_unit): continue
                    #extend_list = data_unit.split('\r') if data_unit.find('\r') != -1 else [data_unit]
                    extend_list = re.split("[0-9.\n\r]", data_unit)
                    page_tables[table_num].extend(extend_list)
            if len(union_set):
                # print(union_set, union_set & set(page_tables[table_num]))
                union_set = union_set & set(page_tables[table_num])
            else:
                union_set = set(page_tables[table_num])
        diff_sets = []
        # print(union_set)
        for table_num in table_range:
            diff_sets.append(set(page_tables[table_num]) - union_set)
        # print("diff_sets={}".format(diff_sets))
        return page_tables, diff_sets

    # 输入读取好的pdf结果，跟逐页和表格内容进行对比、清洗
    def clean_with_tables_data(self, pages_texts):
        # import copy
        # pages_texts = copy.deepcopy(pages_texts)
        page_tables = self.page_tables
        previous_page = None
        for page in range(1, len(pages_texts) + 1):
            page = str(page)
            self.debug[page] = ["page={}".format(page)]
            table_number = len(page_tables[page]) if page in page_tables else 0
            if table_number:
                last_page_head, last_page_idx = self.remove_tables_values(page_tables[page], pages_texts[page], page, table_number)
                if last_page_head:  # 上一页的最后一句话是这一页的表格的前一句
                    if previous_page and len(pages_texts[previous_page]):  # 前一句有最后一句话
                        if "table" not in pages_texts[previous_page]:
                            pages_texts[previous_page]["table"] = []
                        pages_texts[previous_page][-1]["table"].append(last_page_idx)  # -1 表示表格来自于下一页的第一个

            for idx in sorted(range(len(pages_texts[page])), reverse=True):
                if "table" in pages_texts[page][idx]: continue
                if len(pages_texts[page][idx]["origin"]) <= 8:
                    del pages_texts[page][idx]

    ##用每个表格中的独特取值，为每个table定位出一个大致的可命中范围
    def match_unique_value(self, diff_sets, result_dict, table_number):
        table_idx = 0
        hit_range = [(-1, len(result_dict))] * table_number
        sen_cnt = 0
        for sen_unit in result_dict:  # 扫过本页的每句话, 先根据每个表的特性，确定一个大概的起止范围
            sen = sen_unit["origin"].replace(" ", "").replace("（", "(").replace("）", ")").replace("，", ",") \
                .replace("；", ";").replace("：", ":")
            candidate_pool = set()
            candidate_pool.add(sen)
            if len(sen) >= 4:
                candidate_pool.add(sen[1:])
                candidate_pool.add(sen[:-1])
            for candidate in candidate_pool:
                if candidate in diff_sets[table_idx]:
                    left = hit_range[table_idx][0]
                    hit_range[table_idx] = (sen_cnt, sen_cnt) if left == -1 else (left, sen_cnt)
                    diff_sets[table_idx].remove(candidate)
                    break
                elif table_idx + 1 < table_number and candidate in diff_sets[table_idx + 1]:  # 检查是否已经跳到下一个表了
                    table_idx += 1
                    hit_range[table_idx] = (sen_cnt, sen_cnt)
                    diff_sets[table_idx].remove(candidate)
                    break
            sen_cnt += 1
        return hit_range

    def locat_remove_values(self, hit_range, tables_sets, result_dict, table_number):  # 再次扫描，确定所有要移除的值
        remove_dict = {}
        left = 0  # 根据确定的范围，移除所有可以移除的表格取值，并试图定位表格前第一句话（限制句子最小长度>8)
        for table_idx in range(table_number):
            remove_dict[table_idx] = []
            right = hit_range[table_idx + 1][1] if table_idx + 1 < table_number else len(result_dict)
            for sen_cnt in range(left, right):
                sen = result_dict[sen_cnt]["origin"].replace(" ", "").replace("（", "(").replace("）", ")").replace("，",
                                                                                                                  ",") \
                    .replace("；", ";").replace("：", ":")
                # print(sen, sen in tables_sets[table_idx], sen_cnt)
                candidate_pool = set()
                candidate_pool.add(sen)
                if len(sen) >= 4:
                    candidate_pool.add(sen[1:])
                    candidate_pool.add(sen[:-1])
                for candidate in candidate_pool:
                    if candidate in tables_sets[table_idx]:
                        remove_dict[table_idx].append(sen_cnt)
                        tables_sets[table_idx].remove(candidate)
                        break
            # 表格内都是数字，除表头外没有别的地方可以匹配的情况下，会有这种情况
            left = remove_dict[table_idx][-1] + 1 if len(remove_dict[table_idx]) else left
        return remove_dict

    def remove_tables_values(self, page_tables, result_dict, page, table_number):
        tables_sets, diff_sets = self.tablesdata2Set(page_tables, range(table_number))
        hit_range = self.match_unique_value(diff_sets, result_dict, table_number)
        # print(tables_sets, diff_sets)

        remove_dict = self.locat_remove_values(hit_range, tables_sets, result_dict, table_number)
        self.debug[page].append(hit_range)
        self.debug[page].append(remove_dict)

        last_page_head = False  # 一边删除一边确定表头
        last_page_idx = -1
        remove_list, remove_list_idx = [], []
        for table_idx in sorted(remove_dict.keys()):  # 定位不出范围的情况下，就不要了
            if not len(remove_dict[table_idx]):
                del remove_dict[table_idx]
                continue
            remove_list.append(remove_dict[table_idx])
            remove_list_idx.append(table_idx)

        for table_idx in sorted(range(len(remove_list)), reverse=True):
            for sen_idx in sorted(remove_list[table_idx], reverse=True):
                del result_dict[sen_idx]
            if sen_idx:
                # print(sen_idx - 1, pages_texts[sen_idx - 1])
                minrange = remove_list[table_idx - 1][-1] if table_idx else -1
                start_pot = sen_idx - 1
                while start_pot > minrange:
                    if len(result_dict[start_pot]["origin"]) > 8:
                        if "table" not in result_dict[start_pot]:
                            result_dict[start_pot]["table"] = []
                        result_dict[start_pot]["table"].append(remove_list_idx[table_idx])
                        break
                    else:
                        del result_dict[start_pot]
                    start_pot -= 1
                if start_pot == -1: last_page_head = True
            else:  # 前一句话在上一页
                last_page_head = True
                last_page_idx = - (remove_list_idx[table_idx] + 1) # -0 就看不出来表是这一页的还是上一页的了
        return last_page_head, last_page_idx