#-*- coding:utf-8 –*-
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name: Lcal.py
# Purpose: 后处理
# Author: Bill & Liu
# Created: 22/6/2016
#-------------------------------------------------------------------------------
import os
import re
import glob
import copy
import string
import subprocess  
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from openpyxl import load_workbook
import pylab
pylab.mpl.rcParams['font.sans-serif'] = ['SimHei'] #指定默认字体    
pylab.mpl.rcParams['axes.unicode_minus'] = False #解决保存图像是负号'-'显示为方块的问题 
def dat2out(name):
	if os.path.exists('TestRES\\'+name+'.out'):
		data=np.loadtxt('TestRES\\'+name+'.out',skiprows =1)
		return data
	f=open('TestRES\\'+name+'.dat','r')
	f2=open('TestRES\\'+name+'.out','w+')
	lines=f.readlines()
	isSec=0
	for a in lines:
		b=a.split('\t')
		if b[0]=='Sec' and isSec==0:
			isSec=1
			f2.write(a)
			continue
		try:
			isn=1
			float(b[0])
		except:
			isn=0
		if isn==1:
			f2.write(a)
	f.close()
	f2.close()
	data=np.loadtxt('TestRES\\'+name+'.out',skiprows =1)
	return data
#-------------------------------------------------------------------------------
# 生成骨架曲线
#-------------------------------------------------------------------------------
def bacbone(name):
	data=np.loadtxt('TestRES\\'+name+'.out',skiprows =1)
	ll=len(data)
	P=data[0]
	for n in range(ll-1):
		if data[n+1][0]<data[n][0]: 
			P=np.vstack((P,data[n]))
	P1=P[0]
	P2=P[0]
	for m in range(len(P)-1):
		if P[m+1][1]>0: P1=np.vstack((P1,P[m+1]))
		else: P2=np.vstack((P2,P[m+1]))
	for aa in range(len(P1)):
		if aa!=0 and aa!=len(P1)-1 and np.abs(P1[aa][1]-P1[aa-1][1])<0.3 :
			P1[aa][0]=0
	for aa in range(len(P2)):
		if aa!=0 and aa!=len(P2)-1 and np.abs(P2[aa][1]-P2[aa-1][1])<0.3 :
			P2[aa][0]=0
	P1=np.mat(P1)
	P2=np.mat(P2)
	aaa=np.array(P1[np.where(P1[:,0]!=0)[0],:])
	bbb=np.array(P2[np.where(P2[:,0]!=0)[0],:])
	res=np.vstack((bbb[::-1],aaa))
	return res
#-------------------------------------------------------------------------------
# 通道读取
#-------------------------------------------------------------------------------
def readTune(tu,name):
	f=open('TestRES\\'+name+'.TXT','r')
	st1=0
	res=[]
	testst=[]
	pat2=re.compile(r'-?\d*\.\d+')
	lines=f.readlines()
	for a in lines:
		b=a.split(':')
		if b[0].decode('UTF8')==u'试验状态':
			st1=1
			testst.append(b[1].strip('\n').strip())
			continue
		if st1==1:
			try:
				tt=int(b[0])
				if tt==tu:
					try:
						d=float(re.findall(pat2,b[1])[0])
						res.append(d)
					except:
						res.append(0)
				else:
					continue
			except:
				st1=0
				continue
	f.close()
	ans=[[testst[i],res[i]] for i in range(len(testst))]
	return ans

#-------------------------------------------------------------------------------
# 分段:提出位移信号的关键节点行号
#-------------------------------------------------------------------------------
def keypoint(xx):
	lim=100
	eps=0.2
	res=[]
	resp=[]	
	ind=np.where(np.abs(xx)<eps)[0].tolist()
	while 1:
		gr=[a for a in ind if abs(a-ind[0])<lim]
		res.append(gr[np.min(np.where(np.abs(xx[gr])==min(np.abs(xx[gr]))))])
		ind=[a for a in ind if a not in gr]
		if len(ind)==0: break
	n=len(res)-1
	for ii in range(n):
		up=res[ii+1]
		low=res[ii]
		s1=max(xx[range(low,up)])
		s2=min(xx[range(low,up)])
		if s1+s2>0: resp.append(range(low,up)[xx[range(low,up)].tolist().index(s1)])
		else: resp.append(range(low,up)[xx[range(low,up)].tolist().index(s2)])
	#res.extend(resp)
	resp=resp+[0]
	ans=sorted(resp)
	ans=ans+[0]
	return ans
#-------------------------------------------------------------------------------
# 应变箱记录检查
#-------------------------------------------------------------------------------
def recCheck(name='C2-1'):
	f=open('TestRES\\'+name+'.TXT','r')
	st1=0
	res=[]
	pat2=re.compile(r'-?\d*\.\d+')
	lines=f.readlines()
	for a in lines:
		b=a.split(':')
		if b[0].decode('UTF8')==u'试验状态':
			st1+=1
			print b
	print ('\n\'%s\' 采样次数共有 %d 次~~\n'%(name,st1))
	f.close()
