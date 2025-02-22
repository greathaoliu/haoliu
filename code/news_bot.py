import requests
import feedparser
import schedule
import time
from datetime import datetime
import logging
from typing import List, Dict
import openai
from openai import OpenAI
import os
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    WEBHOOK_KEY = ""  # 替换为你的Webhook密钥
    SILICONFLOW_API_KEY = ""  # 修改为你的Silicon Flow API密钥
    NEWS_SOURCES = {
        "36Kr": {
            "name": "科技新闻",
            "url": "https://36kr.com/feed"
        }
    }

class NewsBot:
    def __init__(self):
        self.last_update = {}
        for source in Config.NEWS_SOURCES:
            self.last_update[source] = datetime.now()
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=Config.SILICONFLOW_API_KEY,
            base_url="https://api.siliconflow.cn/v1"
        )
    
    def get_article_content(self, url: str) -> str:
        """获取新闻文章的具体内容"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # 这里需要根据具体网站调整选择器
            article = soup.find('article') or soup.find('div', class_='article-content')
            if article:
                return article.get_text().strip()
            return ""
        except Exception as e:
            logger.error(f"获取文章内容失败: {e}")
            return ""

    def summarize_content(self, content: str) -> str:
        """使用Silicon Flow API总结新闻内容"""
        try:
            if not content:
                return ""
            
            response = self.client.chat.completions.create(
                model="Pro/deepseek-ai/DeepSeek-V3",
                messages=[
                    {"role": "system", "content": "请用简洁的语言总结以下新闻内容，限制在100字以内。"},
                    {"role": "user", "content": content}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"内容总结失败: {e}")
            return ""

    def generate_daily_insights(self, all_news_content: str) -> str:
        """生成每日新闻总结和投资建议"""
        try:
            response = self.client.chat.completions.create(
                model="Pro/deepseek-ai/DeepSeek-V3",
                messages=[
                    {"role": "system", "content": "你是一位专业的投资分析师，请基于今日新闻进行分析并给出见解。"},
                    {"role": "user", "content": f"""请完成以下两项任务：
                    1. 简要总结今日新闻的主要趋势（100字以内）
                    2. 基于这些新闻给出具体的投资建议（包括可能受影响的行业、个股等）
                    
                    今日新闻内容如下：
                    {all_news_content}"""}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"生成每日见解失败: {e}")
            return ""

    def get_news(self, source_id: str) -> List[Dict]:
        """获取指定源的新闻"""
        try:
            source = Config.NEWS_SOURCES[source_id]
            feed = feedparser.parse(source["url"])
            news_list = []
            
            for entry in feed.entries[:5]:  # 获取最新的5条新闻
                # RSS中的内容被CDATA包裹，需要清理
                title = entry.title
                if "CDATA" in title:
                    title = title.split("CDATA[")[1].split("]")[0]
                
                # 直接使用RSS中的描述作为内容
                content = entry.description if hasattr(entry, 'description') else ""
                if "CDATA" in content:
                    content = content.split("CDATA[")[1].split("]")[0]
                
                # 获取AI生成的摘要
                summary = self.summarize_content(content)
                
                # 使用文章的实际发布时间
                published_time = datetime.now()
                if hasattr(entry, 'published'):
                    try:
                        # 解析36Kr特定的时间格式
                        published_time = datetime.strptime(entry.published.strip(), "%Y-%m-%d %H:%M:%S  +0800")
                    except Exception as e:
                        logger.error(f"解析发布时间失败: {e}")
                
                news_list.append({
                    "title": title,
                    "link": entry.link if hasattr(entry, 'link') else "",
                    "published": published_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "summary": summary
                })
            
            if news_list:
                self.last_update[source_id] = datetime.now()
            return news_list
            
        except Exception as e:
            logger.error(f"获取新闻失败 - {source_id}: {e}")
            return []

    def send_wechat_message(self, content: str) -> None:
        """通过Webhook发送消息到企业微信群"""
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={Config.WEBHOOK_KEY}"
        
        data = {
            "msgtype": "markdown",
            "markdown": {"content": content}
        }
        
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            if result.get("errcode") != 0:
                logger.error(f"发送消息失败: {result}")
        except Exception as e:
            logger.error(f"发送消息异常: {e}")

    def generate_report(self) -> None:
        """生成并发送新闻报告"""
        try:
            news_found = False
            report = "# 📰 国内新闻速报\n\n"
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report += f"更新时间：{current_time}\n\n"
            
            # 收集所有新闻内容用于生成见解
            all_news_content = ""

            for source_id, source_info in Config.NEWS_SOURCES.items():
                news_list = self.get_news(source_id)
                if not news_list:
                    continue
                    
                news_found = True
                report += f"## {source_info['name']}\n"
                
                for news in news_list:
                    if news["link"]:
                        report += f"- [{news['title']}]({news['link']})\n"
                    else:
                        report += f"- {news['title']}\n"
                    if news["summary"]:
                        report += f"  > {news['summary']}\n"
                        all_news_content += f"{news['title']}\n{news['summary']}\n\n"
                    report += f"  *更新时间：{news['published']}*\n\n"

            if news_found:
                # 生成每日见解
                insights = self.generate_daily_insights(all_news_content)
                insights_report = ""
                if insights:
                    insights_report += "\n## 📊 每日见解与投资建议\n"
                    insights_report += f"{insights}\n\n"
                    insights_report += "\n*免责声明：以上投资建议仅供参考，投资有风险，入市需谨慎。*\n"
                
                self.send_wechat_message(report)
                self.send_wechat_message(insights_report)
                logger.info("新闻更新已发送")
            else:
                logger.info("没有新的新闻更新")
        except Exception as e:
            logger.error(f"生成报告失败: {e}")


def run_schedule():
    bot = NewsBot()
    
    # 首次运行
    bot.generate_report()
    # 设置定时任务：每30分钟执行一次
    schedule.every(30).minutes.do(bot.generate_report)
    
    logger.info("定时任务已设置，将每30分钟推送一次新闻报告")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    logger.info("新闻报告机器人启动...")
    run_schedule()
