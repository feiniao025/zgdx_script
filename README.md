# 电信任务自动化脚本

中国电信APP日常任务自动化工具。

## 脚本说明

| 脚本 | 说明 |
|------|------|
| 电信任务.py | 电信APP签到、抽奖、喂食等任务 |
| tv189.py | 天翼超高清任务（签到、分享、视频奖励） |

---

## 电信任务.py

### 功能

- **每日签到** - 自动完成签到，获取金豆奖励
- **连签奖励** - 连续签到7天自动领取奖励
- **累签奖励** - 累计签到15/28天自动领取奖励
- **金豆抽奖** - 自动执行金豆转盘抽奖
- **任务完成** - 自动完成可用的日常任务
- **喂食功能** - 自动执行喂食任务（每日最多10次）

### 环境要求

- Python 3.8+

### 安装

```bash
pip install requests pycryptodome certifi
```

### 配置

通过环境变量 `chinaTelecomAccount` 配置账号信息。

**单账号：**
```
手机号#密码
```

**多账号：** 使用 `&` 分隔
```
手机号1#密码1&手机号2#密码2
```

## 使用

### Windows (PowerShell)

```powershell
$env:chinaTelecomAccount = "13800138000#password123"
python 电信任务.py
```

### Windows (CMD)

```cmd
set chinaTelecomAccount=13800138000#password123
python 电信任务.py
```

### Linux / macOS

```bash
export chinaTelecomAccount="13800138000#password123"
python3 电信任务.py
```

## 定时任务

### Windows 任务计划程序

1. **创建批处理文件** `run_task.bat`：

```batch
@echo off
set chinaTelecomAccount=手机号#密码
cd /d D:\code\dx\中国电信
python 电信任务.py >> task.log 2>&1
```

2. **打开任务计划程序**：
   - 按 `Win + R`，输入 `taskschd.msc`，回车

3. **创建基本任务**：
   - 右侧点击「创建基本任务」
   - 名称：`电信任务`
   - 触发器：选择「每天」，设置时间（如 08:00）
   - 操作：选择「启动程序」
   - 程序：浏览选择 `run_task.bat` 文件
   - 完成

4. **（可选）修改任务属性**：
   - 双击任务 → 常规 → 勾选「不管用户是否登录都要运行」
   - 条件 → 取消勾选「只有在计算机使用交流电源时才启动」

### Windows PowerShell 计划任务

```powershell
# 创建计划任务（每天早上8点执行）
$action = New-ScheduledTaskAction -Execute "python" -Argument "D:\code\dx\中国电信\电信任务.py" -WorkingDirectory "D:\code\dx\中国电信"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# 注意：需要先设置环境变量，或在脚本中硬编码账号
Register-ScheduledTask -TaskName "电信任务" -Action $action -Trigger $trigger -Settings $settings
```

### Crontab (每天早上8点)

```bash
0 8 * * * cd /path/to/script && chinaTelecomAccount="手机号#密码" python3 电信任务.py >> task.log 2>&1
```

### 青龙面板

```
cron: 0 8 * * *
```

在环境变量中添加 `chinaTelecomAccount`。

## 输出示例

```
[2025-12-10 08:00:01] 📱 共找到2个账号，开始执行任务

==================== 账号[1] 138****0000 ====================
[2025-12-10 08:00:02] [缓存登录] 138****0000 使用缓存登录
[2025-12-10 08:00:02] [Ticket成功] 138****0000 获取ticket成功
[2025-12-10 08:00:03] [统一登录] 138****0000 获取Authorization成功
[2025-12-10 08:00:03] [抽奖次数] 138****0000 可抽奖2次
[2025-12-10 08:00:04] [抽奖结果] 138****0000 第1次: 5金豆
[2025-12-10 08:00:07] [抽奖结果] 138****0000 第2次: 谢谢参与
[2025-12-10 08:00:08] [签到结果] 138****0000 签到成功
[2025-12-10 08:00:09] [连签进度] 138****0000 连签5天
[2025-12-10 08:00:12] [累签天数] 138****0000 累计签到18天
[2025-12-10 08:00:13] [任务执行] 138****0000 开始: 浏览商城
[2025-12-10 08:00:14] [任务完成] 138****0000 浏览商城: 任务完成
[2025-12-10 08:00:15] [喂食结果] 138****0000 第1次: 喂食成功
...
[2025-12-10 08:00:25] [喂食完成] 138****0000 今日喂食次数已达上限

[2025-12-10 08:00:30] 所有任务完成
```

### 常见问题

**Q: 提示"未找到环境变量"**

确保正确设置了环境变量。PowerShell 使用 `$env:变量名`，CMD 使用 `set 变量名`。

**Q: 登录失败**

1. 检查手机号和密码是否正确
2. 删除 `Cache.json` 后重试

**Q: Token过期**

脚本会自动检测并清除过期缓存。如仍有问题，手动删除 `Cache.json`。

---

## tv189.py

### 功能

- **每日签到** - 天翼超高清每日签到
- **分享任务** - 自动完成分享任务
- **VIP奖励** - VIP会员奖励、连续包月奖励
- **节日奖励** - 节日活动奖励领取
- **视频奖励** - 观看1/5/30分钟奖励领取

### 安装

```bash
pip install requests
```

### 配置

编辑 `tv189.py`，填入任务中心 Cookie：

```python
USER_COOKIE = "从 h5.nty.tv189.com 抓包获取的 Cookie"
```

### 使用

```bash
python tv189.py
```

### 抓包说明

1. 打开天翼超高清APP
2. 进入任务中心页面
3. 抓包域名 `h5.nty.tv189.com` 的请求
4. 复制 Cookie 头信息

---

## 免责声明

本脚本仅供学习交流使用，请勿用于商业用途。使用者应遵守中国电信相关服务条款。