#-------------------------------------------------------------------------------
# 墩顶位移计(T)基线调零
#-------------------------------------------------------------------------------
def baseline(name='C2-2'):
	Ttu=54	
	data0=readTune(Ttu,name)
	data1=copy.deepcopy(data0)
	for a in data1:
		a[0]=int(a[0].split('-')[0])
	data1=np.array(data1)
	#data2=copy.deepcopy(data1)
	ind=np.unique(data1[:,0])
	for a in ind:
		if a==0.0:
			for n in range(len(data1)):
				if data1[n,0]==a:data1[n,1]=0.0
		if a!=0.0:
			aver=np.mean(data1[np.where(data1[:,0]==a)[0]][:,1])
			for n in range(len(data1)):
				if data1[n,0]==a:data1[n,1]=data1[n,1]-aver
	return data1

#-------------------------------------------------------------------------------
# OpenSEES滞回
#-------------------------------------------------------------------------------
def MyHys(name='C2'):
#name='C2'
	wb = load_workbook(filename='TestPara.xlsx')
	sheet=wb['Sheet1']
	for x in range(50):
		if sheet['A'+str(x+2)].value==name:
			h=sheet['B'+str(x+2)].value
			b=sheet['C'+str(x+2)].value
			ds=sheet['D'+str(x+2)].value
			As=ds**2*3.14159*0.25
			ns=sheet['E'+str(x+2)].value
			m=sheet['F'+str(x+2)].value
			n=(ns-4-2*m)/2
			At=sheet['G'+str(x+2)].value**2*3.14159*0.25
			nt=sheet['H'+str(x+2)].value
			s=sheet['I'+str(x+2)].value
			P=sheet['J'+str(x+2)].value*1000
			L=sheet['K'+str(x+2)].value
	c=30
	fy=400
	fc=58
	ft=6
	size=10
	try:
		rec=dat2out(name)
		disp=rec[:,1]
		dispTH=disp[keypoint(disp)]
		npts=len(dispTH)
		np.savetxt('TH.disp',dispTH)
	except:
		dispTH=np.loadtxt('TH.disp')
		npts=len(dispTH)
	fid=open('paraHY.tcl','w+')
	fid.write("set b %f;\n"%(b))
	fid.write("set h %f;\n"%(h))
	fid.write("set c %f;\n"%(c))
	fid.write("set As %f;\n"%(As))
	fid.write("set m %d;\n"%(m))
	fid.write("set n %d;\n"%(n))
	fid.write("set fy %f;\n"%(fy))
	fid.write("set fc %f;\n"%(fc))
	fid.write("set ft %f;\n"%(ft))
	fid.write("set size %f;\n"%(size))
	fid.write("set L %f;\n"%(L))
	fid.write("set npts %d;\n"%(npts))
	fid.write("set Pload %f;"%(P))
	fid.close()
	p=subprocess.Popen('11.cmd',shell=False)
	p.wait()
	resD=np.loadtxt('INF\\Disp.out')[:,1]
	resF=np.loadtxt('INF\\Force.out')[:,1]*(-1)
	return(resD,resF)
#-------------------------------------------------------------------------------
# OpenSEES滞回 参数型
#-------------------------------------------------------------------------------
def MyHys2(h,b,ds,ns,m,At,nt,s,P,L):
	As=ds**2*3.14159*0.25
	n=(ns-4-2*m)/2
	P=P*1000
	c=30
	fy=400
	fc=58
	ft=7.6
	size=10
	dispTH=np.loadtxt('TH.disp')
	npts=len(dispTH)
	fid=open('paraHY.tcl','w+')
	fid.write("set b %f;\n"%(b))
	fid.write("set h %f;\n"%(h))
	fid.write("set c %f;\n"%(c))
	fid.write("set As %f;\n"%(As))
	fid.write("set m %d;\n"%(m))
	fid.write("set n %d;\n"%(n))
	fid.write("set fy %f;\n"%(fy))
	fid.write("set fc %f;\n"%(fc))
	fid.write("set ft %f;\n"%(ft))
	fid.write("set size %f;\n"%(size))
	fid.write("set L %f;\n"%(L))
	fid.write("set npts %d;\n"%(npts))
	fid.write("set Pload %f;"%(P))
	fid.close()
	p=subprocess.Popen('11.cmd',shell=False)
	p.wait()
	resD=np.loadtxt('INF\\Disp.out')[:,1]
	resF=np.loadtxt('INF\\Force.out')[:,1]*(-1)
	return(resD,resF)
#-------------------------------------------------------------------------------
# 绘图
#-------------------------------------------------------------------------------
#nlist=['C2','C3']
#for name in nlist:
#	#name='C2'
#	data=dat2out(name)
#	(preD,preF)=MyHys(name)	
#	xx=data[:,1]
#	yy=data[:,2]
#	fig=Figure()
#	fig.set_size_inches(10,10)
#	cv=FigureCanvas(fig)
#	ax=fig.add_axes([0.14, 0.14, 0.8, 0.6])
#	ax.grid(True)
#	ax.plot(preD,preF/1000,xx,yy)
#	cv.print_figure(name+'.png',dpi=300)
#-------------------------------------------------------------------------------
# 滞回预测
#-------------------------------------------------------------------------------
#name='G1'
##data=dat2out(name)
#(preD,preF)=MyHys(name)