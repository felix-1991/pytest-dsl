from core.keyword_manager import keyword_manager
from playwright.sync_api import sync_playwright


@keyword_manager.register('打开页面', [
    {'name': '地址', 'mapping': 'url', 'description': '要打开的页面地址'},
    {'name': '页面名称', 'mapping': 'page_name', 'description': '页面对象名称'}
])
def open_page(context, **kwargs):
    """
    打开指定URL的页面，并将页面对象存储在上下文中
    
    :param context: 测试上下文对象
    :param kwargs: 关键字参数
        - url: 要打开的页面URL
        - page_name: 页面对象的名称
    """
    url = kwargs.get('url')
    page_name = kwargs.get('page_name')
    
    # 这里假设我们使用 playwright 作为UI自动化工具
    # 实际使用时需要先初始化 playwright
    if not context.has('browser'):
        # 如果浏览器对象不存在，则创建一个新的
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=False)
        context.set('browser', browser)
        context.set('playwright', playwright)

    browser = context.get('browser')
    page = browser.new_page()
    page.goto(url)
    
    # 将页面对象存储在上下文中
    context.set(page_name, page)
    return page

@keyword_manager.register('获取页面', [
    {'name': '页面名称', 'mapping': 'page_name', 'description': '页面对象名称'}
])
def get_page(context, **kwargs):
    """
    从上下文中获取已存在的页面对象
    
    :param context: 测试上下文对象
    :param kwargs: 关键字参数
        - page_name: 页面对象的名称
    :return: 页面对象
    """
    page_name = kwargs.get('page_name')
    if not context.has(page_name):
        raise Exception(f"页面 '{page_name}' 不存在，请先使用 '打开页面' 关键字创建")
    return context.get(page_name)

@keyword_manager.register('关闭浏览器', [])
def close_browser(context, **kwargs):
    """
    关闭浏览器并清理资源
    
    :param context: 测试上下文对象
    :param kwargs: 关键字参数（无）
    """
    if context.has('browser'):
        browser = context.get('browser')
        browser.close()
        
    if context.has('playwright'):
        playwright = context.get('playwright')
        playwright.stop()
        
    # 清理上下文中的浏览器相关对象
    context.clear()