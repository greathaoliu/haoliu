@echo off
chcp 65001 >nul
:: 微信多开脚本
:: 使用方法：双击运行此批处理文件

:: 设置微信开启数量和微信路径
set num=2
set "WeChatPath=C:\Program Files (x86)\Tencent\WeChat\WeChat.exe"

for /l %%i in (1,1,%num%) do (
    echo 正在启动第%%i个微信实例...
    start "" "%WeChatPath%" /multi
)

echo 微信多开已启动！
echo 如果路径不正确，请编辑此脚本并修改为您电脑上微信的实际安装路径。
pause
