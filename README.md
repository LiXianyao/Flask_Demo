# 运行方式
1. 激活 virtualenv

    - Linux / macOS: `` $ source venv/scripts/activate ``
    - Windows: `` $ venv\scripts\activate ``
2. 运行服务器

    在 flaskr 目录下输入命令`` python flaskr.py ``


# flaskr中的文件结构
|static		# 所有静态文件的保存位置，包括css\js\音频\图像和swf
    |css	# 存放css文件
    |js		# 存放js文件
    |image	# 存放imagePage.html页面用的图片文件，及文件名记录imageStorage.txt
    |images	# 存放Information.html页面用的图片文件（就是头像）
    |music	# 存放musicPage.html页面用的音乐文件，及文件名记录musicStorage.txt
    |video	# 存放videoPage.html页面用的动画文件，及文件名记录videoStorage.txt

|config.py	# 框架的配置文件
|flaskr.py	# 后台程序文件，url处理
|HomePage.html	# 网页文件
|imagePage.html
|informationPage.html
|musicPage.html
|videoPage.html

  # 修改源码 table.py 中 268行： x0, top, x1, bottom = bbox -》 top, x0, bottom, x1 = bbox

 # rename its dir from pdfminer/ -> pdfminer3k/
