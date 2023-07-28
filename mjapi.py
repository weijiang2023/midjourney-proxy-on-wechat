import time
import json
import requests
from common.log import logger


class _mjApi:
    def __init__(self, config):
        self.headers = {
            "Content-Type": "application/json",
        }
        self.proxy = config['discordapp_proxy']
        self.baseUrl = config['mj_url']
        self.headers["mj-api-secret"] = config['mj_api_secret']
        self.imagine_prefix = config['imagine_prefix']
        self.fetch_prefix = config['fetch_prefix']
        self.up_prefix = config['up_prefix']
        self.pad_prefix = config['pad_prefix']
        self.blend_prefix = config['blend_prefix']
        self.describe_prefix = config['describe_prefix']
        self.queue_prefix = config['queue_prefix']
        self.end_prefix = config['end_prefix']

    def set_user(self, user):
        self.user = user

    def set_mj(self, mj_url, mj_api_secret="", proxy=""):
        self.baseUrl = mj_url
        self.proxy = proxy
        self.headers["mj-api-secret"] = mj_api_secret

    def subTip(self, res):
        rj = res.json()
        if not rj:
            return False, "❌ MJ服务异常", ""
        code = rj["code"]
        id = rj['result']
        if code == 1:
            msg = "✅ 您的设计需求已提交\n"
            msg += f"🚀 正在快速创作中，请稍后\n"
            msg += f"📨 ID: {id}\n"
            return True, msg, rj["result"]
        else:
            return False, rj['description'], ""

    # 图片想象接口
    def imagine(self, prompt, base64=""):
        try:
            url = self.baseUrl + "/mj/submit/imagine"
            data = {
                "prompt": prompt,
                "base64": base64
            }
            if self.user:
                data["state"] = self.user
            res = requests.post(url, json=data, headers=self.headers)
            return self.subTip(res)
        except Exception as e:
            logger.exception(e)
            return False, "❌ 任务提交失败", None

    # 放大/变换图片接口
    def simpleChange(self, content):
        try:
            url = self.baseUrl + "/mj/submit/simple-change"
            data = {"content": content}
            if self.user:
                data["state"] = self.user
            res = requests.post(url, json=data, headers=self.headers)
            return self.subTip(res)
        except Exception as e:
            logger.exception(e)
            return False, "❌ 任务提交失败", None

    def reroll(self, taskId):
        try:
            url = self.baseUrl + "/mj/submit/change"
            data = {
                "taskId": taskId,
                "action": "REROLL"
            }
            if self.user:
                data["state"] = self.user
            res = requests.post(url, json=data, headers=self.headers)
            return self.subTip(res)
        except Exception as e:
            logger.exception(e)
            return False, "❌ 任务提交失败", None

    # 混合图片接口
    def blend(self, base64Array, dimensions=""):
        try:
            url = self.baseUrl + "/mj/submit/blend"
            data = {
                "base64Array": base64Array
            }
            if dimensions:
                data["dimensions"] = dimensions
            if self.user:
                data["state"] = self.user
            res = requests.post(url, json=data, headers=self.headers)
            return self.subTip(res)
        except Exception as e:
            logger.exception(e)
            return False, "❌ 任务提交失败", None

    # 识图接口
    def describe(self, base64):
        try:
            url = self.baseUrl + "/mj/submit/describe"
            data = {"base64": base64}
            if self.user:
                data["state"] = self.user
            res = requests.post(url, json=data, headers=self.headers)
            return self.subTip(res)
        except Exception as e:
            logger.exception(e)
            return False, "❌ 任务提交失败", None

    # 查询提交的任务信息
    def fetch(self, id):
        try:
            url = self.baseUrl + f"/mj/task/{id}/fetch"
            res = requests.get(url, headers=self.headers)
            rj = res.json()
            if not rj:
                return False, "❌ 查询任务不存在", None
            user = None
            ruser = None
            if self.user:
                user = json.loads(self.user)
            if rj['state']:
                ruser = json.loads(rj['state'])
            if user and ruser:
                if user['user_id'] != ruser['user_id']:
                    return False, "❌ 该任务不属于您提交，您无权查看", None
            status = rj['status']
            startTime = ""
            finishTime = ""
            imageUrl = ""
            timeup = 0
            if rj['startTime']:
                startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rj['startTime']/1000))
            if rj['finishTime']:
                finishTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rj['finishTime']/1000))
                timeup = (rj['finishTime'] - rj['startTime'])/1000
            msg = "✅ 查询成功\n"
            msg += f"-----------------------------\n"
            msg += f"📨 ID: {rj['id']}\n"
            msg += f"🚀 进度：{rj['progress']}\n"
            msg += f"⌛ 状态：{self.status(status)}\n"
            if rj['finishTime']:
                msg += f"⏱ 耗时：{timeup}秒\n"
            if rj["action"] == "DESCRIBE":
                msg += f"✨ 描述：{rj['prompt']}\n"
            else:
                msg += f"✨ 描述：{rj['description']}\n"
            if ruser and ruser["user_nickname"]:
                msg += f"🙋‍♂️ 提交人：{ruser['user_nickname']}\n"
            if rj['failReason']:
                msg += f"❌ 失败原因：{rj['failReason']}\n"
            if rj['imageUrl']:
                imageUrl = self.get_img_url(rj['imageUrl'])
                msg += f"🎬 图片地址: {imageUrl}\n"
            if startTime:
                msg += f"⏱ 开始时间：{startTime}\n"
            if finishTime:
                msg += f"⏱ 完成时间：{finishTime}\n"
            msg += f"-----------------------------"
            return True, msg, imageUrl
        except Exception as e:
            logger.exception(e)
            return False, "❌ 查询失败", None

    # 轮询获取任务结果
    def get_f_img(self, id):
        try:
            url = self.baseUrl + f"/mj/task/{id}/fetch"
            status = ""
            rj = ""
            while status != "SUCCESS" and status != "FAILURE":
                time.sleep(3)
                res = requests.get(url, headers=self.headers)
                rj = res.json()
                status = rj["status"]
            if not rj:
                return False, "❌ 任务提交异常", None
            if status == "SUCCESS":
                msg = ""
                startTime = ""
                finishTime = ""
                imageUrl = ""
                action = rj["action"]
                ruser = None
                timeup = 0
                if rj['state']:
                    ruser = json.loads(rj['state'])
                msg += f"-----------------------------\n"
                if rj['finishTime']:
                    timeup = (rj['finishTime'] - rj['startTime'])/1000
                if action == "IMAGINE":
                    msg += f"🎨 创作成功\n"
                elif  action == "UPSCALE":
                    msg += "🎨 放大成功\n"
                elif action == "VARIATION":
                    msg += "🎨 变换成功\n"
                elif action == "DESCRIBE":
                    msg += "🎨 转述成功\n"
                elif action == "BLEND":
                    msg += "🎨 混合绘制成功\n"
                elif action == "REROLL":
                    msg += "🎨 重新绘制成功\n"
                msg += f"📨 ID: {id}\n"
                if action == "DESCRIBE":
                    msg += f"✨ 描述：{rj['prompt']}\n"
                else:
                    msg += f"✨ 描述：{rj['description']}\n"
                if rj['finishTime']:
                    msg += f"⏱ 耗时：{timeup}秒\n"
                if action == "IMAGINE" or action == "BLEND" or action == "REROLL":
                    msg += f"🪄 放大 U1～U4，变换 V1～V4：使用[{self.up_prefix[0]} + 任务ID]\n"
                    msg += f"✍️ 例如：{self.up_prefix[0]} {id} U1\n"
                if ruser and ruser["user_nickname"]:
                    msg += f"🙋‍♂️ 提交人：{ruser['user_nickname']}\n"
                if rj['imageUrl']:
                    imageUrl = self.get_img_url(rj['imageUrl'])
                    msg += f"🎬 图片地址: {imageUrl}\n"
                if rj['startTime']:
                    startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rj['startTime']/1000))
                    msg += f"⏱ 开始时间：{startTime}\n"
                if rj['finishTime']:
                    finishTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rj['finishTime']/1000))
                    msg += f"⏱ 完成时间：{finishTime}\n"
                msg += f"-----------------------------"
                return True, msg, imageUrl
            elif status == "FAILURE":
                failReason = rj["failReason"]
                return False, f"❌ 请求失败：{failReason}", ""
            else:
                return False, f"❌ 请求失败：服务异常", ""
        except Exception as e:
            logger.exception(e)
            return False, "❌ 请求失败", ""

    # 查询任务队列
    def task_queue(self):
        try:
            url = self.baseUrl + f"/mj/task/queue"
            res = requests.get(url, headers=self.headers)
            rj = res.json()
            msg = f"✅ 查询成功\n"
            if not rj:
                msg += "❌ 暂无执行中的任务"
                return True, msg
            user = None
            ruser = None
            if self.user:
                user = json.loads(self.user)
            for i in range(0, len(rj)):
                if rj[i]['state']:
                    ruser = json.loads(rj[i]['state'])
                if (ruser and user and user['user_id'] == ruser['user_id']) or not ruser:
                    msg += f"-----------------------------\n"
                    msg += f"📨 ID: {rj[i]['id']}\n"
                    msg += f"🚀 进度：{rj[i]['progress']}\n"
                    msg += f"⌛ 状态：{self.status(rj[i]['status'])}\n"
                    msg += f"✨ 描述：{rj[i]['description']}\n"
                    if ruser and ruser["user_nickname"]:
                        msg += f"🙋‍♂️ 提交人：{ruser['user_nickname']}\n"
                    if rj[i]['failReason']:
                        msg += f"❌ 失败原因：{rj[i]['failReason']}\n"
                    if rj[i]['imageUrl']:
                        imageUrl = self.get_img_url(rj[i]['imageUrl'])
                        msg += f"🎬 图片地址: {imageUrl}\n"
                    startTime = ""
                    if rj[i]['startTime']:
                        startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rj[i]['startTime']/1000))
                    if startTime:
                        msg += f"⏱开始时间：{startTime}\n"
            msg += f"-----------------------------\n"
            msg += f"共计：{len(rj)}个任务在执行"
            return True, msg
        except Exception as e:
            logger.exception(e)
            return False, "❌ 查询失败"

    def status(self, status):
        msg = ""
        if status == "SUCCESS":
            msg = "已完成"
        elif status == "FAILURE":
            msg = "失败"
        elif status == "SUBMITTED":
            msg = "已提交"
        elif status == "IN_PROGRESS":
            msg = "处理中"
        else:
            msg = "未知"
        return msg

    def get_img_url(self, image_url):
        if self.proxy and image_url.startswith("https://cdn.discordapp.com"):
            image_url = image_url.replace("https://cdn.discordapp.com", self.proxy)
        return image_url

    def help_text(self):
        help_text = "🎨欢迎使用AI原优舍Tshirt图案定制服务！🎨\n"
        help_text += f"您只需输入文字描述图案需求，我们即能为您定制充满个性的Tshirt。\n"
        help_text += f"让我们开始创作属于自己的Tshirt吧！\n"
        help_text += f"以下是一些创作的例子及相应模版\n"
        help_text += f"@bot /mj a tshirt logo of two cats, with background color to be yellow\n"
        help_text += f"@bot /mj a tshirt logo of two cats, with background color to be orange\n"
        help_text += f"@bot /mj a tshirt logo of two cats, with background color to be red\n"
        help_text += f"@bot /mj a tshirt logo of two cats, with background color to be purple\n"
        help_text += f"@bot /mj a tshirt logo of two cats, with background color to be blue\n"
        help_text += f"@bot /mj a tshirt logo of two cats, with background color to be green\n"
        return help_text
