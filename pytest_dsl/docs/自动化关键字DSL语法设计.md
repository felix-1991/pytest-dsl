# DSL语法设计

# 目的

这是一个测试自动化关键字驱动的DSL语法，请基于你的理解，识别出其中的语法

# DSL语法如下

```
@name: 测试好用例
@description: 这是一个测试用例
@tags: [BVT, 自动化]
@author: 陈双麟
@date: 2021-08-10 14:30:00

function 打印内容 (内容) do
    [打印],输出:${内容}
end

number = 5
for i in range(1, ${number}) do
    [打印内容],内容: '第${i}次循环'
end

[API接口调用],方法:GET,URL:'https://www.baidu.com/1',请求头:'{"Content-Type": "application/json"}',请求参数:'{}',响应参数:'{"status_code": 200, "content": "success"}'
[API接口调用],方法:GET,URL:'https://www.baidu.com/2',请求头:'{"Content-Type": "application/json"}',请求参数:'{}',响应参数:'{"status_code": 200, "content": "success"}'
[API接口调用],方法:GET,URL:'https://www.baidu.com/3',请求头:'{"Content-Type": "application/json"}',请求参数:'{}',响应参数:'{"status_code": 200, "content": "success"}'

@teardown do
    [打印内容],内容:测试结束
    [API接口调用],方法:GET,URL:'https://www.baidu.com',请求头:'{"Content-Type": "application/json"}',请求参数:'{}',响应参数:'{"status_code": 200, "content": "success"}'
end
```

从上述`DSL`（`领域特定语言`）来看，它设计为一种简洁的测试自动化语法，融合了关键字驱动的方式，以下是语法的分析与关键元素的识别：

# **DSL语法结构**

## **元信息描述部分**

```
  # 用于描述测试用例的基本信息，通常以@开头：
  @name：用例名称
  @description：用例描述
  @tags：标签（支持多个标签）
  @author：编写人
  @date：创建日期

```

## **变量声明**

变量可以直接赋值：

示例：`number = 5`

### **全局变量**

以`g_`开头的变量会自动成为全局变量，可以在不同的测试用例之间共享：

示例：`g_username = "testuser"`

这样定义的全局变量可以在其他测试用例中直接使用，无需显式调用设置全局变量关键字。

## **循环**

使用`for...in range...do`定义循环：

示例：

```
for i in range(1, ${number}) do
    ...
end
```

支持占位符语法（如：`${number}`）用于动态替换。

## **关键字驱动调用**

核心测试步骤是通过类似“关键字+参数”形式来描述的：

格式：`[关键字]，参数名1:值1, 参数名2:值2, ...`

示例：

```
[打印内容],内容: 第${i}次循环
```

## **收尾清理（`Teardown`）**

使用`@teardown`定义测试后的清理操作：

格式：`@teardown do...end`

示例：

```
@teardown do
    [打印内容],内容:测试结束
    ...
end

```

# **DSL语法关键特性**

## **动态性**

• 使用占位符（如：`${变量名}`）实现动态参数注入，便于复用和灵活性。

## **可读性**

• 采用中文关键字（如：`打印内容`、`API接口调用`）和参数描述，使得语法更加直观易懂。

### **结构化**

• 函数、循环、变量、关键字调用等模块化设计，易于扩展和维护。

### **元信息增强**

元信息部分提供了额外的上下文（如`标签`、`作者`），便于用例分类和管理。

## **总结的DSL语法元素**

| **类型** | **关键字 / 格式** | **功能** |
| --- | --- | --- |
| **元信息** | @name, @description 等 | 测试用例的元信息描述 |
| **变量** | 变量名 = 值 | 声明变量并赋值 |
| **循环** | for...in range...do | 循环控制结构 |
| **关键字调用** | [关键字]，参数：值 | 调用预定义关键字实现特定功能 |
| **清理操作** | @teardown do...end | 定义测试结束后的操作 |