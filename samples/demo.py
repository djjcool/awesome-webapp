# encoding=utf-8
"""
    一个批量压缩小工具,帮朋友写的,先放这儿..
"""

from zipfile import *
from os import *
import zipfile

dirlist=[]
filelist=[]
for root,dirs,files in walk("F:\\awesome-webapp\\"):
    for dir in dirs: 
        dirlist.append(path.join(root,dir))
    for file in files: 
        filelist.append(path.join(root,file))
    print(path.join(root,file))
print("文件读取完成")

with ZipFile('scpwisdjjco.zip', 'a') as myzip:
    for i in filelist:
        myzip.write(i)
print("压缩完毕")
