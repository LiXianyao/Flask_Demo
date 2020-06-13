# -*- coding: utf-8 -*-
from flask import Flask,request,render_template,url_for,session,escape,redirect,make_response
import json
import traceback
app=Flask(__name__, template_folder="")
app.config.from_object('config')

music_name_file = {}
image_name_file = {}
video_name_file ={}
name_file_dict = {"music":music_name_file ,"image":image_name_file,"video":video_name_file}


@app.route('/',methods=['GET'])
def welcome():
    print('in welcome')
    return render_template("HomePage.html")

@app.route('/List/',methods=['GET'])
def get_list():

    print(request.args)
    getType = request.args['type']
    content_list = name_file_dict[getType].keys()
    resp = {"successed":True, "List":content_list}
    resp = json.dumps(resp)
    return resp

@app.route('/upload/',methods=['GET','POST'])
def upload():

    resp = {"successed": True, "List": []}
    if request.method=='GET':
        print(request.args['type'])
    if request.method=='POST':
        try:
            print(request.form)
            print(equest.files["file"])
            f = request.files["file"]
            upType = request.form['type'].encode("gbk")  ###原文都是Unicode,在操作文件时会报错
            filename = request.form["filename"]
        except(Exception, e):
            failed_Res = traceback.format_exc()
            message = "表单数据解析异常" + failed_Res
            resp["message"] = message
            resp["successed"] = False
            resp = json.dumps(resp)
            return resp

        #检查有没有重名
        try:
            flag = name_file_dict[upType][filename]
            filename += u"a"
        except:
            name_file_dict[upType][filename] = True

        filename = filename.encode("gbk")
        try:
            f_write = open("static/" + upType + "/" + upType + "Storage.txt", "a")
            f_write.write(filename + "\n")
            f_write.close()
            f.save("static/" + upType + "/" + filename)
        except(Exception, e):
            failed_Res = traceback.format_exc()
            message = "文件保存失败" + failed_Res
            resp["message"] = message
            resp["successed"] = False
            resp = json.dumps(resp)
            return resp

    resp = json.dumps(resp)
    return resp

@app.route('/musicPage.html',methods=['GET'])
def musicPage():
    return render_template('musicPage.html')

@app.route('/imagePage.html',methods=['GET'])
def imagePage():
    return render_template('imagePage.html')

@app.route('/videoPage.html',methods=['GET'])
def videoPage():
    return render_template('videoPage.html')

@app.route('/informationPage.html',methods=['GET'])
def informationPage():
    return render_template('informationPage.html')


def get_name_file(type, name_dict):
    fr = open("static/" + type + "/" + type + "Storage.txt","r")
    lines = fr.readlines()
    for line in lines:
        if len(line) == 0:
            continue
        print(line)
        name_dict[line] = True
print('当前已有文件：')
get_name_file("music", music_name_file)
get_name_file("image", image_name_file)
get_name_file("video", video_name_file)
if __name__ == '__main__':
    app.run(host='127.0.0.1')