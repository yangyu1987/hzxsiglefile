from django.shortcuts import render
from django.views.generic.base import View
from django.http import HttpResponse,JsonResponse
from haozx import models
from haozx.tools import sendmsg
from utils.commom import *
from utils.config import *
import uuid,json,time
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
# Create your views here.


class TokenMaker(View):
    # 访问页面挂载token
    def get(self, request):
        tokens = models.Tokens()
        token= creToken()
        tokens.token = token
        tokens.timestamp = int(time.time() * 1000)
        tokens.save()
        msg_res = {
            'token': token,
        }
        return csrfJsonRes(HttpResponse,msg_res)

    def post(self, request):
        # 访问页面挂载token
        tokens = models.Tokens()
        token = creToken()
        tokens.token = token
        tokens.timestamp = int(time.time() * 1000)
        tokens.save()
        msg_res = {
            'token': token,
        }
        return csrfJsonRes(HttpResponse, msg_res)


class Sendmsg(View):
    # 短信发送模块
    def get(self, request):
        return render(request, 'haozx/sendmsg.html')
        # return HttpResponse('短信输入页面')

    def post(self, request):
        # 校验和发送
        phoneNum = request.POST.get('phoneNum', '')
        token = request.POST.get('token', '')
        smsCode = sms6num() # 短信验证码
        return sendsms(phoneNum=phoneNum,smsCode=smsCode,token=token)


class Checkmsg(View):
    # 短信校验模块
    def get(self, request):
        return render(request, 'haozx/checkmsg.html')
        # return HttpResponse('输入页面')

    def post(self, request):
        phoneNum = request.POST.get('phoneNum', '')
        smsCode = request.POST.get('smsCode', '')
        token = request.POST.get('token', '')
        return smsCheck(phoneNum,smsCode,token)


class GetRes(View):
    # 接口查询 并返回结果
    def get(self, request):
        return render(request, 'haozx/getmaininfo.html')
        # return HttpResponse(status=503)

    def post(self, request):
        # 5线程查询5个接口
        name = request.POST.get('name', '')
        idCard = request.POST.get('idCard', '')
        phoneNum = request.POST.get('phoneNum', '')
        token = request.POST.get('token', '')
        return resGet(name,idCard,phoneNum,token)


# 基础函数
def tokenCheck(token):
    # token 校验器
    def decor(func):
        @wraps(func)
        def check(*args,**kwargs):
            token_sql = models.Tokens.objects.filter(token=token)
            if token_sql:
                # 查到token
                token_sql = models.Tokens.objects.get(token=token)
                if timeCheckForToken(token_sql.timestamp, 30):
                    # 在30分钟内 执行函数
                    return func(*args, **kwargs)
                else:
                    # 超过30分钟
                    # token 校验失败
                    msg_res = {
                        'success': 0,
                        'info': 'Token Time Out',
                    }
                    response = HttpResponse(json.dumps(msg_res))
                    response['Content-Type'] = "application/json"
                    response['Access-Control-Allow-Origin'] = "*"
                    return response
            else:
                # 未查到token
                # token 校验失败
                msg_res = {
                    'success': 0,
                    'info': 'NO such Token',
                }
                response = HttpResponse(json.dumps(msg_res))
                response['Content-Type'] = "application/json"
                response['Access-Control-Allow-Origin'] = "*"
                return response
        return check
    return decor


def sendsms(phoneNum, smsCode, token):
    # 短信发送
    @tokenCheck(token=token)
    def sendsms_func(phoneNum,  smsCode, token):
                try:
                    # 检查库中是否有手机号，有说明查过了 更新数据
                    hzx = models.Haozx.objects.get(phoneNum=phoneNum, codeUsed=1)
                    hzx.smsCode = smsCode
                    # 发送短信
                    __business_id = uuid.uuid1()
                    params = json.dumps({'code': smsCode})
                    dy_res = sendmsg.send_sms(__business_id, phoneNum, "好甄信", "SMS_130915678", params)
                    dy_res = json.loads(dy_res)
                    if dy_res['Code'] == "OK":
                        # "Code": "OK" 表示发送成功
                        hzx.smsSend = 1  #
                        hzx.codeUsed = 0  # 把短信验证状态置为零
                        # hzx.timestamp = int(time.time() * 1000)  # 不在记录发送时间
                        hzx.save()
                        msg_res = {
                            'success': 1,
                            'info': 'Sms send suc',
                            'phoneNum': phoneNum,
                            'token': token
                        }
                        return csrfJsonRes(HttpResponse, msg_res)
                    else:
                        hzx.smsSend = 0
                        hzx.save()
                        msg_res = {
                            'success': 0,
                            'info': 'Sms send Fail',
                        }
                        return csrfJsonRes(HttpResponse, msg_res)
                except:
                    # 库中无查询记录 新建数据
                    hzx = models.Haozx()
                    # 在记录表中存入手机号和短信验证码
                    hzx.phoneNum = phoneNum
                    hzx.smsCode = smsCode
                    # 发送短信
                    __business_id = uuid.uuid1()
                    params = json.dumps({'code': smsCode})
                    dy_res = sendmsg.send_sms(__business_id, phoneNum, "好甄信", "SMS_130915678", params)
                    dy_res = json.loads(dy_res)
                    if dy_res['Code'] == "OK":
                        # "Code": "OK" 表示发送成功
                        hzx.smsSend = 1
                        # hzx.timestamp = int(time.time() * 1000) # 发送时间 时间统一在查询时候记录
                        hzx.save()
                        msg_res = {
                            'success': 1,
                            'info': 'Sms send suc',
                            'phoneNum': phoneNum,
                            'token': token
                        }
                        return csrfJsonRes(HttpResponse, msg_res)
                    else:
                        hzx.smsSend = 0
                        hzx.save()
                        msg_res = {
                            'success': 0,
                            'info': 'Sms send Fail',
                        }
                        return csrfJsonRes(HttpResponse, msg_res)

    return sendsms_func(phoneNum,  smsCode, token)


