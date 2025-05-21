# 远程关键字语法示例

## 当前支持的语法

目前，pytest-dsl 支持以下远程关键字导入和调用语法：

### 远程关键字导入

```python
@remote: "http://keyword-server:8270/" as machineone
@remote: "http://keyword-server2:8270/" as machinetwo
```

这种语法的格式是：`@remote: "URL" as 别名`

### 远程关键字调用

与当前支持的语法相同：

```python
machineone|[打印],内容: "这是通过远程服务器执行的关键字"
结果 = machineone|[拼接字符串],前缀: "Hello, ",后缀: "Remote World!"

machinetwo|[打印],内容: "这是通过远程服务器执行的关键字"
结果 = machinetwo|[拼接字符串],前缀: "Hello, ",后缀: "Remote World!"
```
