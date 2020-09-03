# -*- coding: utf-8 -*-
from flask import Flask,request,render_template,url_for,session,escape,redirect,make_response
import json
import traceback
import threading
import os
app=Flask(__name__, template_folder="")
app.config.from_object('config')

txt_name_file ={}
name_file_dict = {"txt": txt_name_file}


@app.route('/',methods=['GET'])
def welcome():
    print('in welcome')
    return render_template("HomePage.html")

@app.route('/List',methods=['GET'])
def get_list():
    print(request.args)
    getType = request.args['type']
    content_list = list(name_file_dict[getType].keys())
    resp = {"successed":True, "List":content_list}
    print(resp)
    resp = json.dumps(resp)
    return resp

@app.route('/upload',methods=['GET','POST'])
def upload():

    resp = {"successed": True, "List": []}
    if request.method=='GET':
        print(request.args['type'])
    if request.method=='POST':
        try:
            print(request.form)
            print(request.files["file"])
            f = request.files["file"]
            upType = request.form['type']  ###原文都是Unicode,在操作文件时会报错
            filename = f.filename.encode('unicode_escape').decode('ascii')
        except:
            failed_Res = traceback.format_exc()
            message = "表单数据解析异常" + failed_Res
            resp["message"] = message
            resp["successed"] = False
            resp = json.dumps(resp)
            return resp

        #检查有没有重名
        pdf_filename = filename
        store_path = os.path.join("static", upType, pdf_filename)
        txt_filename = filename.replace(".pdf", ".txt")
        try:
            if not os.path.exists(store_path):
                f.save(store_path)
                name_file_dict["txt" if upType == "pdf" else upType][txt_filename] = True
            with open("static/" + upType + "/" + txt_filename, "w", encoding="utf-8") as res_file:
                res_file.writelines(["--------- INFO: 解析请求提交中，长时间无变化请检查后台日志..."])
            threading.Thread(target=runthread, args=([pdf_filename])).start()
        except:
            failed_Res = traceback.format_exc()
            message = "文件保存失败" + failed_Res
            resp["message"] = message
            resp["successed"] = False
            resp = json.dumps(resp)
            return resp
    resp = json.dumps(resp)
    return resp

@app.route('/txtPage.html',methods=['GET'])
def txtPage():
    return render_template('txtPage.html')

def runthread(pdfName):
    '''
    '''
    try:
        os.system("(python -u pdfToTxt.py -f {}) > {}.out".format(pdfName, pdfName))
    except:
        print(u"--------- ERROR: 解析程序执行失败")

def get_name_file(type, name_dict):
    directory = os.path.join("static", type)
    hasPrefix = lambda x: x.find("." + type) != -1
    target = []  # 所有作业目标，是（目录，json文件名二元组）
    print(u"--------- INFO:程序将遍历目录:{}，查找类型为{}的文件".format(directory, type))
    for dir, subdir, files in os.walk(directory):
        withPreifx = set(list(filter(hasPrefix, files)))
        for fileName in withPreifx:
            fileName = os.path.join(fileName)
            name_dict[fileName] = True
    print(name_dict)

print('当前已有文件：')
get_name_file("txt", txt_name_file)
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)