def smsCheck(phoneNum,smsCode,token):
    # 短信校验方法
    @tokenCheck(token=token)
    def smsCheck_func(phoneNum,smsCode,token):
        # 开始校验
        try:
            hzx = models.Haozx.objects.get(phoneNum=phoneNum, smsCode=smsCode)
            #  校验成功把校验状态设为1
            hzx.codeUsed = 1
            hzx.save()
            msg_res = {
                'success': 1,
                'info': 'Sms Check Suc',
                'phoneNum': phoneNum,
                'token': token
            }
            return csrfJsonRes(HttpResponse,msg_res)
        except:
            msg_res = {
                'success': 0,
                'info': 'Sms Check Fail'
            }
            return csrfJsonRes(HttpResponse, msg_res)

    return smsCheck_func(phoneNum,smsCode,token)


def resGet(name,idCard,phoneNum,token):
    # 获取结果
    @tokenCheck(token=token)
    def resGet_func(name, idCard, phoneNum):
        try:
            # sql_res = models.Haozx.objects.get(token=token, codeUsed=0) # 检测验证码是否用过
            sql_res = models.Haozx.objects.get(phoneNum=phoneNum, codeUsed=1)  # 说明短信验证已通过
        except:
            # 短信校验失败
            msg_res = {
                'success': 0,
                'info': 'msg check fail'
            }
            return csrfJsonRes(HttpResponse, msg_res)

        # 已有缓存数据 时间不超过1个月
        if sql_res.result and timeCheckForCookie(sql_res.timestamp, 30):
            # 暴露结果
            return csrfJsonRes(HttpResponse, sql_res.result)

            # 没有缓存数据或缓存时间大于一个月去接口查询
        else:
            sql_res.name = name
            sql_res.idCard = idCard
            mobile = str(sql_res.phoneNum)
            # 多线程
            executor = ThreadPoolExecutor(max_workers=5)
            res_dic = {}
            for s, u in SERVICENAMES.items():
                res = executor.submit(zx_test, *(name, idCard, mobile, s, u))
                res_dic[s] = res.result()
            # 获取基本状态
            common_stat = int(json.loads(res_dic.get('BlackListCheck'))['RESULT'])
            if common_stat < 0:
                # 输入有错误 手机号 或者身份证
                msg_res = {
                    'success': 0,
                    'info': 'error'
                }
                return csrfJsonRes(HttpResponse, msg_res)
            else:
                # 开始解析
                new_res = {
                    'PaymentBlackVerify': 0,
                    'BlackListCheckint': 0,
                    'courtDefaulter': {
                        'status': 2,
                        'detail': ''
                    },
                    'bankOverdue': {
                        'status': 2,
                        'detail': ''
                    },
                    'netLoanOverdue': {
                        'status': 2,
                        'detail': ''
                    },
                    'longLoanApply': {
                        'status': 2,
                        'detail': ''
                    },
                    'suspectFraud': {
                        'status': 2,
                        'detail': ''
                    }
                }
                # 被催收
                paymentBlackVerify_code = json.loads(res_dic['PaymentBlackVerify'])['detail']['resultCode']
                paymentBlackVerify_code = 0 if paymentBlackVerify_code == "2001" else 1
                new_res['PaymentBlackVerify'] = paymentBlackVerify_code

                # 逾期黑名单
                blackListCheck_code = json.loads(res_dic.get('BlackListCheck'))['RESULT']
                blackListCheck_code = 0 if blackListCheck_code == "2" else 1
                new_res['BlackListCheckint'] = blackListCheck_code

                # 风险详情
                riskListCombineInfo_code = json.loads(res_dic['RiskListCombineInfo'])['RESULT']
                riskListCombineInfo_code = 0 if riskListCombineInfo_code == "2" else 1
                if riskListCombineInfo_code == 0:
                    # 风险详情无结果
                    new_res['courtDefaulter']['status'] = 0  # 行政披露信息
                    new_res['bankOverdue']['status'] = 0  # 银行逾期名单信息
                    new_res['netLoanOverdue']['status'] = 0  # 网贷逾期名单信息
                    new_res['longLoanApply']['status'] = 0  # 多次申贷信息
                    new_res['suspectFraud']['status'] = 0  # 疑似欺诈申请信息
                else:
                    # 风险详情有结果 开始解析
                    parse_res(res_dic, new_res, 'courtDefaulter')
                    parse_res(res_dic, new_res, 'bankOverdue')
                    parse_res(res_dic, new_res, 'netLoanOverdue')
                    parse_res(res_dic, new_res, 'longLoanApply')
                    parse_res(res_dic, new_res, 'suspectFraud')

                sql_res.result = json.dumps(new_res)
                # 更新验证码为已用
                sql_res.codeUsed = 1
                sql_res.timestamp = int(time.time() * 1000)
                sql_res.save()
                # 暴露结果
                return csrfJsonRes(HttpResponse, new_res)

    return resGet_func(name,idCard,phoneNum)


def parse_res(res_dic,new_res,data_type):
    res = json.loads(res_dic['RiskListCombineInfo'])['riskList'][data_type]
    res_code = 0 if res['statCode'] == "2" else 1
    if res_code == 0:
        new_res[data_type]['status'] = 0
    else:
        new_res[data_type]['status'] = 1
        new_res[data_type]['detail'] = res['detailInfo']